import asyncio
import json
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.models import Character, CharacterState, StoryLog, WorldLore, CharacterRelationship
from app.schemas import (
    ArbitratorDelta,
    CharacterStateView,
    StoryLogView,
    StepTickResponse,
    RestDecision,
    InventoryDelta,
    GoalDelta,
    SimulationPromptConfig,
)
from app.services.arbitrator import ArbitratorService
from app.services.storyteller import StorytellerService
from app.services.llm_client import llm_client, strip_emojis

logger = logging.getLogger("world_sim.simulation")

# 角色级别的并发互斥锁字典
_character_locks: Dict[str, asyncio.Lock] = {}


def get_character_lock(character_id: str) -> asyncio.Lock:
    if character_id not in _character_locks:
        _character_locks[character_id] = asyncio.Lock()
    return _character_locks[character_id]


def _apply_tick_delta(db: Session, character: Character, state: CharacterState, delta: ArbitratorDelta) -> None:
    """原子更新状态看板、背包、目标以及人际关系网"""
    state.virtual_time = delta.new_virtual_time
    state.location = delta.new_location
    state.health = max(0, min(100, state.health + delta.health_delta))
    state.stamina = max(0, min(100, state.stamina + delta.stamina_delta))
    state.is_sleeping = 1 if delta.rest_decision.is_sleeping else 0
    state.psychological_state = delta.psychological_change
    state.total_ticks += 1

    # 背包更新
    curr_inv = json.loads(state.inventory_json) if state.inventory_json else []
    for item in delta.inventory_delta.added:
        if item not in curr_inv:
            curr_inv.append(item)
    for item in delta.inventory_delta.removed:
        if item in curr_inv:
            curr_inv.remove(item)
    state.inventory_json = json.dumps(curr_inv, ensure_ascii=False)

    # 目标更新
    curr_goals = delta.goal_delta.current_active
    comp_goals = json.loads(state.completed_goals_json) if state.completed_goals_json else []
    for cg in delta.goal_delta.completed:
        if cg not in comp_goals:
            comp_goals.append(cg)
        if cg in curr_goals:
            curr_goals.remove(cg)
    state.active_goals_json = json.dumps(curr_goals, ensure_ascii=False)
    state.completed_goals_json = json.dumps(comp_goals, ensure_ascii=False)

    # 人际关系网动态更新
    if delta.relationship_delta:
        # 1. 结识新 NPC（仅限有深刻印象且有后续交集的角色）
        for n_item in delta.relationship_delta.new_npcs:
            if not n_item.npc_name or not n_item.npc_name.strip():
                continue
            name_clean = n_item.npc_name.strip()
            existing_npc = db.query(CharacterRelationship).filter(
                CharacterRelationship.character_id == character.id,
                CharacterRelationship.npc_name == name_clean,
            ).first()
            if not existing_npc:
                new_rel = CharacterRelationship(
                    character_id=character.id,
                    npc_name=name_clean,
                    relation_type=n_item.relation_type or "新结识",
                    affinity=max(0, min(100, n_item.affinity)),
                    summary=n_item.summary or "",
                    is_present=1 if n_item.is_present else 0,
                )
                db.add(new_rel)
                logger.info(f"[NPC动态结识] 角色 {character.name} 结识了新角色: {name_clean} ({n_item.relation_type})")
            else:
                existing_npc.is_present = 1 if n_item.is_present else 0
                if n_item.summary:
                    existing_npc.summary = n_item.summary

        # 2. 更新已有 NPC 的好感、状态与在场
        for u_item in delta.relationship_delta.updated_npcs:
            if not u_item.npc_name or not u_item.npc_name.strip():
                continue
            name_clean = u_item.npc_name.strip()
            existing_npc = db.query(CharacterRelationship).filter(
                CharacterRelationship.character_id == character.id,
                CharacterRelationship.npc_name == name_clean,
            ).first()
            if existing_npc:
                existing_npc.affinity = max(0, min(100, u_item.affinity))
                existing_npc.is_present = 1 if u_item.is_present else 0
                if u_item.summary:
                    existing_npc.summary = u_item.summary
                if u_item.relation_type:
                    existing_npc.relation_type = u_item.relation_type


