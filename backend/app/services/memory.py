import json
import logging
from typing import List, Dict, Any, Optional
import jieba
from sqlalchemy.orm import Session
from app.models import Character, CharacterState, StoryLog, WorldLore, CharacterRelationship
from app.schemas import CircadianProfile

logger = logging.getLogger("world_sim.memory")


def calculate_dynamic_age(birthday_or_persona: str, current_virtual_time_str: str) -> Optional[int]:
    """基于虚拟世界当前时间与角色生日或档案，动态计算实时周岁"""
    import re
    if not current_virtual_time_str or not birthday_or_persona:
        return None

    curr_y_m = re.search(r"(\d{4})[年\-]", current_virtual_time_str)
    if not curr_y_m:
        return None
    curr_year = int(curr_y_m.group(1))

    # 优先匹配直接传入的生日格式
    direct_match = re.search(r"(\d{4})[年\-]", birthday_or_persona)
    if direct_match:
        birth_year = int(direct_match.group(1))
        if 0 < curr_year - birth_year < 200:
            return curr_year - birth_year

    birth_y_m = re.search(r"(?:诞生时间|生日|出生|诞生)[^\d\n]{0,12}(\d{4})[年\-]", birthday_or_persona)
    if not birth_y_m:
        birth_y_m = re.search(r"(\d{4})[年\-]\d{1,2}[月\-]\d{1,2}[日号]?", birthday_or_persona)

    if birth_y_m:
        birth_year = int(birth_y_m.group(1))
        if 0 < curr_year - birth_year < 200:
            return curr_year - birth_year

    return None


