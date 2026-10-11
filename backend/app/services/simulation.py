import asyncio
import json
import logging
from typing import Dict, Optional
from fastapi import HTTPException
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
from app.services.memory import MemoryService
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
                raw_sum = (n_item.summary or "").strip()
                if raw_sum and "【对该角色的态度与羁绊】" not in raw_sum and "【态度】" not in raw_sum:
                    final_sum = f"{raw_sum}\n\n【对该角色的态度与羁绊】：新结识的关键角色，在当前变局中留下了深刻的相处印象。"
                else:
                    final_sum = raw_sum
                new_rel = CharacterRelationship(
                    character_id=character.id,
                    npc_name=name_clean,
                    relation_type=n_item.relation_type or "新结识",
                    affinity=max(-100, min(100, n_item.affinity)),
                    summary=final_sum,
                    is_present=1 if n_item.is_present else 0,
                )
                db.add(new_rel)
                logger.info(f"[NPC动态结识] 角色 {character.name} 结识了新角色: {name_clean} ({n_item.relation_type})")
            else:
                existing_npc.is_present = 1 if n_item.is_present else 0
                if n_item.summary:
                    new_s = n_item.summary.strip()
                    parts = re.split(r"【对该角色的态度与羁绊】[：:]?\s*", existing_npc.summary or "")
                    if len(parts) >= 2 and "【对该角色的态度与羁绊】" not in new_s and "【态度】" not in new_s:
                        existing_npc.summary = f"{parts[0].strip()}\n\n【对该角色的态度与羁绊】：{new_s}"
                    else:
                        existing_npc.summary = new_s

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
                existing_npc.affinity = max(-100, min(100, u_item.affinity))
                existing_npc.is_present = 1 if u_item.is_present else 0
                if u_item.summary:
                    new_s = u_item.summary.strip()
                    parts = re.split(r"【对该角色的态度与羁绊】[：:]?\s*", existing_npc.summary or "")
                    if len(parts) >= 2 and "【对该角色的态度与羁绊】" not in new_s and "【态度】" not in new_s:
                        existing_npc.summary = f"{parts[0].strip()}\n\n【对该角色的态度与羁绊】：{new_s}"
                    else:
                        existing_npc.summary = new_s
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
        is_continuation: bool = False,
    ) -> StepTickResponse:
        """
        单步微步进、自由续写或突发事件驱动步进
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
                    is_continuation=is_continuation,
                )

                # 2. 执行 Pass 2: 纯文学场景切片撰写
                # 注意：Pass 2 必须在任何数据库状态持久化之前执行，确保两步任一失败绝不入库
                narrative_prose: str = await StorytellerService.narrate_tick(
                    db=db,
                    character=character,
                    state=state,
                    delta=delta,
                    config=config,
                    is_continuation=is_continuation,
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
    async def run_step_stream(
        cls,
        db: Session,
        character_id: str,
        hours: int = 1,
        forced_incident_prompt: Optional[str] = None,
        config: Optional[SimulationPromptConfig] = None,
        is_continuation: bool = False,
    ):
        """
        单步微步进、自由续写或突发事件驱动的实时流式生成管线：
        1. Pass 1 理性世界物理与心理裁决；
        2. Pass 2 实时流式输出纯文学小说切片（通过异步队列分块吐出）；
        3. 事务性原子提交并落库；
        4. 吐出最终完整的 StepTickResponse 数据。
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
                yield {
                    "event": "status",
                    "data": {"stage": "pass1", "message": "【衡律之神】正在权衡因果法则与身心节律..."}
                }

                # 1. 执行 Pass 1: 理性裁决
                delta: ArbitratorDelta = await ArbitratorService.decide_tick(
                    db=db,
                    character=character,
                    state=state,
                    hours_passed=hours,
                    forced_incident_prompt=forced_incident_prompt,
                    config=config,
                    is_continuation=is_continuation,
                )

                yield {
                    "event": "pass1_done",
                    "data": {
                        "virtual_time": delta.new_virtual_time,
                        "location": delta.new_location,
                        "plot_beat": delta.plot_beat,
                        "is_sleeping": delta.rest_decision.is_sleeping,
                        "hours_passed": delta.simulated_hours_passed,
                    }
                }

                yield {
                    "event": "status",
                    "data": {"stage": "pass2", "message": "【见证之神】正在以有限视角编织时空切片..."}
                }

                # 2. 执行 Pass 2: 纯文学场景切片撰写（带流式队列回调）
                queue: asyncio.Queue = asyncio.Queue()

                async def chunk_listener(c: str):
                    await queue.put(c)

                async def background_narrate():
                    try:
                        return await StorytellerService.narrate_tick(
                            db=db,
                            character=character,
                            state=state,
                            delta=delta,
                            config=config,
                            on_chunk=chunk_listener,
                            is_continuation=is_continuation,
                        )
                    except Exception as err:
                        await queue.put(err)
                        raise
                    finally:
                        await queue.put(None)

                task = asyncio.create_task(background_narrate())

                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    if isinstance(item, Exception):
                        raise item
                    yield {
                        "event": "chunk",
                        "data": {"text": item, "delta": item}
                    }

                narrative_prose: str = await task

                # 3. 提交持久化
                _apply_tick_delta(db, character, state, delta)
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
                    f"[流式推演失败·终端报错] 角色 {character_id} 事务回滚: {e}",
                    exc_info=True,
                )
                raise

            # 4. 构建终态视图
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

            response = StepTickResponse(
                character_id=character.id,
                story_log=log_view,
                current_state=state_view,
            )

            yield {
                "event": "finish",
                "data": response.model_dump(mode="json")
            }

    @classmethod
    async def fast_forward_stream(
        cls,
        db: Session,
        character_id: str,
        step_type: str = "hour_6",
        config: Optional[SimulationPromptConfig] = None,
    ):
        """阶段快进实时流式输出"""
        hours = 6 if step_type == "hour_6" else 24
        async for evt in cls.run_step_stream(db, character_id, hours=hours, config=config):
            yield evt

    @classmethod
    async def continue_stream(
        cls,
        db: Session,
        character_id: str,
        config: Optional[SimulationPromptConfig] = None,
    ):
        """智能续写实时流式输出 (AI 自主决定时间尺度)"""
        async for evt in cls.run_step_stream(db, character_id, hours=1, config=config, is_continuation=True):
            yield evt

    @classmethod
    async def trigger_incident_stream(
        cls,
        db: Session,
        character_id: str,
        incident_description: Optional[str] = None,
        config: Optional[SimulationPromptConfig] = None,
    ):
        """突发事件实时流式输出 (支持用户指定事件或 AI 结合世界观自主衍生)"""
        character = db.query(Character).filter(Character.id == character_id).first()
        state = db.query(CharacterState).filter(CharacterState.character_id == character_id).first()
        if not character or not state:
            raise ValueError("角色或状态不存在")

        if incident_description and incident_description.strip():
            incident_beat = incident_description.strip()
            yield {
                "event": "status",
                "data": {"stage": "incident_conceive", "message": f"【变数之引】正在将突发变故注入因果: {incident_beat[:20]}..."}
            }
            logger.info(f"使用用户指定突发事件: {incident_beat}")
        else:
            yield {
                "event": "status",
                "data": {"stage": "incident_conceive", "message": "【变数之引】正在结合世界题材构思突发变故..."}
            }

            lore_context = MemoryService.get_tier3_lorebook_and_ledger(
                db, character.id, state.location, state.psychological_state
            )

            system_prompt = (
                "你是一个虚拟世界突发事件（Inciting Incident）构思引擎。\n"
                "你的任务是为当前虚拟世界构思一场契合题材背景与即时情境的意外变故、外部变数或情势转折。\n"
                "【题材自适应与合理性铁律（极重要）】:\n"
                "- 坚决杜绝脱离背景、千篇一律地编造激进的暗杀、杀手堵门、血腥复仇或致命阴谋！\n"
                "- 突发事件必须严密契合当前世界观题材（校园青春、都市日常、职场商战、古风修仙、科幻调查、公路旅行等）与微观现实情境：\n"
                "  * 校园日常/青春背景：突击检查、失物招领、突发雷阵雨导致滞留、黑板上的神秘留字、社团预算危机、同伴带来的意外传闻、尴尬撞破的小秘密等；\n"
                "  * 都市职场/现代背景：突发紧急工作传达、失联朋友发来离奇短讯、突发断电、错收的快递包裹、偶遇多年未见的故人、临时调派；\n"
                "  * 奇幻/修仙/悬疑/冒险背景：合理范围内的机关异响、突如其来的传讯符飞鸟、恶劣天气异变、意外闯入的求助者、遗迹禁制松动等；\n"
                "- 突发事件旨在打破当前稳态，为推演注入戏剧动力与真实波澜，而非为了制造冲突强行毁灭日常。\n"
                "- 用 80~140 字扼要描述此突发变故的客观事实，具备自然强烈的戏剧张力与因果潜能。\n"
                "- 严禁包含任何 Emoji 图标。"
            )
            user_prompt = (
                f"主角姓名: {character.name} ({character.title or '活动中'})\n"
                f"人设背景与性格底色: {character.persona_summary}\n"
                f"核心执念 (Inner Drive): {character.inner_drive}\n"
                f"当前时空地点: {state.virtual_time} | {state.location}\n"
                f"当前状态: {'休眠中' if state.is_sleeping else '清醒活动'} | 心理: {state.psychological_state}\n"
                f"{lore_context}\n"
                f"请结合以上题材世界观与即时情境，构思一场契合题材的突发变故："
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

        async for evt in cls.run_step_stream(
            db, character_id, hours=1, forced_incident_prompt=incident_beat, config=config
        ):
            yield evt

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
    async def run_continue(
        cls,
        db: Session,
        character_id: str,
        config: Optional[SimulationPromptConfig] = None,
    ) -> StepTickResponse:
        """智能续写（由 AI 自主判断合理时间切速与情节推进）"""
        return await cls.run_step(
            db,
            character_id,
            hours=1,
            config=config,
            is_continuation=True,
        )

    @classmethod
    async def trigger_inciting_incident(
        cls,
        db: Session,
        character_id: str,
        incident_description: Optional[str] = None,
        config: Optional[SimulationPromptConfig] = None,
    ) -> StepTickResponse:
        """
        突发事件引擎：
        支持用户指定事件或 AI 结合世界观题材自主衍生突发变故，送入 Pass 1
        """
        character = db.query(Character).filter(Character.id == character_id).first()
        state = db.query(CharacterState).filter(CharacterState.character_id == character_id).first()
        if not character or not state:
            raise ValueError("角色或状态不存在")

        if incident_description and incident_description.strip():
            incident_beat = incident_description.strip()
            logger.info(f"使用用户指定突发事件: {incident_beat}")
        else:
            lore_context = MemoryService.get_tier3_lorebook_and_ledger(
                db, character.id, state.location, state.psychological_state
            )

            system_prompt = (
                "你是一个虚拟世界突发事件（Inciting Incident）构思引擎。\n"
                "你的任务是为当前虚拟世界构思一场契合题材背景与即时情境的意外变故、外部变数或情势转折。\n"
                "【题材自适应与合理性铁律（极重要）】:\n"
                "- 坚决杜绝脱离背景、千篇一律地编造激进的暗杀、杀手堵门、血腥复仇或致命阴谋！\n"
                "- 突发事件必须严密契合当前世界观题材（校园青春、都市日常、职场商战、古风修仙、科幻调查、公路旅行等）与微观现实情境：\n"
                "  * 校园日常/青春背景：突击检查、失物招领、突发雷阵雨导致滞留、黑板上的神秘留字、社团预算危机、同伴带来的意外传闻、尴尬撞破的小秘密等；\n"
                "  * 都市职场/现代背景：突发紧急工作传达、失联朋友发来离奇短讯、突发断电、错收的快递包裹、偶遇多年未见的故人、临时调派；\n"
                "  * 奇幻/修仙/悬疑/冒险背景：合理范围内的机关异响、突如其来的传讯符飞鸟、恶劣天气异变、意外闯入的求助者、遗迹禁制松动等；\n"
                "- 突发事件旨在打破当前稳态，为推演注入戏剧动力与真实波澜，而非为了制造冲突强行毁灭日常。\n"
                "- 用 80~140 字扼要描述此突发变故的客观事实，具备自然强烈的戏剧张力与因果潜能。\n"
                "- 严禁包含任何 Emoji 图标。"
            )
            user_prompt = (
                f"主角姓名: {character.name} ({character.title or '活动中'})\n"
                f"人设背景与性格底色: {character.persona_summary}\n"
                f"核心执念 (Inner Drive): {character.inner_drive}\n"
                f"当前时空地点: {state.virtual_time} | {state.location}\n"
                f"当前状态: {'休眠中' if state.is_sleeping else '清醒活动'} | 心理: {state.psychological_state}\n"
                f"{lore_context}\n"
                f"请结合以上题材世界观与即时情境，构思一场契合题材的突发变故："
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

                # 恢复角色基础体征字段
                if snap.get("gender"):
                    character.gender = snap.get("gender")
                if snap.get("birthday"):
                    character.birthday = snap.get("birthday")
                if snap.get("appearance"):
                    character.appearance = snap.get("appearance")

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

    @classmethod
    def rollback_to_tick(cls, db: Session, character_id: str, target_tick: int) -> int:
        """回滚世界状态至 target_tick 之前，并级联删除 tick_index >= target_tick 的所有切片"""
        character = db.query(Character).filter(Character.id == character_id).first()
        state = db.query(CharacterState).filter(CharacterState.character_id == character_id).first()
        if not character or not state:
            return 0

        # 1. 查询保留的历史记录 (tick_index < target_tick)
        remaining_logs = (
            db.query(StoryLog)
            .filter(
                StoryLog.character_id == character_id,
                StoryLog.tick_index < target_tick,
            )
            .order_by(StoryLog.tick_index.asc())
            .all()
        )

        # 2. 统计并级联删除 >= target_tick 的所有切片
        deleted_count = (
            db.query(StoryLog)
            .filter(
                StoryLog.character_id == character_id,
                StoryLog.tick_index >= target_tick,
            )
            .delete()
        )

        # 3. 将角色状态及 NPC 关系还原至初始快照
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

                init_npc_names = set(snap.get("initial_npc_names") or [])
                if init_npc_names:
                    all_npcs = db.query(CharacterRelationship).filter(CharacterRelationship.character_id == character_id).all()
                    for npc in all_npcs:
                        if npc.npc_name not in init_npc_names:
                            db.delete(npc)
                        else:
                            npc.is_present = 0
            except Exception as e:
                logger.error(f"解析角色初始快照异常: {e}")
        else:
            state.health = 100
            state.stamina = 90
            state.is_sleeping = 0
            state.completed_goals_json = "[]"
            state.total_ticks = 0

        # 4. 依次重放所有保留切片的 delta，精确恢复至 target_tick - 1 刻的状态
        for log in remaining_logs:
            try:
                delta = ArbitratorDelta.model_validate_json(log.delta_snapshot_json)
                _apply_tick_delta(db, character, state, delta)
            except Exception as e:
                logger.error(f"重放日志 delta 失败 (tick {log.tick_index}): {e}")
                state.total_ticks = log.tick_index
                state.virtual_time = log.virtual_time
                state.location = log.location

        db.commit()
        db.refresh(state)
        logger.info(f"角色【{character.name}】已成功回滚至第 {target_tick - 1} 刻，级联删除 {deleted_count} 条故事切片")
        return deleted_count

    @classmethod
    def update_story_log(
        cls,
        db: Session,
        character_id: str,
        log_id: int,
        narrative_prose: str,
        plot_beat: Optional[str] = None,
    ) -> StoryLog:
        """更新指定故事切片的文学正文与事实骨架"""
        log = (
            db.query(StoryLog)
            .filter(StoryLog.id == log_id, StoryLog.character_id == character_id)
            .first()
        )
        if not log:
            raise HTTPException(status_code=404, detail="未找到该故事切片")

        log.narrative_prose = narrative_prose
        if plot_beat is not None:
            log.plot_beat = plot_beat

        db.commit()
        db.refresh(log)
        logger.info(f"故事切片 (ID: {log_id}, 第 {log.tick_index} 刻) 正文已更新")
        return log