class SimulationService:
    @classmethod
    async def run_step(
        cls,
        db: Session,
        character_id: str,
        hours: int = 1,
        forced_incident_prompt: Optional[str] = None,
        config: Optional[SimulationPromptConfig] = None,
    ) -> StepTickResponse:
        """
        单步微步进或突发事件驱动步进
        获取互斥锁 -> Pass 1 裁决 -> 更新状态看板 -> Pass 2 撰写正文 -> 落库
        """
        lock = get_character_lock(character_id)
        async with lock:
            character = db.query(Character).filter(Character.id == character_id).first()
            if not character:
                raise ValueError(f"未找到角色: {character_id}")

            state = db.query(CharacterState).filter(CharacterState.character_id == character_id).first()
            if not state:
                raise ValueError(f"未找到角色状态看板: {character_id}")

            try:
                # 1. 执行 Pass 1: 理性裁决
                delta: ArbitratorDelta = await ArbitratorService.decide_tick(
                    db=db,
                    character=character,
                    state=state,
                    hours_passed=hours,
                    forced_incident_prompt=forced_incident_prompt,
                    config=config,
                )

                # 2. 执行 Pass 2: 纯文学场景切片撰写
                # 注意：Pass 2 必须在任何数据库状态持久化之前执行，确保两步任一失败绝不入库
                narrative_prose: str = await StorytellerService.narrate_tick(
                    db=db,
                    character=character,
                    state=state,
                    delta=delta,
                    config=config,
                )

                # 3. 两步推演均成功！统一原子更新状态看板、背包、目标与人际关系网
                _apply_tick_delta(db, character, state, delta)

                # 写入 story_logs
                new_log = StoryLog(
                    character_id=character.id,
                    tick_index=state.total_ticks,
                    virtual_time=state.virtual_time,
                    location=state.location,
                    plot_beat=delta.plot_beat,
                    narrative_prose=narrative_prose,
                    delta_snapshot_json=delta.model_dump_json(),
                )
                db.add(new_log)
                db.commit()
                db.refresh(state)
                db.refresh(new_log)
            except Exception as e:
                db.rollback()
                logger.error(
                    f"[推演失败·终端报错] 角色 {character_id} 的推演事务已自动回滚，数据库未录入任何数据。异常详情: {e}",
                    exc_info=True,
                )
                raise

            # 构建视图响应
            state_view = CharacterStateView(
                id=state.id,
                character_id=state.character_id,
                virtual_time=state.virtual_time,
                location=state.location,
                health=state.health,
                stamina=state.stamina,
                is_sleeping=state.is_sleeping,
                psychological_state=state.psychological_state,
                inventory=json.loads(state.inventory_json),
                active_goals=json.loads(state.active_goals_json),
                completed_goals=json.loads(state.completed_goals_json),
                total_ticks=state.total_ticks,
                updated_at=state.updated_at,
            )

            log_view = StoryLogView(
                id=new_log.id,
                character_id=new_log.character_id,
                tick_index=new_log.tick_index,
                virtual_time=new_log.virtual_time,
                location=new_log.location,
                plot_beat=new_log.plot_beat,
                narrative_prose=new_log.narrative_prose,
                delta_snapshot=delta,
                created_at=new_log.created_at,
            )

            return StepTickResponse(
                character_id=character.id,
                story_log=log_view,
                current_state=state_view,
            )

    @classmethod
    async def fast_forward(
        cls,
        db: Session,
        character_id: str,
        step_type: str = "hour_6",
        config: Optional[SimulationPromptConfig] = None,
    ) -> StepTickResponse:
        """
        阶段快进（+6h 或 +24h）
        采用两阶段折叠算法：
        阶段 A: 粗粒度折叠宏观作息与编年史
        阶段 B: 最后 1 小时执行标准高精度双步推演
        """
        total_hours = 6 if step_type == "hour_6" else 24

        lock = get_character_lock(character_id)
        async with lock:
            character = db.query(Character).filter(Character.id == character_id).first()
            state = db.query(CharacterState).filter(CharacterState.character_id == character_id).first()
            if not character or not state:
                raise ValueError("角色或状态不存在")

            try:
                # 一次性推进完整跨度（6h 或 24h），生成唯一一条连贯充实的高保真故事切片
                delta: ArbitratorDelta = await ArbitratorService.decide_tick(
                    db=db,
                    character=character,
                    state=state,
                    hours_passed=total_hours,
                    config=config,
                )

                narrative_prose: str = await StorytellerService.narrate_tick(
                    db=db,
                    character=character,
                    state=state,
                    delta=delta,
                    config=config,
                )

                # 统一原子更新角色状态、背包、目标与人际关系网
                _apply_tick_delta(db, character, state, delta)

                # 持久化唯一的故事切片
                story_log = StoryLog(
                    character_id=character.id,
                    tick_index=state.total_ticks,
                    virtual_time=state.virtual_time,
                    location=state.location,
                    plot_beat=delta.plot_beat,
                    narrative_prose=narrative_prose,
                    delta_snapshot_json=delta.model_dump_json(),
                )
                db.add(story_log)
                db.commit()
                db.refresh(state)
                db.refresh(story_log)

                state_view = CharacterStateView(
                    id=state.id,
                    character_id=state.character_id,
                    virtual_time=state.virtual_time,
                    location=state.location,
                    health=state.health,
                    stamina=state.stamina,
                    is_sleeping=state.is_sleeping,
                    psychological_state=state.psychological_state,
                    inventory=json.loads(state.inventory_json),
                    active_goals=json.loads(state.active_goals_json),
                    completed_goals=json.loads(state.completed_goals_json),
                    total_ticks=state.total_ticks,
                    updated_at=state.updated_at,
                )

                log_view = StoryLogView(
                    id=story_log.id,
                    character_id=story_log.character_id,
                    tick_index=story_log.tick_index,
                    virtual_time=story_log.virtual_time,
                    location=story_log.location,
                    plot_beat=story_log.plot_beat,
                    narrative_prose=story_log.narrative_prose,
                    delta_snapshot=delta,
                    created_at=story_log.created_at,
                )

                return StepTickResponse(
                    character_id=character.id,
                    story_log=log_view,
                    current_state=state_view,
                )
            except Exception as e:
                db.rollback()
                logger.error(
                    f"[快进失败·终端报错] 角色 {character_id} 快进事务已自动回滚，数据库未录入任何数据: {e}",
                    exc_info=True,
                )
                raise

    @classmethod
    async def trigger_inciting_incident(
        cls,
        db: Session,
        character_id: str,
        config: Optional[SimulationPromptConfig] = None,
    ) -> StepTickResponse:
        """
        突发事件引擎：
        绝无用户输入，AI 结合当前时空、未解执念、世界书自主构思危机事件，送入 Pass 1
        """
        character = db.query(Character).filter(Character.id == character_id).first()
        state = db.query(CharacterState).filter(CharacterState.character_id == character_id).first()
        if not character or not state:
            raise ValueError("角色或状态不存在")

        system_prompt = (
            "你是一个虚拟世界突发事件（Inciting Incident）构思引擎。\n"
            "用户按下了【触发突发事件】按钮。请结合角色的身份、核心执念、当前所处物理地点与心理状态，"
            "自主构思一场突如其来的危机、奇遇或变故（如：仇家尾随堵门、异响预警、机关突发故障、带有密信的飞鸟、"
            "突降天灾或巡逻队突击搜查）。\n"
            "用 100~150 字扼要描述此突发变故的客观事实，具有强烈的因果张力。\n"
            "严禁包含任何 Emoji 图标。"
        )
        user_prompt = (
            f"主角姓名: {character.name} ({character.title})\n"
            f"核心执念: {character.inner_drive}\n"
            f"当前时空地点: {state.virtual_time} | {state.location}\n"
            f"当前状态: {'休眠中' if state.is_sleeping else '清醒活动'} | 心理: {state.psychological_state}\n"
            f"请构思这场突发变故："
        )

        incident_beat = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            json_mode=False,
            temperature=0.85,
        )

        incident_beat = strip_emojis(incident_beat.strip())
        logger.info(f"AI 自主构思突发事件: {incident_beat}")

        # 注入单步推演
        return await cls.run_step(db, character_id, hours=1, forced_incident_prompt=incident_beat, config=config)

    @classmethod
    def reset_character(cls, db: Session, character_id: str) -> None:
        """重置角色世界：清除全部故事流水，100% 还原至导入时保存的开局原始设置"""
        character = db.query(Character).filter(Character.id == character_id).first()
        state = db.query(CharacterState).filter(CharacterState.character_id == character_id).first()
        if not character or not state:
            return

        # 1. 彻底清空所有故事切片历史流水
        db.query(StoryLog).filter(StoryLog.character_id == character_id).delete()

        # 2. 从开局全量快照 initial_snapshot_json 恢复所有原始设置
        if character.initial_snapshot_json:
            try:
                snap = json.loads(character.initial_snapshot_json)
                state.virtual_time = snap.get("virtual_time") or state.virtual_time
                state.location = snap.get("location") or state.location
                state.health = snap.get("health", 100)
                state.stamina = snap.get("stamina", 90)
                state.is_sleeping = snap.get("is_sleeping", 0)
                state.psychological_state = snap.get("psychological_state") or "平静内敛"
                state.inventory_json = json.dumps(snap.get("inventory") or [], ensure_ascii=False)
                state.active_goals_json = json.dumps(snap.get("active_goals") or [], ensure_ascii=False)
                state.completed_goals_json = "[]"
                state.total_ticks = 0

                # 恢复初始社交网络生态：清理推演过程中动态新增的非初始 NPC
                init_npc_names = set(snap.get("initial_npc_names") or [])
                if init_npc_names:
                    all_npcs = db.query(CharacterRelationship).filter(CharacterRelationship.character_id == character_id).all()
                    for npc in all_npcs:
                        if npc.npc_name not in init_npc_names:
                            db.delete(npc)
                        else:
                            npc.is_present = 0  # 恢复开局默认现场状态
            except Exception as e:
                logger.error(f"解析角色初始快照异常: {e}")
        else:
            # 兜底防御：绝不硬编码虚假日期与道具，保留原始时间和地点，清理临时状态
            state.health = 100
            state.stamina = 90
            state.is_sleeping = 0
            state.completed_goals_json = "[]"
            state.total_ticks = 0

        db.commit()
        db.refresh(state)
        logger.info(f"角色【{character.name}】历史已成功清空，已恢复至开局全量原始设置")