class MemoryService:
    @staticmethod
    def format_tier1_living_state(character: Character, state: CharacterState) -> str:
        """构建 Tier 1: Living State Sheet (即时生存状态看板) 提示词块"""
        try:
            profile_data = json.loads(character.circadian_profile_json)
        except Exception:
            profile_data = {}
        inventory = json.loads(state.inventory_json) if state.inventory_json else []
        active_goals = json.loads(state.active_goals_json) if state.active_goals_json else []
        completed_goals = json.loads(state.completed_goals_json) if state.completed_goals_json else []

        status_text = "【熟睡休眠中】" if state.is_sleeping else "【清醒活动中】"
        birthday_str = getattr(character, "birthday", "") or ""
        dynamic_age = calculate_dynamic_age(birthday_str or character.persona_summary, state.virtual_time)
        age_info = f" | 动态生理年龄: 实时周岁约 {dynamic_age} 岁 (随世界时间流逝自然增长)" if dynamic_age else ""
        gender_val = getattr(character, "gender", "") or "保密"
        appearance_val = getattr(character, "appearance", "") or "无特殊外貌记录"

        lines = [
            "=== [Tier 1: Living State Sheet (当前即时生存看板)] ===",
            f"主角姓名: {character.name} (头衔: {character.title or '无'}{age_info})",
            f"生理体征: 性别={gender_val} | 外貌特征={appearance_val}",
            f"虚拟时空: {state.virtual_time} | 当前微观地点: {state.location} | 当前安身据点/住所: {getattr(state, 'residence', '') or '四海漂泊/流浪途中'}",
            f"生理指标: 健康值 {state.health}/100 | 精力值 {state.stamina}/100 | 生理状态: {status_text}",
            f"心理情绪: {state.psychological_state}",
            f"自适应作息画像: 节律={profile_data.get('chronotype', '昼夜无律型')}, "
            f"倾向休眠窗口={profile_data.get('typical_rest_window', '无')}, "
            f"环境容忍度={profile_data.get('environment_tolerance', '普通室内')}",
            f"核心内在执念 (Inner Drive): {character.inner_drive}",
            f"随身物品背包 (当前容量 {len(inventory)}/8 件{'【严重超载，本次必须强制消耗/收纳/清理】' if len(inventory) >= 8 else ''}): {', '.join(inventory) if inventory else '空'}",
            f"当前推进目标: {', '.join(active_goals) if active_goals else '无明确短期目标'}",
            f"历史已达成目标: {', '.join(completed_goals[-3:]) if completed_goals else '无'}",
        ]
        return "\n".join(lines)

    @staticmethod
    def format_active_goals_block(state: CharacterState) -> str:
        """独立高亮格式化当前推进目标 (Active Goals)，作为驱动演化的核心依据"""
        goals = json.loads(state.active_goals_json) if state.active_goals_json else []
        if not goals:
            return "=== [当前推进目标 (Active Goals)] ===\n暂无明确具体目标，角色目前依据生存本能与核心执念行动。"
        items = "\n".join(f"- 【目标 {idx+1}】: {g}" for idx, g in enumerate(goals))
        return f"=== [当前推进目标 (Active Goals - 驱动核心)] ===\n{items}"

    @staticmethod
    def format_relationships_block(db: Session, character_id: str) -> str:
        """独立高亮格式化人际关系网与在场角色 (Relationships & NPCs)，作为社会交互核心"""
        npcs = (
            db.query(CharacterRelationship)
            .filter(
                CharacterRelationship.character_id == character_id,
                CharacterRelationship.is_archived == 0,
            )
            .all()
        )
        if not npcs:
            return "=== [人际关系网络与关联角色 (Relationships & NPCs)] ===\n主角当前独行，暂无活跃的已结识关键角色。"
        lines = [
            "=== [人际关系网络与关联角色 (Relationships & NPCs)] ===",
            "【空间与出场法则】: NPC 默认居于其常驻地。若其常驻地并非主角当前现场且其非‘同行者’，绝不可凭空出现在现场！居无定所/云游四海类角色仅在合乎情理的偶遇中现身。",
        ]
        for npc in npcs:
            pres = "【就在眼前同一现场】" if npc.is_present else "未在当前视线内"
            loc_desc = f"常驻地/活动范围: {npc.residence_location}" if npc.residence_location else "常驻地: 未标明"
            time_desc = f" | 最后交集: {npc.last_interacted_virtual_time}" if npc.last_interacted_virtual_time else ""
            lines.append(
                f"- {npc.npc_name} (关系: {npc.relation_type}, 好感度: {npc.affinity}/100, {loc_desc}{time_desc}, 现场状态: {pres})\n"
                f"  人物背景与对主角态度: {npc.summary}"
            )
        return "\n".join(lines)

    @staticmethod
    def get_tier2_working_buffer(db: Session, character_id: str, limit: int = 15) -> List[StoryLog]:
        """获取 Tier 2: Deep Working Buffer (最近 10~20 轮连续高精小说切片)"""
        return (
            db.query(StoryLog)
            .filter(StoryLog.character_id == character_id)
            .order_by(StoryLog.tick_index.desc())
            .limit(limit)
            .all()
        )[::-1]

    @staticmethod
    def format_tier2_working_buffer(logs: List[StoryLog]) -> str:
        """格式化 Working Buffer 供叙事机与裁决机感知近期细节"""
        if not logs:
            return "=== [Tier 2: Deep Working Buffer (前文上下文)] ===\n(目前为开局首轮，暂无前序小说切片)\n"

        chunks = ["=== [Tier 2: Deep Working Buffer (最近连续小说正文切片)] ==="]
        for log in logs:
            chunks.append(
                f"--- [Tick #{log.tick_index} | {log.virtual_time} | 地点: {log.location}] ---\n"
                f"【事实骨架】: {log.plot_beat}\n"
                f"【正文切片】: {log.narrative_prose}\n"
            )
        return "\n".join(chunks)

    @classmethod
    def get_tier3_lorebook_and_ledger(
        cls,
        db: Session,
        character_id: str,
        current_location: str,
        recent_text_context: str,
    ) -> str:
        """
        构建 Tier 3: 完整静态世界书 + 动态触发词激活世界书 + 历史长程账本倒排召回
        """
        # 1. 查询世界书
        all_lores = (
            db.query(WorldLore)
            .filter(
                (WorldLore.character_id == character_id) | (WorldLore.character_id.is_(None)),
                WorldLore.is_active == 1,
            )
            .all()
        )

        static_lores = []
        triggered_lores = []

        context_corpus = f"{current_location} {recent_text_context}"

        for lore in all_lores:
            if lore.category == "static" or not lore.trigger_keys:
                static_lores.append(lore)
            else:
                keys = [k.strip() for k in lore.trigger_keys.split(",") if k.strip()]
                if any(k in context_corpus for k in keys):
                    triggered_lores.append(lore)

        lore_sections = ["=== [Tier 3: 世界书与背景法则库 (Full Lorebook)] ==="]
        if static_lores:
            lore_sections.append("【常驻全局世界观法则】:")
            for lore in static_lores:
                lore_sections.append(f"《{lore.title}》:\n{lore.content}\n")
        if triggered_lores:
            lore_sections.append("【当前场景动态激活世界书】:")
            for lore in triggered_lores:
                lore_sections.append(f"《{lore.title}》 (触发词: {lore.trigger_keys}):\n{lore.content}\n")

        # 2. 社交 NPC 关系网
        npcs = db.query(CharacterRelationship).filter(CharacterRelationship.character_id == character_id).all()
        if npcs:
            lore_sections.append("【降维关联 NPC 状态与羁绊】:")
            for npc in npcs:
                pres = "在场" if npc.is_present else "未在同场景"
                lore_sections.append(f"- {npc.npc_name} (关系: {npc.relation_type}, 好感: {npc.affinity}, 状态: {pres}): {npc.summary}")

        # 3. 历史倒排召回（召回不在最近 Working Buffer 中的更早期重大事件）
        keywords = list(jieba.cut_for_search(context_corpus))
        # 过滤过短分词
        valid_kw = [k for k in keywords if len(k) > 1 and k not in ["角色", "当前", "这个", "那个", "时间", "地点"]][:6]

        if valid_kw:
            earlier_logs = (
                db.query(StoryLog)
                .filter(StoryLog.character_id == character_id)
                .order_by(StoryLog.tick_index.desc())
                .offset(15)  # 避开最近的 working buffer
                .limit(20)
                .all()
            )
            recalled_beats = []
            for elog in earlier_logs:
                for kw in valid_kw:
                    if kw in elog.plot_beat or kw in elog.location:
                        recalled_beats.append(f"[Tick #{elog.tick_index} | {elog.virtual_time}]: {elog.plot_beat}")
                        break

            if recalled_beats:
                lore_sections.append("【历史因果长程账本倒排回想 (Timeline Ledger)】:")
                for rb in recalled_beats[:5]:
                    lore_sections.append(f"- {rb}")

        return "\n".join(lore_sections)
