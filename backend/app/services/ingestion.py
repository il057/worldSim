import base64
import json
import logging
import re
import struct
import uuid
import zlib
from typing import List, Dict, Any, Tuple, Optional
from app.schemas import (
    DetectedEntity,
    DetectedRelationship,
    CircadianProfile,
    WorldLoreInput,
    CardParseResponse,
    QuickCharacterRequest,
)
from app.services.llm_client import llm_client, strip_emojis
from app.services.config_service import sync_config_to_runtime

logger = logging.getLogger("world_sim.ingestion")


def clean_json_str(text: str) -> str:
    """健壮提取文本中嵌套的 JSON 对象字符串"""
    if not text:
        return "{}"
    t = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    fb = t.find("{")
    lb = t.rfind("}")
    if fb != -1 and lb != -1 and lb > fb:
        return t[fb : lb + 1].strip()
    return t


class IngestionService:
    @staticmethod
    def clean_text_artifacts(text: str, char_name: str = "") -> str:
        """剥离 HTML 标签、酒馆宏、纯正则替换代码与控制性标记（仅做基础正则预处理，绝不截断正文）"""
        if not text:
            return ""

        # 1. 剔除 <style>, <script>, <details>, <summary> 块
        text = re.sub(r"<(style|script|details|summary)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # 2. 转换常见容器与换行标签
        text = re.sub(r"<(br|p|div)[^>]*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</(p|div)>", "\n", text, flags=re.IGNORECASE)

        # 3. 移除剩余 HTML 标签与注释
        text = re.sub(r"<!--[\s\S]*?-->", "", text)
        text = re.sub(r"<[^>]+>", "", text)

        # 4. 剥离酒馆对话标记、变量与条件宏
        text = re.sub(r"<START>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\{\{random:[^}]+\}\}", "", text)
        text = re.sub(r"\{\{setvar:[^}]+\}\}", "", text)
        text = re.sub(r"\{\{getvar:[^}]+\}\}", "", text)

        # 5. 剥离内嵌的纯正则替换宏 (如 s/foo/bar/g)
        text = re.sub(r"s/[^/\n]+/[^/\n]*/[gimsuy]*", "", text)

        # 6. 替换 {{char}} 占位符
        if char_name:
            text = text.replace("{{char}}", char_name).replace("{{CHAR}}", char_name)

        # 规整空行与空白
        lines = [line.strip() for line in text.split("\n")]
        cleaned = "\n".join([line for line in lines if line])
        return strip_emojis(cleaned)

    @classmethod
    def is_frontend_junk_entry(cls, title: str, content: str, keys: str) -> bool:
        """精准识别并拦截纯酒馆前端插件、状态栏模板、纯正则脚本与越狱/提示词注入条目（保护写作风格指导）"""
        t_low = title.lower()
        c_low = content.lower()

        # 0. 写作风格指导白名单（严禁拦截，必须交由 AI 完整保留并重写整理）
        style_keywords = ["写作风格", "风格指导", "文风", "描写规范", "语调", "writing style", "style guide", "narrative style"]
        if any(sk in t_low or sk in c_low for sk in style_keywords):
            return False

        # 1. 标题高危关键词命中（前端配置/状态栏/正则宏等）
        junk_title_keywords = [
            "状态栏", "status", "hud", "display", "format", "regex", "正则",
            "脚本", "script", "jailbreak", "越狱", "post-history", "inject",
            "macro", "代码", "table_format", "gui", "ui", "view_template",
            "system_prompt", "prompt_template", "reply_format", "回复格式",
            "output_format", "markdown_table", "author's note", "authors note"
        ]
        if any(kw in t_low for kw in junk_title_keywords):
            return True

        # 2. 纯正则替换脚本特征 (如 s/foo/bar/g 或 /(.*)/g ->)
        if re.search(r"/(?:[^\n/]+)/[gimsuy]*\s*->", content) or re.search(r"s/[^/\n]+/[^/\n]*/[gimsuy]*", content):
            return True

        # 3. HTML/CSS 前端渲染代码块特征
        if "<style" in c_low or "<script" in c_low or "div class=" in c_low or "markdown_table" in c_low:
            return True

        # 4. 前端变量宏与状态模板特征
        if "{{getvar:" in c_low or "{{setvar:" in c_low or "status_bar" in c_low:
            return True

        # 5. 系统指令/越狱覆写特征
        if re.search(r"\[(?:system|instruction|prompt)\s*(?:note|override):", content, re.IGNORECASE):
            return True

        return False

    @classmethod
    def decouple_user_dependency(cls, text: str) -> str:
        """解耦 {{user}} 交互依赖，转化为客观叙事代词"""
        if not text:
            return ""

        replacements = [
            (r"等待\s*\{\{user\}\}\s*下达指令", "沉思审视当下的处境与行动目标"),
            (r"与\s*\{\{user\}\}\s*对话", "与同行之人交谈"),
            (r"听从\s*\{\{user\}\}", "遵循既定的契约与盟约"),
            (r"\{\{user\}\}的", "昔日同行者的"),
            (r"\{\{user\}\}", "不告而别的旧友"),
            (r"\{\{USER\}\}", "昔日旧友"),
            (r"<user>", "昔日旧友"),
            (r"\{user\}", "昔日旧友"),
        ]
        res = text
        for pat, repl in replacements:
            res = re.sub(pat, repl, res)
        return res

    @staticmethod
    def extract_png_data(png_bytes: bytes) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """从 PNG 字节流解析酒馆卡 tEXt/zTXt/iTXt 数据块并生成头像 Base64 数据 URL"""
        if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return None, None

        avatar_url = f"data:image/png;base64,{base64.b64encode(png_bytes).decode('ascii')}"
        parsed_json = None

        pos = 8
        length = len(png_bytes)
        while pos + 8 <= length:
            try:
                chunk_len, chunk_type = struct.unpack(">I4s", png_bytes[pos : pos + 8])
                pos += 8
                chunk_data = png_bytes[pos : pos + chunk_len]
                pos += chunk_len + 4  # skip CRC
                if chunk_type in (b"tEXt", b"zTXt", b"iTXt"):
                    parts = chunk_data.split(b"\x00", 1)
                    keyword = parts[0].decode("latin-1", errors="ignore").lower()
                    if len(parts) > 1 and keyword in ("chara", "ccv3"):
                        val = parts[1]
                        if chunk_type == b"zTXt":
                            val = zlib.decompress(val[1:])
                        try:
                            decoded = base64.b64decode(val).decode("utf-8")
                            parsed_json = json.loads(decoded)
                            break
                        except Exception:
                            try:
                                parsed_json = json.loads(val.decode("utf-8"))
                                break
                            except Exception:
                                pass
            except Exception:
                break

        if not parsed_json:
            text_decoded = png_bytes.decode("latin-1", errors="ignore")
            chara_match = re.search(r"chara\x00([A-Za-z0-9+/=]+)", text_decoded)
            if chara_match:
                try:
                    decoded = base64.b64decode(chara_match.group(1)).decode("utf-8")
                    parsed_json = json.loads(decoded)
                except Exception:
                    pass

        return parsed_json, avatar_url

    @classmethod
    async def parse_character_card(
        cls,
        card_data: Dict[str, Any],
        avatar_data_url: Optional[str] = None,
    ) -> CardParseResponse:
        """
        全面由 AI 整理与清洗酒馆角色卡：
        1. 正则仅做轻量预处理，绝不截断 persona_summary；
        2. 将全量人设 + 全部世界书条目注入 AI；
        3. 由 AI 深度提炼角色精准头衔、内在执念、生理作息、初始地点、随身物品与目标；
        4. 识别多人卡（含世界书内角色）与多主角候选；
        5. 深度识别并提炼 NPC 关系网（自适应好感度与背景）；
        6. 剔除状态栏/越狱脏条目；已被提炼为 NPC 的世界书条目不再重复保留在世界书中；
        7. 严禁使用任何默认 fallback 兜底值。
        """
        # 实时同步最新系统 LLM 运行期配置
        sync_config_to_runtime()

        data_block = card_data.get("data", card_data)

        # 提取基础文本
        main_name = (data_block.get("name") or "未命名角色").strip()
        description = data_block.get("description", "")
        personality = data_block.get("personality", "")
        scenario = data_block.get("scenario", "")
        first_mes = data_block.get("first_mes", "")

        # 1. 基础正则清洗（剔除 HTML/CSS 与宏标记，但保留原设定中涉及 {{user}} 的上下文，以便 AI 精确识别其生态位并具象化为 NPC）
        cleaned_desc = cls.clean_text_artifacts(description, main_name)
        cleaned_pers = cls.clean_text_artifacts(personality, main_name)
        cleaned_scen = cls.clean_text_artifacts(scenario, main_name)
        cleaned_first = cls.clean_text_artifacts(first_mes, main_name)

        # 全量组装人设（绝不做限制截断）
        persona_parts = []
        if cleaned_pers:
            persona_parts.append(cleaned_pers)
        if cleaned_desc and cleaned_desc != cleaned_pers:
            persona_parts.append(cleaned_desc)
        if cleaned_scen:
            persona_parts.append(f"背景与场景：{cleaned_scen}")

        full_persona_text = "\n\n".join(persona_parts).strip()
        if not full_persona_text:
            full_persona_text = f"{main_name}，角色卡未提供详细文字描述。"

        # 2. 收集卡片自带的全部世界书条目（提取原始 constant 常驻属性与触发词，并强力拦截前端状态栏/正则脏条目）
        cbook = data_block.get("character_book", {}) or card_data.get("character_book", {})
        raw_entries = cbook.get("entries", [])
        raw_entries_list: List[Dict[str, Any]] = []

        if isinstance(raw_entries, list):
            for entry in raw_entries:
                if not entry.get("enabled", True):
                    continue
                content = entry.get("content", "")
                if not content or len(content.strip()) < 5:
                    continue
                keys = entry.get("keys", [])
                if not keys:
                    keys = entry.get("key", [])
                keys_str = ",".join([k.strip() for k in keys if k.strip()]) if isinstance(keys, list) else str(keys)
                comment = entry.get("comment", "") or entry.get("name", "") or "世界书设定"

                # 核心拦截：直接过滤前端状态栏、正则代码、输出格式宏与越狱垃圾条目（防止输入Token膨胀与垃圾正文入库）
                if cls.is_frontend_junk_entry(comment, content, keys_str):
                    logger.info(f"[AI Ingestion] 已自动过滤前端/正则脏条目: 【{comment}】")
                    continue

                is_constant = bool(entry.get("constant", False))
                cleaned_c = cls.clean_text_artifacts(content, main_name)
                if not cleaned_c or len(cleaned_c.strip()) < 5:
                    continue

                raw_entries_list.append({
                    "title": comment,
                    "is_constant": is_constant,
                    "keys": keys_str,
                    "content": cleaned_c,
                })

        # 3. 构建全量 AI 整理提示词
        system_prompt = (
            "你是一个顶尖虚拟世界设定深度分析与群像小说推演架构专家。用户上传了一张 SillyTavern 酒馆角色卡。\n"
            "你需要对卡片的基础人设与全部世界书条目进行端到端的深度整理、清洗与高阶画像衍生。\n\n"
            "【最高铁律准则】\n"
            "1. 严禁使用任何敷衍的默认占位值（如“漫游者”、“警惕且冷静”、“随身物件”等）！必须完全立足于人设背景、世界法理和生活情境量身定制！\n\n"
            "2. 【解耦 {{user}} 与生态位 NPC 具象化生成】（极度重要）：\n"
            "   - 绝对禁止识别 {{user}} / 玩家 为 POV 候选主角！主视角实体（entities）必须全部是角色卡中真实定义的具名人物。\n"
            "   - 仔细分析卡片设定与世界书中关于 {{user}}（原玩家/对话者）的描写与设定：\n"
            "     若原设定赋予了 {{user}} 某种特定社会角色或生态位（例如：五人乐队里的鼓手、侦探事务所搭档、同住舍友、青梅竹马、契约者、专属监护人等）：\n"
            "     你必须根据卡片中提到的只言片语，具象化新建一个符合世界观背景的具名 NPC，用以代替原 user 的生态位！\n"
            "   - 【严格遵循社会学与亲属文化逻辑】（必须严密自洽，杜绝逻辑漏洞）：\n"
            "     1. 血缘亲属同姓：若原设定中 user 与主角（或某位主要角色）是双胞胎、兄弟姐妹、父子/母女等亲属关系，生成的具名 NPC 必须共享相同的家族姓氏！若为双胞胎，名字更需体现对称呼应、同字辈或相近音义（如中式同姓同字辈，西式同姓且音律相衬），绝对禁止双胞胎却使用完全无关姓氏的低级常识漏洞；\n"
            "     2. 组织与阶层自洽：若是同门弟子、同一乐队、同事搭档，姓名风格必须与故事所处的世界观时代、国别文化与社会阶层高度协调；\n"
            "     - 明确其社会身份、外貌性格特征以及与主角们的交集；\n"
            "     - 将该 NPC 加入到所有候选主角的 NPC 关系网（relationships）中；\n"
            "     - 在各个主角的描述和人设中，将原本对 {{user}} 的依赖彻底转写为对该具象化 NPC 的羁绊与态度，使世界完全自洽闭环演化！\n\n"
            "3. 【所有登场 NPC 平等深度描写准则（双轨结构与零冗余提炼）】（极度重要）：\n"
            "   - 仔细识别卡片主体与世界书中包含的所有主要角色（或可操作角色/并列主角，如乐队的各个乐手、公馆的几位主要住客等）。\n"
            "   - 若包含多个主要角色，is_multi_entity 设为 true，在 entities 数组中输出所有候选主角实体。\n"
            "   - 每个候选实体的人设、执念、作息、开局场景、生理状态、背包物品与行动目标必须完全独立且量身定制。\n"
            "   - 【所有登场 NPC 平等对待原则】：\n"
            "     无论某 NPC 在原卡中是并列主要角色还是世界书配角，在最终呈现时地位完全平等；\n"
            "     在 entities 的 relationships 关系网中，聚焦输出当前主视角对该 NPC 的【专属社会关系】、【初始好感度】与【专属主观态度与互动纠葛】（精炼深刻，50~100字，写明具体相处态度与过往羁绊，严禁单句‘嫌弃对方’敷衍；客观身份生平画像将由系统统一从实体人设/世界书中自动对齐融合，切勿在此重复冗长抄写其生平，严禁写‘本卡主要角色’等元标签）；\n"
            "   - 【多实体专属关系网绝对独立与好感度支持负数】：每一个 entity 必须包含专属的 relationships 关系网数组！实体 A 对 NPC X 的好感度（affinity 支持 -100 到 100，允许且支持负数表示对立、戒备、厌恶或竞争纠葛）和态度评价，必须与实体 B 对 NPC X 完全不同，立足各自立场深入撰写！\n\n"
            "4. 【消除字段冗余与纯粹深入性格特质】（极度重要）：\n"
            "   - 每一个 entity 必须提炼输出独立的显式基础生理字段：\n"
            "     - gender: 生理/社会性别 (男 | 女 | 其他/非二元 | 无性别/未知)\n"
            "     - birthday: 诞生时间/生日（必须包含确切年份与月日，如 '2007年3月15日' 或 '天禧二年五月初三'）\n"
            "     - appearance: 外貌体征与服饰细节 (身高、体型、发型发色、瞳孔眼眸、显著面部特征与标志性常驻着装)\n"
            "   - 【严禁在 persona_summary 中重复生理标签】：gender、birthday、appearance 已经具备专属独立字段，persona_summary 严禁重复写性别、生日、外貌等已结构化的基础信息，杜绝浪费上下文 Token！\n"
            "   - 【人设立体自然，切勿强加病态阴暗设定】：persona_summary 必须将全量笔墨倾注于：角色核心性格底色、为人处世哲学、行事准则、个性特征与行为习惯、人际交往态度与深层人物背景脉络（不设字数上限，严禁人为机械截断；必须忠于原卡画风与基调，切勿无端脑补病态阴暗心理或过度防御机制）。\n\n"
            "5. 【世界书配角全量提炼与高质量重写世界法则（必须保留写作风格指导）】（极度重要）：\n"
            "   - 【全量提取世界书具名配角/NPC（不可遗漏）】：凡是描述具体人物、次要角色、配角、组织首脑/干部、联络人、同伴、对手或导师等具名角色的条目，必须全部提取并输出到顶层的 world_npcs 列表中！每一个世界书具名角色都必须被提取为 NPC！\n"
            "   - 【NPC 人设画像完整刻画】：提取的 world_npcs 的 summary 中，深入完整阐述其身份背景、社会定位与性格特征（80~150字，严禁人为字数截断，严禁出现“本卡主要角色”等元标签）！已被提炼为 NPC 的世界书人物条目，绝不再放入 kept_lores 中；\n"
            "   - 【AI 深度重写与理顺世界法则正文（精炼自洽，保留核心）】：\n"
            "     对于保留在 kept_lores 中的世界法则条目，必须由你输出深度重写润色后的 content！彻底剥离原文中夹杂的酒馆正则代码、宏语法、前端排版格式与乱码，理顺语句逻辑，使用流畅自然、严谨自洽的小说世界观文学语言重新组织表述（每条控制在 100~300 字核心设定以内，绝不拖泥带水，杜绝冗长扩写）！\n"
            "   - 【必须保留“写作风格指导”类条目】：特别注意！若原世界书中包含“写作风格指导”、“文学语调或语言风格”、“叙事视角与描写规范”等创作准则，必须予以保留并深度重写理顺，将其 category 设为 'static'，trigger_keys 必须为空字符串 ''！\n"
            "   - 【世界法则分类严格区隔】：\n"
            "     - category 为 'static'（静态常驻）：用于全域世界观法则、物理/魔法底层定理、大时代背景、写作风格指导。静态常驻条目的 trigger_keys 必须为空字符串 ''！严禁填写触发词！\n"
            "     - category 为 'dynamic'（动态关键词触发）：用于特定微观地点、特定阵营组织、专属神器道具、特定机密或支线事件。动态触发条目的 trigger_keys 必须填写 1~5 个逗号分隔的精确触发关键词（如：'黑天鹅公馆, 钟楼'）！\n"
            "   - 【彻底替换与解耦 {{user}}】：在重写世界法则正文时，将涉及原玩家/user 的设定，彻底转写为对替代 user 的具象化 NPC 的羁绊或客观背景代词，绝不能保留任何 {{user}} 标签！\n"
            "   - 剔除纯酒馆前端状态栏、回复格式宏、代码块指令、系统提示或越狱条目（无需在 kept_lores 中列出被剔除的条目）。\n\n"
            "严格以 JSON 对象输出，包含以下结构：\n"
            "{\n"
            '  "is_multi_entity": false,\n'
            '  "user_replacement_npc_name": "若识别并具象化了替代 user 生态位的 NPC 则填写其姓名，否则为空字符串",\n'
            '  "world_npcs": [\n'
            "    {\n"
            '      "npc_name": "从世界书条目中提取的具名NPC姓名",\n'
            '      "relation_type": "该NPC在世界观中的公共社会身份或职业",\n'
            '      "affinity": 50,  // 该NPC对外部整体的基准态度 (-100 到 100)\n'
            '      "summary": "该NPC在世界中的客观身份背景、核心能力特征与性格特质（立体独立画像，80~150字，严禁写‘本卡主要角色’等废话）"\n'
            "    }\n"
            "  ],\n"
            '  "entities": [\n'
            "    {\n"
            '      "name": "角色姓名",\n'
            '      "role": "角色的精准身份称号或头衔",\n'
            '      "gender": "生理/社会性别 (男 | 女 | 其他/非二元 | 无性别/未知)",\n'
            '      "birthday": "诞生时间/生日 (例如: 2007年3月15日 或 天禧二年五月初三)",\n'
            '      "appearance": "外貌体征与服饰细节 (身高、体型、发色瞳色、标志性装束等)",\n'
            '      "persona_summary": "深入且完整地刻画该实体的性格特质、处事哲学、行事准则与深层背景（不设字数上限，严禁人为截断；绝不重复写性别/生日/外貌；已彻底解耦 {{user}}，转为对替代 NPC 的羁绊）",\n'
            '      "inner_drive": "核心内在驱动力或长期追求（深入刻画，不限字数。必须紧扣原卡片的基调与人物抱负，拒绝套路化地归结为童年创伤、被遗弃恐惧或精神病理性动机；它可以是理想抱负、责任信念、对某人的守护与承诺、探索未知的热忱、或生活志向）",\n'
            '      "chronotype": "生理节律倾向 (夜行型 | 早起型 | 昼夜无律型 | 无休眠体质)",\n'
            '      "typical_rest_window": "常规休眠倾向窗口 (例如 05:00 - 13:00)",\n'
            '      "environment_tolerance": "休眠环境耐受度与要求",\n'
            '      "sleep_trigger_summary": "作息驱动与休眠逻辑简述",\n'
            '      "initial_location": "开局微观具体场景位置",\n'
            '      "initial_virtual_time": "开局虚拟时间。必须包含确切的具体年、月、日、时:分（例如：\'2024年10月9日 20:15\' 或 \'天禧三年十月初九日 20:15\'）",\n'
            '      "initial_health": 100,\n'
            '      "initial_stamina": 90,\n'
            '      "initial_psychological_state": "即时心理情绪",\n'
            '      "initial_inventory": ["3~5件标志性随身物品"],\n'
            '      "initial_goals": ["2~3条贴合背景与当前情境的紧迫目标"],\n'
            '      "relationships": [\n'
            "        {\n"
            '          "npc_name": "与当前实体有直接联系的NPC姓名（包含其他主要角色、核心世界书NPC、替代user的NPC）",\n'
            '          "relation_type": "当前实体视角下的专属社会关系类型",\n'
            '          "affinity": 50,  // 当前实体对该 NPC 的初始好感度 (-100 到 100，支持且允许负数表示对立/戒备/厌恶)\n'
            '          "summary": "当前主视角实体对该 NPC 的专属态度、看法、好感成因与互动纠葛（精炼深刻，50~100字，写明具体相处态度与过往羁绊，严禁单句‘嫌弃对方’敷衍；客观身份生平画像将由系统统一融合，无需在此重复抄写生平，严禁‘本卡主角’等元描述）"\n'
            "        }\n"
            "      ]\n"
            "    }\n"
            "  ],\n"
            '  "kept_lores": [\n'
            "    {\n"
            '      "entry_index": 1,  // 对应上述【条目编号 1】\n'
            '      "title": "条目标题",\n'
            '      "category": "static 或 dynamic",\n'
            '      "trigger_keys": "若为 static 必须为空字符串；若为 dynamic 则为逗号分隔的触发词",\n'
            '      "content": "深度重写润色、理顺逻辑、剔除错乱正则与前端宏后的高质量世界法则正文（保留核心设定与写作风格指导，语言精炼自洽，每条100~300字，彻底解耦 {{user}}）"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "严禁包含任何 Emoji 图标。"
        )

        lores_context_items = []
        for i, e in enumerate(raw_entries_list):
            idx = i + 1
            raw_type_hint = "常驻生效(Constant)" if e["is_constant"] else ("关键词触发" if e["keys"] else "常驻背景")
            clean_c = e['content']
            c_snippet = clean_c if len(clean_c) <= 1500 else f"{clean_c[:1500]}...(后略)"
            lores_context_items.append(
                f"【条目编号 {idx}】标题: {e['title']}\n"
                f"原始属性提示: {raw_type_hint}\n"
                f"原始关键词: {e['keys'] or '无'}\n"
                f"内容概要:\n{c_snippet}"
            )
        lores_context = "\n\n".join(lores_context_items)

        user_prompt = (
            f"【角色卡主体信息】\n"
            f"姓名: {main_name}\n"
            f"描述与背景全貌:\n{full_persona_text}\n\n"
            f"开局微观场景设定:\n{cleaned_scen or '未注明具体开局场景'}\n\n"
            f"第一句对话/台词引子:\n{cleaned_first or '无初始台词'}\n\n"
            f"【原始世界书条目列表 (共 {len(raw_entries_list)} 条)】\n"
            f"{lores_context or '本角色卡未包含独立世界书'}"
        )

        # 检查是否配置了有效 API Key
        if not llm_client.api_key or llm_client.api_key.startswith("sk-xxxx"):
            raise ValueError("未检测到有效系统 LLM 配置。请先前往【系统配置】面板填入有效的 API Key 与 Base URL，再进行角色卡导入。")

        # 调用 AI 统一分析
        raw_output = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            json_mode=True,
            temperature=0.3,
        )

        try:
            cleaned_json = clean_json_str(raw_output)
            ai_data = json.loads(cleaned_json)
        except Exception as e:
            logger.error(f"[AI Ingestion] 模型返回的 JSON 无法解析，原始文本: {raw_output[:500]}")
            raise ValueError(f"AI 整理返回格式异常，解析失败: {str(e)}")

        is_multi = bool(ai_data.get("is_multi_entity", False))
        user_rep_name = str(ai_data.get("user_replacement_npc_name") or "").strip()
        user_rep_hint = None
        if user_rep_name:
            user_rep_hint = f"已识别到卡片中涉及原玩家生态位的设定，并自动具象化为具名 NPC【{user_rep_name}】注入关系网与人设中。"

        # 收集顶级 world_npcs 列表（全量世界书配角提取通道）
        raw_world_npcs: List[DetectedRelationship] = []
        raw_world_npcs_data = ai_data.get("world_npcs") or ai_data.get("npcs") or []
        for wn in raw_world_npcs_data:
            if isinstance(wn, dict) and wn.get("npc_name"):
                w_name = str(wn["npc_name"]).strip()
                if w_name:
                    raw_world_npcs.append(
                        DetectedRelationship(
                            npc_name=w_name,
                            relation_type=str(wn.get("relation_type") or "关联者").strip(),
                            affinity=max(0, min(100, int(wn.get("affinity", 50)))),
                            summary=str(wn.get("summary") or "").strip(),
                        )
                    )

        raw_entities = ai_data.get("entities", [])
        if not raw_entities or not isinstance(raw_entities, list):
            # 若 entities 为空，构造基于卡片主体的单实体
            raw_entities = [{
                "name": main_name,
                "role": "漫游者",
                "gender": "保密",
                "birthday": "",
                "appearance": "",
                "persona_summary": full_persona_text,
                "inner_drive": "探寻自身与旧势力的羁绊真相，并在动荡危机中维持生存与秩序。",
                "chronotype": "昼夜无律型",
                "typical_rest_window": "01:00 - 08:00",
                "environment_tolerance": "隐蔽安全居所",
                "sleep_trigger_summary": "依现场危险程度与生理消耗动态休眠",
                "initial_location": "长宁市古董街老宅正堂",
                "initial_virtual_time": "2024年10月9日 08:00",
                "initial_health": 100,
                "initial_stamina": 90,
                "initial_psychological_state": "警惕且冷静",
                "initial_inventory": ["随身物件"],
                "initial_goals": ["审视四周环境安全"],
                "relationships": [],
            }]

        entities: List[DetectedEntity] = []
        for e in raw_entities:
            c_name = e.get("name") or main_name
            c_role = e.get("role") or "候选主角"
            c_gender = str(e.get("gender") or "保密").strip()
            c_birthday = str(e.get("birthday") or "").strip()
            c_appearance = str(e.get("appearance") or "").strip()

            c_persona = e.get("persona_summary") or full_persona_text
            # 兜底替换可能遗留的 {{user}}
            if user_rep_name:
                c_persona = c_persona.replace("{{user}}", user_rep_name).replace("{{USER}}", user_rep_name)
            c_persona = cls.decouple_user_dependency(c_persona)

            # 彻底清洗可能残留的旧式【基础档案】与【性格与处世】标签，专注纯净性格特质，绝不重复拼接档案
            c_persona = re.sub(r"^【基础档案】[^\n]*\n*", "", c_persona).strip()
            c_persona = re.sub(r"^【性格与处世】\s*", "", c_persona).strip()

            c_drive = e.get("inner_drive") or "践行自身处事准则与信念，追寻长远的目标与理想。"
            if user_rep_name:
                c_drive = c_drive.replace("{{user}}", user_rep_name).replace("{{USER}}", user_rep_name)
            c_drive = cls.decouple_user_dependency(c_drive)

            circ = CircadianProfile(
                chronotype=e.get("chronotype", "昼夜无律型"),
                typical_rest_window=e.get("typical_rest_window", "01:00 - 08:00"),
                environment_tolerance=e.get("environment_tolerance", "安全掩体"),
                sleep_trigger_summary=e.get("sleep_trigger_summary", ""),
            )
            raw_time_str = str(e.get("initial_virtual_time") or "").strip()
            # 校验是否具备日号与时分
            if not re.search(r"\d{1,2}:\d{2}", raw_time_str):
                norm_time = "2024年10月9日 20:00"
            elif not re.search(r"\d{1,2}日", raw_time_str) and not re.search(r"[初|十|廿|卅][一|二|三|四|五|六|七|八|九|十]", raw_time_str):
                tf = re.search(r"(\d{1,2}:\d{2})", raw_time_str).group(1)
                norm_time = f"2024年10月9日 {tf}"
            else:
                norm_time = raw_time_str

            # 整理该实体专属的个性化 relationships
            entity_npcs: List[DetectedRelationship] = []
            raw_rels = e.get("relationships", [])

            for r in raw_rels:
                if isinstance(r, dict) and r.get("npc_name"):
                    r_name = str(r["npc_name"]).strip()
                    if r_name and r_name != c_name:
                        # 清理可能误带的标签
                        r_summary = re.sub(r"^【基础档案】[^\n]*\n*", "", str(r.get("summary") or "")).strip()
                        r_summary = re.sub(r"^【性格与处世】\s*", "", r_summary).strip()
                        entity_npcs.append(
                            DetectedRelationship(
                                npc_name=r_name,
                                relation_type=r.get("relation_type", "关联者"),
                                affinity=max(-100, min(100, int(r.get("affinity", 50)))),
                                summary=r_summary,
                            )
                        )

            entities.append(
                DetectedEntity(
                    entity_id=f"ent_{uuid.uuid4().hex[:8]}",
                    name=c_name,
                    title=c_role,
                    gender=c_gender,
                    birthday=c_birthday,
                    appearance=c_appearance,
                    avatar_url=avatar_data_url or "",
                    persona_summary=c_persona,
                    inner_drive=c_drive,
                    circadian_profile=circ,
                    relationships_with_others="",
                    relationships=entity_npcs,
                    initial_location=e.get("initial_location") or "长宁市古董街老宅正堂",
                    initial_virtual_time=norm_time,
                    initial_health=int(e.get("initial_health", 100)),
                    initial_stamina=int(e.get("initial_stamina", 90)),
                    initial_psychological_state=e.get("initial_psychological_state") or "冷静警惕",
                    initial_inventory=e.get("initial_inventory") or ["随身物件"],
                    initial_goals=e.get("initial_goals") or ["排查环境安全"],
                )
            )

        # 全局 NPC 三位一体聚合防御与平等深度双轨标准对齐：
        # 全局 NPC 三位一体聚合防御与平等深度双轨标准对齐：
        # （无论原角色是并列主要角色还是世界书NPC，所有NPC必须平等深度描写，杜绝单句敷衍与厚此薄彼）
        all_entity_map = {ent.name: ent for ent in entities}
        raw_world_npc_map = {wn.npc_name: wn for wn in raw_world_npcs}

        for ent in entities:
            # 1. 深度对齐已有关系的双轨标准：
            # 无论目标 NPC 是原卡并列主要角色、世界书配角还是替代 user 的 NPC，均自动合成【客观生平画像 + 主视角专属态度】
            for r in ent.relationships:
                raw_s = (r.summary or "").strip()
                if r.npc_name in all_entity_map:
                    other_ent = all_entity_map[r.npc_name]
                    other_persona = (other_ent.persona_summary or "").strip()
                    if other_persona:
                        already_has_persona = (
                            other_persona[:25] in raw_s
                            or (len(raw_s) >= 180 and ("【" in raw_s or other_ent.name in raw_s[:25]))
                        )
                        if not already_has_persona:
                            if raw_s:
                                if "【对该角色的态度与羁绊】" not in raw_s and "【态度】" not in raw_s:
                                    r.summary = f"{other_persona}\n\n【对该角色的态度与羁绊】：{raw_s}"
                                else:
                                    r.summary = f"{other_persona}\n\n{raw_s}"
                            else:
                                r.summary = f"{other_persona}\n\n【对该角色的态度与羁绊】：同行同伴，在动荡的世界中共处并维系着深层羁绊。"
                elif r.npc_name in raw_world_npc_map:
                    wn = raw_world_npc_map[r.npc_name]
                    wn_desc = (wn.summary or "").strip()
                    if wn_desc and raw_s:
                        already_has_desc = (
                            wn_desc[:25] in raw_s
                            or (len(raw_s) >= 180 and ("【" in raw_s or wn.npc_name in raw_s[:25]))
                        )
                        if not already_has_desc:
                            if "【对该角色的态度与羁绊】" not in raw_s and "【态度】" not in raw_s:
                                r.summary = f"{wn_desc}\n\n【对该角色的态度与羁绊】：{raw_s}"
                            else:
                                r.summary = f"{wn_desc}\n\n{raw_s}"

            existing_npc_names = {r.npc_name for r in ent.relationships}

            # 2. 补全其他未被当前实体包含的主要候选角色实体（作为同行者/搭档）
            for other_name, other_ent in all_entity_map.items():
                if other_name != ent.name and other_name not in existing_npc_names:
                    # 采用完整的客观画像 + 同行者专属羁绊态度，杜绝缺失与厚此薄彼
                    ent.relationships.append(
                        DetectedRelationship(
                            npc_name=other_name,
                            relation_type=other_ent.title or "同行者",
                            affinity=50,
                            summary=f"{other_ent.persona_summary.strip()}\n\n【对该角色的态度与羁绊】：同处一处的同行同伴，彼此性格与处事风格各异，维系着基本的同伴羁绊。",
                        )
                    )
                    existing_npc_names.add(other_name)

            # 3. 补全世界书提取出的全部 NPC (world_npcs)，防止世界书配角因模型注意力遗漏
            for wn in raw_world_npcs:
                if wn.npc_name != ent.name and wn.npc_name not in existing_npc_names:
                    base_summary = (wn.summary or "").strip()
                    full_wn_summary = (
                        f"{base_summary}\n\n【对该角色的态度与羁绊】：世界中的已知关联人物，维持着常规的社交往来。"
                        if base_summary
                        else "世界中的已知关联人物，维持着常规的社交往来。"
                    )
                    ent.relationships.append(
                        DetectedRelationship(
                            npc_name=wn.npc_name,
                            relation_type=wn.relation_type or "世界关联者",
                            affinity=wn.affinity if wn.affinity is not None else 50,
                            summary=full_wn_summary,
                        )
                    )
                    existing_npc_names.add(wn.npc_name)

            # 4. 补全具象化替代 user 的生态位 NPC
            if user_rep_name and user_rep_name != ent.name and user_rep_name not in existing_npc_names:
                ent.relationships.append(
                    DetectedRelationship(
                        npc_name=user_rep_name,
                        relation_type="重要同行者",
                        affinity=60,
                        summary="原设定中与主角群存在重要社会生态位羁绊的角色，现已具象化为世界独立成员，与主角共同面对风波。\n\n【对该角色的态度与羁绊】：与主角维系着深层信赖与默契配合。",
                    )
                )
                existing_npc_names.add(user_rep_name)

        # 构建原始条目的编号与标题映射表（用于精准取回高保真原生正文）
        raw_index_map = {i + 1: e for i, e in enumerate(raw_entries_list)}
        raw_title_map = {str(e.get("title", "")).strip(): e for e in raw_entries_list if e.get("title")}

        # 整理保留的世界书条目并执行严格规整（杜绝常驻+触发词矛盾）
        lores: List[WorldLoreInput] = []
        for lore in ai_data.get("kept_lores", []):
            if isinstance(lore, dict):
                e_idx = lore.get("entry_index")
                title = str(lore.get("title") or "").strip()
                cat = str(lore.get("category") or "static").strip().lower()
                trig_keys = str(lore.get("trigger_keys") or "").strip()

                # 优先获取匹配的原始条目
                matched_raw = None
                if isinstance(e_idx, int) and e_idx in raw_index_map:
                    matched_raw = raw_index_map[e_idx]
                elif title and title in raw_title_map:
                    matched_raw = raw_title_map[title]

                # 内容确定性：若 AI 返回了非空 content 则使用，否则从原始清洗条目中高保真挂载原生正文
                final_content = str(lore.get("content") or "").strip()
                if not final_content and matched_raw:
                    final_content = str(matched_raw.get("content") or "").strip()
                final_title = title or (matched_raw.get("title") if matched_raw else "世界法则")

                if not final_content:
                    continue

                # 必须对最终入库的正文深度清洗，并彻底解耦 {{user}} 与替换具象化 NPC 姓名！
                final_content = cls.clean_text_artifacts(final_content, main_name)
                if user_rep_name:
                    final_content = final_content.replace("{{user}}", user_rep_name).replace("{{USER}}", user_rep_name)
                    final_content = final_content.replace("<user>", user_rep_name).replace("{user}", user_rep_name)
                final_content = cls.decouple_user_dependency(final_content)
                final_content = re.sub(r"\{\{user\}\}", user_rep_name or "旧友", final_content, flags=re.IGNORECASE)
                final_content = re.sub(r"\{\{USER\}\}", user_rep_name or "旧友", final_content)

                if cat == "static":
                    trig_keys = ""
                else:
                    cat = "dynamic"
                    if not trig_keys:
                        if final_title and len(final_title) < 20 and not any(kw in final_title for kw in ["设定", "世界观", "法则", "背景"]):
                            trig_keys = final_title
                        else:
                            cat = "static"
                            trig_keys = ""

                lores.append(
                    WorldLoreInput(
                        title=final_title,
                        category=cat,
                        trigger_keys=trig_keys,
                        content=final_content,
                    )
                )

        # 顶层 detected_relationships 赋予首个实体的完整关系列表（已聚合其他主角 + 全量世界书 NPC + user替代NPC）
        top_relationships = entities[0].relationships if entities else raw_world_npcs

        return CardParseResponse(
            is_multi_entity=is_multi or len(entities) > 1,
            detected_entities=entities,
            detected_relationships=top_relationships,
            total_lore_entries=len(lores),
            lores=lores,
            user_replacement_hint=user_rep_hint,
            raw_preview={
                "name": main_name,
                "first_mes": cleaned_first[:300],
                "desc_snippet": full_persona_text[:200],
            },
        )

    @classmethod
    async def generate_from_quick_form(cls, req: QuickCharacterRequest) -> Dict[str, Any]:
        """通过灵活表单（所有项均可选），由 AI 智能衍生完整角色设定、NPC 关系网（含敌对/矛盾）与世界书"""
        sync_config_to_runtime()

        system_prompt = (
            "你是一个富有想象力的小说世界观与生动角色设计专家。\n"
            "用户提供了一组角色的构想线索（可能包含完整设定，也可能极为轻量或全部留空）。\n"
            "请遵循以下设计准则，衍生出基调契合、生动有趣、具有小说戏剧张力的推演蓝图：\n\n"
            "1. 基调高度自适应（核心铁律）：\n"
            "   - 必须敏锐体察用户的输入风格与情境氛围（涵盖日常温馨、轻松喜剧、奇幻冒险、赛博科幻、悬疑解谜、武侠江湖或严肃生存等任意体裁）。\n"
            "   - 剧情冲突与人物心态必须严格契合该体裁的天然画风与精神风貌。严禁将轻松、生活化或温情的题材强行扭曲为压抑、阴暗、苦大仇深的风格。\n"
            "   - 用户显式给出的内容是必须尊重的设定锚点；未提供的留空项，请紧扣该体裁基调原创补全。\n\n"
            "2. 核心内在执念 (inner_drive) 去沉重化与正向动力源：\n"
            "   - 核心执念是角色采取行动的内在动力源泉与长远追求（50~100字），绝不应公式化地归因于“童年创伤”、“被遗弃的恐惧”或精神病理性动机！\n"
            "   - 执念应当自然且宽广，紧扣人物定位与世界法则：\n"
            "     * 可以是目标理想与抱负追求（如探索世界边界、精进职业技艺、赢取特定荣誉等）；\n"
            "     * 可以是情感羁绊、责任与誓约（如对同伴的守护、对师门或长辈的承诺、助人达成心愿等）；\n"
            "     * 可以是纯粹的好奇心、探索欲、个性爱好或对生活的热忱；\n"
            "     * 唯有在明确设定的残酷末世或生死危机情境下，才体现求生与对抗创伤。\n"
            "   - 角色应是一个“因心中的追求与热爱而前行的人”，切勿将其写成被恐惧和心理阴影驱动的创伤病人。\n\n"
            "3. 真实立体的人物塑造（生活化缺陷与性格反差）：\n"
            "   - 拒绝千篇一律的完美圣人，但角色的弱点应是富有人情味的小毛病、个性反差或处事短板（如爱逞强、好面子、嘴硬心软、做事三分钟热度、贪吃嗜睡、爱恶作剧但偶有翻车、对特定事物毫无抵抗力等）。\n"
            "   - 严禁强加精神病理学层面的阴暗病态心理或神经质防御机制。\n"
            "   - 外貌 (appearance) 包含身型、五官特色、发型与典型穿着风格，贴合该世界的设定画风（80~150字）。\n\n"
            "4. 人际网络与 NPC 关系（所有登场 NPC 平等深度双轨描写铁律）：\n"
            "   - 现实微型社交网络中的关系应当丰富多维，涵盖支持者、羁绊对象、观念不同者与竞争者，好感度 (affinity) 在 -100 到 100 之间浮动。\n"
            "   - 负好感或对立关系源于立场分歧、性格不对付、日常争辩、行事风格差异或利益较劲，绝非所有冲突都是血海深仇或背叛追杀。\n"
            "   - 必须生成 2~4 位与主角有直接交集的初始 NPC（若用户指定了 NPC，优先精准提取并丰富；未指定则按世界观基调原创）。\n"
            "   - 每一个 NPC 必须遵循规范的【双轨深度结构】：\n"
            "     * background (客观身份背景): 客观交代该人物在世界中的真实社会身份/职业/核心能力特征与性格底色（60~120字，严禁写‘本卡主要角色’等元标签）；\n"
            "     * attitude (对该角色的态度与羁绊): 深入写明当前主角对其的真实主观态度、评价、好感成因、互动习惯或过往恩怨纠葛（40~80字，严禁敷衍）。\n\n"
            "5. 世界书条目 (lores) 提取与构建：\n"
            "   - 从用户引导与世界背景中提炼 1~3 条核心设定条目（如社会组织规则、阵营势力格局、行业与能力法则、风土人情或特定戒律），使推演世界具有背景厚度与代入感。\n"
            "   - 每条世界书包含：title, category ('static'|'dynamic'), trigger_keys, content (100~200字详实说明)。\n\n"
            "6. 严禁使用任何 Emoji 图标。\n\n"
            "严格输出有效 JSON 对象，格式如下：\n"
            "{\n"
            '  "name": "主角姓名",\n'
            '  "title": "称号或头衔",\n'
            '  "gender": "男/女/保密/自定义",\n'
            '  "birthday": "生日或纪元时间",\n'
            '  "appearance": "外貌特征详细描述",\n'
            '  "persona_summary": "核心性格与处世准则（200~400字）",\n'
            '  "inner_drive": "内在驱动力或长远追求（50~100字，与整体基调自洽，拒绝套路化创伤）",\n'
            '  "circadian_profile": {\n'
            '    "chronotype": "早起型"|"夜行型"|"昼夜无律型"|"无休眠体质",\n'
            '    "typical_rest_window": "23:00 - 07:00",\n'
            '    "environment_tolerance": "休眠环境要求",\n'
            '    "sleep_trigger_summary": "疲惫与休眠触发机制"\n'
            "  },\n"
            '  "initial_health": 100,\n'
            '  "initial_stamina": 85,\n'
            '  "initial_psychological_state": "当前心理状态（与当下情境相符）",\n'
            '  "initial_inventory": ["物品1", "物品2", "物品3"],\n'
            '  "initial_goals": ["近期目标1", "长远愿景2"],\n'
            '  "initial_location": "开局具体场景位置",\n'
            '  "initial_virtual_time": "符合世界观纪元的起始时间（如：\'新历 342年 霜降月 1日 08:00\' 或 \'2024年10月10日 08:00\'）",\n'
            '  "relationships": [\n'
            "    {\n"
            '      "npc_name": "NPC姓名",\n'
            '      "relation_type": "关系类型（如搭档/同行者/竞争对手/导师/长辈等）",\n'
            '      "affinity": 50,\n'
            '      "background": "NPC在世界中的客观身份背景、核心能力与性格底色（60~120字）",\n'
            '      "attitude": "当前主角对该角色的专属主观态度、评价、好感成因与相处羁绊（40~80字）"\n'
            "    }\n"
            "  ],\n"
            '  "lores": [\n'
            "    {\n"
            '      "title": "条目标题",\n'
            '      "category": "static",\n'
            '      "trigger_keys": "",\n'
            '      "content": "详细世界法则、社会环境或背景设定"\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        user_prompt_lines = ["用户提供的角色创建线索如下（未填写的项请自主发挥）："]
        if req.name and req.name.strip():
            user_prompt_lines.append(f"- 角色姓名: {req.name.strip()}")
        if req.gender and req.gender.strip():
            user_prompt_lines.append(f"- 性别: {req.gender.strip()}")
        if req.birthday and req.birthday.strip():
            user_prompt_lines.append(f"- 生日/历法: {req.birthday.strip()}")
        if req.role and req.role.strip():
            user_prompt_lines.append(f"- 社会身份/职业: {req.role.strip()}")
        if req.appearance and req.appearance.strip():
            user_prompt_lines.append(f"- 外貌特征要求: {req.appearance.strip()}")
        if req.archetype and req.archetype.strip():
            user_prompt_lines.append(f"- 性格底色/处事风格: {req.archetype.strip()}")
        if req.world_guidance and req.world_guidance.strip():
            user_prompt_lines.append(f"- 世界观、社交网络与人际羁绊引导: {req.world_guidance.strip()}")
        if req.initial_situation and req.initial_situation.strip():
            user_prompt_lines.append(f"- 开局微观处境: {req.initial_situation.strip()}")

        if len(user_prompt_lines) == 1:
            user_prompt_lines.append("用户未提供任何输入，请自由发挥创意，构思一个生动有趣、具有鲜明个性与独特世界观的原创主角及引人入胜的开局处境。")

        user_prompt = "\n".join(user_prompt_lines)

        raw = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            json_mode=True,
            temperature=0.75,
        )

        cleaned = clean_json_str(raw)
        data = json.loads(cleaned)

        entity_id = f"ent-{uuid.uuid4().hex[:8]}"
        name = strip_emojis(data.get("name") or req.name or "漫游者")
        title = strip_emojis(data.get("title") or req.role or "探索者")
        gender = strip_emojis(data.get("gender") or req.gender or "保密")
        birthday = strip_emojis(data.get("birthday") or req.birthday or "")
        appearance = strip_emojis(data.get("appearance") or req.appearance or "")
        persona_summary = strip_emojis(data.get("persona_summary") or req.archetype or "性格鲜明，做事富有主见。")
        inner_drive = strip_emojis(data.get("inner_drive") or "追寻自我的价值与生活的热爱。")
        circadian = data.get("circadian_profile") or {
            "chronotype": "早起型",
            "typical_rest_window": "23:00 - 07:00",
            "environment_tolerance": "寻常遮蔽环境",
            "sleep_trigger_summary": "身心俱疲时自然陷入休眠",
        }

        # 关系列表清洗与双轨深度对齐保底（确保客观身份画像 + 对该角色的态度与羁绊规范统一）
        raw_rels = data.get("relationships") or []
        cleaned_relationships = []
        for r in raw_rels:
            npc_name = strip_emojis(r.get("npc_name", "")).strip()
            if not npc_name:
                continue
            rel_type = strip_emojis(r.get("relation_type", "同行者"))
            aff = max(-100, min(100, int(r.get("affinity", 50))))
            bg = strip_emojis(r.get("background", "")).strip()
            att = strip_emojis(r.get("attitude", "")).strip()
            raw_s = strip_emojis(r.get("summary", "")).strip()

            if bg and att:
                final_summary = f"{bg}\n\n【对该角色的态度与羁绊】：{att}"
            elif raw_s:
                if "【对该角色的态度与羁绊】" in raw_s:
                    final_summary = raw_s
                elif "【态度与羁绊】" in raw_s:
                    final_summary = raw_s.replace("【态度与羁绊】", "【对该角色的态度与羁绊】")
                elif "【态度】" in raw_s:
                    final_summary = raw_s.replace("【态度】", "【对该角色的态度与羁绊】")
                elif "【羁绊与态度】" in raw_s:
                    final_summary = raw_s.replace("【羁绊与态度】", "【对该角色的态度与羁绊】")
                else:
                    if att:
                        final_summary = f"{raw_s}\n\n【对该角色的态度与羁绊】：{att}"
                    else:
                        final_summary = f"{raw_s}\n\n【对该角色的态度与羁绊】：与主角处于【{rel_type}】关系（初始好感 {aff}），在日常交往与局势变迁中维系着交集。"
            elif bg:
                final_summary = f"{bg}\n\n【对该角色的态度与羁绊】：与主角处于【{rel_type}】关系（初始好感 {aff}），在日常交往与局势变迁中维系着交集。"
            elif att:
                final_summary = f"世界中的已知关联人物，维持着日常社交往来。\n\n【对该角色的态度与羁绊】：{att}"
            else:
                final_summary = f"世界中的已知关联人物，维持着常规的社交往来。\n\n【对该角色的态度与羁绊】：同行同伴，在动荡的世界中共处并维系着深层羁绊。"

            cleaned_relationships.append({
                "npc_name": npc_name,
                "relation_type": rel_type,
                "affinity": aff,
                "summary": final_summary,
            })

        # 世界书清洗
        raw_lores = data.get("lores") or []
        cleaned_lores = []
        for l in raw_lores:
            title_l = strip_emojis(l.get("title", "")).strip()
            content_l = strip_emojis(l.get("content", "")).strip()
            if not title_l or not content_l:
                continue
            cleaned_lores.append({
                "category": "dynamic" if l.get("category") == "dynamic" else "static",
                "trigger_keys": strip_emojis(l.get("trigger_keys", "")),
                "title": title_l,
                "content": content_l,
            })

        # 若未生成世界书，兜底提供一条常驻背景
        if not cleaned_lores:
            cleaned_lores.append({
                "category": "static",
                "trigger_keys": "",
                "title": "世界初始法则",
                "content": f"{name} 所处的世界处于生动演化之中，未知与机遇并存。",
            })

        detected_entity = {
            "entity_id": entity_id,
            "name": name,
            "title": title,
            "gender": gender,
            "birthday": birthday,
            "appearance": appearance,
            "avatar_url": "",
            "persona_summary": persona_summary,
            "inner_drive": inner_drive,
            "circadian_profile": circadian,
            "relationships": cleaned_relationships,
            "initial_location": strip_emojis(data.get("initial_location") or "起始场景"),
            "initial_virtual_time": strip_emojis(data.get("initial_virtual_time") or "晨光月 1日 08:00"),
            "initial_health": int(data.get("initial_health", 100)),
            "initial_stamina": int(data.get("initial_stamina", 85)),
            "initial_psychological_state": strip_emojis(data.get("initial_psychological_state") or "平稳且怀有期待"),
            "initial_inventory": [strip_emojis(str(x)) for x in data.get("initial_inventory", ["随身笔记", "日常行囊"])],
            "initial_goals": [strip_emojis(str(x)) for x in data.get("initial_goals", ["适应当下处境"])],
        }

        # 构造 CardParseResponse 兼容数据包，并保留顶层平铺字段以向后兼容
        blueprint = {
            "is_multi_entity": False,
            "detected_entities": [detected_entity],
            "detected_relationships": cleaned_relationships,
            "total_lore_entries": len(cleaned_lores),
            "lores": cleaned_lores,
            "user_replacement_hint": None,
            "raw_preview": data,
            # 向后兼容字段
            "entity_id": entity_id,
            "name": name,
            "title": title,
            "gender": gender,
            "birthday": birthday,
            "appearance": appearance,
            "persona_summary": persona_summary,
            "inner_drive": inner_drive,
            "circadian_profile": circadian,
            "initial_location": detected_entity["initial_location"],
            "initial_virtual_time": detected_entity["initial_virtual_time"],
            "initial_health": detected_entity["initial_health"],
            "initial_stamina": detected_entity["initial_stamina"],
            "initial_psychological_state": detected_entity["initial_psychological_state"],
            "initial_inventory": detected_entity["initial_inventory"],
            "initial_goals": detected_entity["initial_goals"],
            "relationships": cleaned_relationships,
        }

        return blueprint
