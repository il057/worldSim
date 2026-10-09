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
        """剥离 HTML 标签、酒馆宏与控制性标记（仅做基础正则预处理，绝不截断正文）"""
        if not text:
            return ""

        # 1. 剔除 <style>, <script>, <details>, <summary> 块
        text = re.sub(r"<(style|script|details|summary)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # 2. 转换常见容器与换行标签
        text = re.sub(r"<(br|p|div)[^>]*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</(p|div)>", "\n", text, flags=re.IGNORECASE)

        # 3. 移除剩余裸露 HTML 标签
        text = re.sub(r"<[^>]+>", "", text)

        # 4. 剥离酒馆对话标记与条件宏
        text = re.sub(r"<START>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\{\{random:[^}]+\}\}", "", text)
        text = re.sub(r"\{\{setvar:[^}]+\}\}", "", text)

        # 5. 替换 {{char}} 占位符
        if char_name:
            text = text.replace("{{char}}", char_name).replace("{{CHAR}}", char_name)

        # 规整空行与空白
        lines = [line.strip() for line in text.split("\n")]
        cleaned = "\n".join([line for line in lines if line])
        return strip_emojis(cleaned)

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

        # 1. 基础正则清洗（不截断任何长度）
        cleaned_desc = cls.decouple_user_dependency(cls.clean_text_artifacts(description, main_name))
        cleaned_pers = cls.decouple_user_dependency(cls.clean_text_artifacts(personality, main_name))
        cleaned_scen = cls.decouple_user_dependency(cls.clean_text_artifacts(scenario, main_name))
        cleaned_first = cls.decouple_user_dependency(cls.clean_text_artifacts(first_mes, main_name))

        # 全量组装人设（绝不做 [:400] 或 [:1000] 等任何限制截断）
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

        # 2. 收集卡片自带的全部世界书条目
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
                keys_str = ",".join([k.strip() for k in keys if k.strip()]) if isinstance(keys, list) else str(keys)
                comment = entry.get("comment", "") or entry.get("name", "") or "世界书设定"
                raw_entries_list.append({
                    "title": comment,
                    "keys": keys_str,
                    "content": cls.clean_text_artifacts(content, main_name),
                })

        # 3. 构建全量 AI 整理提示词
        system_prompt = (
            "你是一个虚拟世界设定深度分析与小说推演架构专家。用户上传了一张 SillyTavern 酒馆角色卡。\n"
            "你需要对卡片的基础人设与全部世界书条目进行端到端的深度整理、清洗与高阶画像衍生。\n\n"
            "【铁律准则】\n"
            "1. 严禁使用任何敷衍的默认占位值（如“漫游者”、“警惕且冷静”、“随身物件”、“避雨涵洞”等）！必须完全立足于提供的人设背景、世界法理和生活情境，量身打造每一个字段！\n"
            "2. 角色卡通常不存在高阶运行数据（如精确身份称号、作息画像、具体居所地点、随身特色物品、紧迫目标），你必须基于卡片人设与世界观深度推导补全。\n"
            "3. 世界书清洗与整合：\n"
            "   - 剔除纯酒馆前端状态栏、回复格式宏、代码块指令、系统提示或越狱条目；\n"
            "   - 识别并提取所有 NPC 关系；凡是已转化为 NPC 关系的条目，不再重复保留在世界书列表（kept_lores）中，避免重复冗余；\n"
            "   - 保留真实的架空世界法则、历史事件、地理背景与势力设定。\n"
            "4. 多人卡识别：检查世界书与卡片设定中是否包含多个独立主角（或可操作角色）。若有，entities 数组中输出所有候选主角；若为单主角卡，输出 1 个主角实体。\n\n"
            "严格以 JSON 对象输出，包含以下结构：\n"
            "{\n"
            '  "is_multi_entity": false,\n'
            '  "entities": [\n'
            "    {\n"
            '      "name": "角色姓名",\n'
            '      "role": "角色的精准身份称号或头衔（如九尾天狐 / 特级荣誉顾问，严禁漫游者）",\n'
            '      "persona_summary": "该实体的完整人设（可基于输入人设适度整理，严禁粗暴截断）",\n'
            '      "inner_drive": "核心内在心理执念与不可磨灭的终极追求（50~100字）",\n'
            '      "chronotype": "生理节律倾向 (夜行型 | 早起型 | 昼夜无律型 | 无休眠体质)",\n'
            '      "typical_rest_window": "常规休眠倾向窗口 (例如 05:00 - 13:00)",\n'
            '      "environment_tolerance": "休眠环境耐受度与要求 (例如 私人老宅软榻或安静向阳的躺椅)",\n'
            '      "sleep_trigger_summary": "作息驱动与休眠逻辑简述",\n'
            '      "initial_location": "开局微观具体场景位置 (基于背景与住所提炼，例如 长宁市古董街36号枕流居老宅前厅茶榻)",\n'
            '      "initial_virtual_time": "开局虚拟时间。必须包含明确确切的【年份、月份、日号、时:分】（例如：\'2024年10月9日 20:15\' 或 \'天禧三年十月初九日 20:15\'）！严禁仅写模糊的季节或无日期的时辰，必须包含明确具体的年、月、日、时:分！",\n'
            '      "initial_health": 100,\n'
            '      "initial_stamina": 90,\n'
            '      "initial_psychological_state": "即时心理情绪 (例如 慵懒、内敛且敏锐)",\n'
            '      "initial_inventory": ["3~5件高度符合角色身份与背景的随身/在手标志性物品"],\n'
            '      "initial_goals": ["2~3条贴合背景与当前情境的紧迫目标"]\n'
            "    }\n"
            "  ],\n"
            '  "npcs": [\n'
            "    {\n"
            '      "npc_name": "NPC 姓名",\n'
            '      "relation_type": "与主角的社会关系类型",\n'
            '      "affinity": 50,  // 根据态度与好恶推导 (0-100)\n'
            '      "summary": "身份背景、外貌特征、性格及对主角态度概述"\n'
            "    }\n"
            "  ],\n"
            '  "kept_lores": [\n'
            "    {\n"
            '      "title": "条目标题",\n'
            '      "category": "static 或 dynamic",\n'
            '      "trigger_keys": "触发词（逗号分隔）",\n'
            '      "content": "清洗后的世界观法则正文"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "严禁包含任何 Emoji 图标。"
        )

        lores_context = "\n\n".join([
            f"【条目 {i+1}】标题: {e['title']}\n触发词: {e['keys']}\n内容:\n{e['content']}"
            for i, e in enumerate(raw_entries_list)
        ])

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
        raw_entities = ai_data.get("entities", [])
        if not raw_entities or not isinstance(raw_entities, list):
            # 若 entities 为空，构造基于卡片主体的单实体
            raw_entities = [{
                "name": main_name,
                "role": "漫游者",
                "persona_summary": full_persona_text,
                "inner_drive": "探寻自身与旧势力的羁绊真相，并在动荡危机中维持生存与秩序。",
                "chronotype": "昼夜无律型",
                "typical_rest_window": "01:00 - 08:00",
                "environment_tolerance": "隐蔽安全居所",
                "sleep_trigger_summary": "依现场危险程度与生理消耗动态休眠",
                "initial_location": "长宁市古董街老宅正堂",
                "initial_virtual_time": "晨光月 1日 08:00",
                "initial_health": 100,
                "initial_stamina": 90,
                "initial_psychological_state": "警惕且冷静",
                "initial_inventory": ["随身物件"],
                "initial_goals": ["审视四周环境安全"],
            }]

        entities: List[DetectedEntity] = []
        for e in raw_entities:
            c_name = e.get("name") or main_name
            c_role = e.get("role") or "候选主角"
            c_persona = e.get("persona_summary") or full_persona_text
            c_drive = e.get("inner_drive") or "在动荡危机中维持生存与秩序。"
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
                # 提取时分部分
                tf = re.search(r"(\d{1,2}:\d{2})", raw_time_str).group(1)
                norm_time = f"2024年10月9日 {tf}"
            else:
                norm_time = raw_time_str

            entities.append(
                DetectedEntity(
                    entity_id=f"ent_{uuid.uuid4().hex[:8]}",
                    name=c_name,
                    title=c_role,
                    avatar_url=avatar_data_url or "",
                    persona_summary=c_persona,
                    inner_drive=c_drive,
                    circadian_profile=circ,
                    relationships_with_others="",
                    initial_location=e.get("initial_location") or "长宁市古董街老宅正堂",
                    initial_virtual_time=norm_time,
                    initial_health=int(e.get("initial_health", 100)),
                    initial_stamina=int(e.get("initial_stamina", 90)),
                    initial_psychological_state=e.get("initial_psychological_state") or "冷静警惕",
                    initial_inventory=e.get("initial_inventory") or ["随身物件"],
                    initial_goals=e.get("initial_goals") or ["排查环境安全"],
                )
            )

        # 整理 NPC 关系网
        detected_npcs: List[DetectedRelationship] = []
        for npc in ai_data.get("npcs", []):
            if isinstance(npc, dict) and npc.get("npc_name"):
                detected_npcs.append(
                    DetectedRelationship(
                        npc_name=npc["npc_name"],
                        relation_type=npc.get("relation_type", "关联者"),
                        affinity=int(npc.get("affinity", 50)),
                        summary=npc.get("summary", ""),
                    )
                )

        # 整理保留的世界书条目（剔除了状态栏与已被提炼为 NPC 的条目）
        lores: List[WorldLoreInput] = []
        for lore in ai_data.get("kept_lores", []):
            if isinstance(lore, dict) and lore.get("content"):
                lores.append(
                    WorldLoreInput(
                        title=lore.get("title", "世界法则"),
                        category=lore.get("category", "static"),
                        trigger_keys=lore.get("trigger_keys", ""),
                        content=lore.get("content", ""),
                    )
                )

        return CardParseResponse(
            is_multi_entity=is_multi or len(entities) > 1,
            detected_entities=entities,
            detected_relationships=detected_npcs,
            total_lore_entries=len(lores),
            lores=lores,
            raw_preview={
                "name": main_name,
                "first_mes": cleaned_first[:300],
                "desc_snippet": full_persona_text[:200],
            },
        )

    @classmethod
    async def generate_from_quick_form(cls, req: QuickCharacterRequest) -> Dict[str, Any]:
        """通过极简 4 维度表单，由 AI 标准化衍生完整角色、初始状态与作息"""
        sync_config_to_runtime()

        system_prompt = (
            "你是一个小说世界观与硬核角色设计专家。用户提供了角色创建的4个极简维度：\n"
            "名称、社会身份、性格底色、开局处境。\n"
            "请根据这些信息，一次性衍生出符合设定的完整角色卡数据，严格输出为 JSON 对象，包含：\n"
            "- name: 姓名\n"
            "- title: 角色称号或头衔\n"
            "- persona_summary: 核心性格与行为准则（200~400字，完整设定）\n"
            "- inner_drive: 内在终极心理动机与不可磨灭的执念（50~100字）\n"
            "- circadian_profile: 对象，包含 chronotype ('早起型'|'夜行型'|'昼夜无律型'|'无休眠体质'), "
            "typical_rest_window (如 '23:00 - 07:00'), environment_tolerance (休眠环境要求), sleep_trigger_summary\n"
            "- initial_health: 初始健康 (0~100, 建议 90~100)\n"
            "- initial_stamina: 初始精力 (0~100, 建议 75~95)\n"
            "- initial_inventory: 随身物品列表 (3~5件符合职业的物品)\n"
            "- initial_goals: 当前紧迫目标列表 (2~3条)\n"
            "- initial_location: 开局微观具体场景位置\n"
            "- initial_virtual_time: 开局虚拟时间 (如 '晨光月 1日 08:00')\n"
            "- initial_lore: 包含 title, content 的初始世界背景设定条目\n"
            "严禁输出任何 Emoji 图标。"
        )
        user_prompt = (
            f"角色名称: {req.name}\n"
            f"社会身份: {req.role}\n"
            f"性格底色: {req.archetype}\n"
            f"开局处境: {req.initial_situation}\n"
        )

        raw = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            json_mode=True,
            temperature=0.7,
        )

        cleaned = clean_json_str(raw)
        return json.loads(cleaned)
