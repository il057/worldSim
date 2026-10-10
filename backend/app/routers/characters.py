import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Character, CharacterState, StoryLog, WorldLore, CharacterRelationship
from app.schemas import (
    CharacterStateView,
    CharacterDetailView,
    TimelinePageResponse,
    StoryLogView,
    StoryLogUpdateRequest,
    ArbitratorDelta,
    CharacterRelationshipView,
    CircadianProfile,
)
from app.services.simulation import SimulationService, get_character_lock

router = APIRouter(prefix="/api/v1/characters", tags=["Characters"])


@router.get("", response_model=List[Dict[str, Any]])
def list_characters(db: Session = Depends(get_db)):
    """获取所有已激活角色简要列表"""
    chars = db.query(Character).filter(Character.is_active == 1).order_by(Character.created_at.desc()).all()
    res = []
    for c in chars:
        res.append({
            "id": c.id,
            "name": c.name,
            "title": c.title,
            "avatar_url": c.avatar_url,
            "created_at": c.created_at,
        })
    return res


@router.get("/{character_id}/state", response_model=CharacterStateView)
def get_character_state(character_id: str, db: Session = Depends(get_db)):
    """查询角色的 Living State 看板数值"""
    state = db.query(CharacterState).filter(CharacterState.character_id == character_id).first()
    if not state:
        raise HTTPException(status_code=404, detail="角色状态未找到")

    return CharacterStateView(
        id=state.id,
        character_id=state.character_id,
        virtual_time=state.virtual_time,
        location=state.location,
        health=state.health,
        stamina=state.stamina,
        is_sleeping=state.is_sleeping,
        psychological_state=state.psychological_state,
        inventory=json.loads(state.inventory_json) if state.inventory_json else [],
        active_goals=json.loads(state.active_goals_json) if state.active_goals_json else [],
        completed_goals=json.loads(state.completed_goals_json) if state.completed_goals_json else [],
        total_ticks=state.total_ticks,
        updated_at=state.updated_at,
    )


@router.get("/{character_id}/detail", response_model=CharacterDetailView)
def get_character_detail(character_id: str, db: Session = Depends(get_db)):
    """查询角色完整信息（人设、自适应作息、即时状态、NPC 关系网、世界书统计）"""
    char = db.query(Character).filter(Character.id == character_id).first()
    if not char:
        raise HTTPException(status_code=404, detail="未找到该角色")

    state = db.query(CharacterState).filter(CharacterState.character_id == character_id).first()
    state_view = None
    if state:
        state_view = CharacterStateView(
            id=state.id,
            character_id=state.character_id,
            virtual_time=state.virtual_time,
            location=state.location,
            health=state.health,
            stamina=state.stamina,
            is_sleeping=state.is_sleeping,
            psychological_state=state.psychological_state,
            inventory=json.loads(state.inventory_json) if state.inventory_json else [],
            active_goals=json.loads(state.active_goals_json) if state.active_goals_json else [],
            completed_goals=json.loads(state.completed_goals_json) if state.completed_goals_json else [],
            total_ticks=state.total_ticks,
            updated_at=state.updated_at,
        )

    # 提取作息画像
    try:
        circ_dict = json.loads(char.circadian_profile_json)
        circ_prof = CircadianProfile(**circ_dict)
    except Exception:
        circ_prof = CircadianProfile(
            chronotype="昼夜无律型",
            typical_rest_window="00:00 - 08:00",
            environment_tolerance="常规庇护所",
            sleep_trigger_summary="",
        )

    # 关系网
    npcs = db.query(CharacterRelationship).filter(CharacterRelationship.character_id == character_id).all()
    rel_views = [
        CharacterRelationshipView(
            id=n.id,
            npc_name=n.npc_name,
            relation_type=n.relation_type,
            affinity=n.affinity,
            summary=n.summary,
            is_present=n.is_present,
        )
        for n in npcs
    ]

    lore_count = db.query(WorldLore).filter(
        (WorldLore.character_id == character_id) | (WorldLore.character_id.is_(None))
    ).count()

    return CharacterDetailView(
        id=char.id,
        name=char.name,
        title=char.title,
        avatar_url=char.avatar_url,
        persona_summary=char.persona_summary,
        inner_drive=char.inner_drive,
        circadian_profile=circ_prof,
        is_active=char.is_active,
        state=state_view,
        relationships=rel_views,
        world_lores_count=lore_count,
    )


@router.get("/{character_id}/timeline", response_model=TimelinePageResponse)
def get_character_timeline(
    character_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """分页拉取小说正文切片流水（按 tick_index 正序排列）"""
    total = db.query(StoryLog).filter(StoryLog.character_id == character_id).count()
    offset = (page - 1) * page_size
    logs = (
        db.query(StoryLog)
        .filter(StoryLog.character_id == character_id)
        .order_by(StoryLog.tick_index.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = []
    for log in logs:
        try:
            delta_obj = ArbitratorDelta.model_validate_json(log.delta_snapshot_json)
        except Exception:
            delta_obj = None

        items.append(
            StoryLogView(
                id=log.id,
                character_id=log.character_id,
                tick_index=log.tick_index,
                virtual_time=log.virtual_time,
                location=log.location,
                plot_beat=log.plot_beat,
                narrative_prose=log.narrative_prose,
                delta_snapshot=delta_obj,
                created_at=log.created_at,
            )
        )

    return TimelinePageResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.put("/{character_id}/timeline/{log_id}", response_model=StoryLogView)
async def update_character_story_log(
    character_id: str,
    log_id: int,
    req: StoryLogUpdateRequest,
    db: Session = Depends(get_db),
):
    """更新指定故事切片的文学正文与事实骨架"""
    async with get_character_lock(character_id):
        log = SimulationService.update_story_log(
            db, character_id, log_id, req.narrative_prose, req.plot_beat
        )
        delta_obj = None
        try:
            delta_obj = ArbitratorDelta.model_validate_json(log.delta_snapshot_json)
        except Exception:
            pass

        return StoryLogView(
            id=log.id,
            character_id=log.character_id,
            tick_index=log.tick_index,
            virtual_time=log.virtual_time,
            location=log.location,
            plot_beat=log.plot_beat,
            narrative_prose=log.narrative_prose,
            delta_snapshot=delta_obj,
            created_at=log.created_at,
        )


@router.delete("/{character_id}/timeline/{log_id}")
async def delete_character_story_log(
    character_id: str,
    log_id: int,
    db: Session = Depends(get_db),
):
    """级联删除指定故事切片及其后续所有切片，并自动回滚世界状态"""
    async with get_character_lock(character_id):
        target_log = (
            db.query(StoryLog)
            .filter(StoryLog.id == log_id, StoryLog.character_id == character_id)
            .first()
        )
        if not target_log:
            raise HTTPException(status_code=404, detail="未找到该故事切片")

        target_tick = target_log.tick_index
        deleted_count = SimulationService.rollback_to_tick(db, character_id, target_tick)
        return {
            "message": f"第 {target_tick} 刻及后续切片已成功删除（共删除 {deleted_count} 刻），世界状态已同步回滚",
            "deleted_count": deleted_count,
            "rollback_to_tick": target_tick - 1,
        }


@router.post("/{character_id}/reset")
def reset_character_timeline(character_id: str, db: Session = Depends(get_db)):
    """重置当前角色世界：清空全部 story_logs，回滚状态"""
    SimulationService.reset_character(db, character_id)
    return {"message": "角色世界已成功重置"}


@router.delete("/{character_id}")
def delete_character(character_id: str, db: Session = Depends(get_db)):
    """彻底删除角色及所有关联数据（包括即时状态、故事切片长卷、专属世界书设定、NPC关系网）"""
    char = db.query(Character).filter(Character.id == character_id).first()
    if not char:
        raise HTTPException(status_code=404, detail="未找到该角色")

    char_name = char.name
    # 显式级联清理关联数据
    db.query(StoryLog).filter(StoryLog.character_id == character_id).delete()
    db.query(CharacterState).filter(CharacterState.character_id == character_id).delete()
    db.query(WorldLore).filter(WorldLore.character_id == character_id).delete()
    db.query(CharacterRelationship).filter(CharacterRelationship.character_id == character_id).delete()
    db.delete(char)
    db.commit()
    return {"message": f"角色【{char_name}】及其全部推演历程、即时状态与世界书已彻底删除"}


@router.get("/{character_id}/lores")
def list_character_lores(character_id: str, db: Session = Depends(get_db)):
    """获取角色的世界书条目列表"""
    lores = (
        db.query(WorldLore)
        .filter(
            (WorldLore.character_id == character_id) | (WorldLore.character_id.is_(None)),
            WorldLore.is_active == 1,
        )
        .order_by(WorldLore.id.desc())
        .all()
    )
    return [
        {
            "id": l.id,
            "category": l.category,
            "trigger_keys": l.trigger_keys,
            "title": l.title,
            "content": l.content,
            "is_active": l.is_active,
        }
        for l in lores
    ]


@router.post("/{character_id}/lores")
def create_character_lore(character_id: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """新建世界书条目"""
    lore = WorldLore(
        character_id=character_id,
        category=payload.get("category", "static"),
        trigger_keys=payload.get("trigger_keys", ""),
        title=payload.get("title", "未命名设定"),
        content=payload.get("content", ""),
        is_active=1,
    )
    db.add(lore)
    db.commit()
    db.refresh(lore)
    return {"id": lore.id, "message": "世界书条目已保存"}


@router.put("/{character_id}/lores/{lore_id}")
def update_character_lore(character_id: str, lore_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """更新/编辑世界书条目"""
    lore = (
        db.query(WorldLore)
        .filter(
            WorldLore.id == lore_id,
            (WorldLore.character_id == character_id) | (WorldLore.character_id.is_(None)),
        )
        .first()
    )
    if not lore:
        raise HTTPException(status_code=404, detail="世界书条目不存在")

    if "category" in payload and payload["category"] is not None:
        lore.category = payload["category"]
    if "trigger_keys" in payload and payload["trigger_keys"] is not None:
        lore.trigger_keys = payload["trigger_keys"]
    if "title" in payload and payload["title"] is not None:
        lore.title = payload["title"]
    if "content" in payload and payload["content"] is not None:
        lore.content = payload["content"]
    if "is_active" in payload and payload["is_active"] is not None:
        lore.is_active = payload["is_active"]

    db.commit()
    db.refresh(lore)
    return {
        "id": lore.id,
        "category": lore.category,
        "trigger_keys": lore.trigger_keys,
        "title": lore.title,
        "content": lore.content,
        "is_active": lore.is_active,
        "message": "世界书条目已更新",
    }


@router.delete("/{character_id}/lores/{lore_id}")
def delete_character_lore(character_id: str, lore_id: int, db: Session = Depends(get_db)):
    """删除世界书条目"""
    db.query(WorldLore).filter(WorldLore.id == lore_id).delete()
    db.commit()
    return {"message": "已删除该条目"}


@router.get("/system/config")
def get_system_config(db: Session = Depends(get_db)):
    """获取系统运行期 LLM 与沙盒配置（从数据库持久化存储读取）"""
    from app.services.config_service import get_all_system_configs
    cfg = get_all_system_configs(db)
    api_key = cfg.get("llm_api_key", "")
    return {
        "llm_base_url": cfg.get("llm_base_url", "https://api.openai.com/v1"),
        "llm_model_name": cfg.get("llm_model_name", "gpt-4o-mini"),
        "has_api_key": bool(api_key and not api_key.startswith("sk-xxxx")),
        "api_key_masked": api_key[:4] + "****" + api_key[-4:] if len(api_key) > 8 else ("****" if api_key else ""),
        "llm_context_window": int(cfg.get("llm_context_window", "60000")),
        "llm_temperature": float(cfg.get("llm_temperature", "1.0")),
        "llm_frequency_penalty": float(cfg.get("llm_frequency_penalty", "0.0")),
        "llm_presence_penalty": float(cfg.get("llm_presence_penalty", "0.0")),
        "llm_top_p": float(cfg.get("llm_top_p", "1.0")),
        "enable_realtime_sync": cfg.get("enable_realtime_sync", "false").lower() == "true",
        "realtime_tick_hours": int(cfg.get("realtime_tick_hours", "1")),
        "enable_stream_display": cfg.get("enable_stream_display", "true").lower() == "true",
        "enable_phone_simulation": cfg.get("enable_phone_simulation", "false").lower() == "true",
        "theme_mode": cfg.get("theme_mode", "light"),
        "theme_color": cfg.get("theme_color", "#5e72e4"),
    }


@router.post("/system/config")
def update_system_config(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """更新系统运行期 LLM 与沙盒配置并持久化至数据库"""
    from app.config import settings
    from app.services.config_service import save_system_configs, get_all_system_configs
    from app.services.scheduler import update_scheduler_job

    updates = {}
    if "llm_base_url" in payload and payload["llm_base_url"] is not None:
        updates["llm_base_url"] = payload["llm_base_url"].strip()
    
    # 只有当用户显式输入了非空 API Key 时才更新，避免保存时冲掉已存 Key
    if "llm_api_key" in payload and payload["llm_api_key"] is not None and str(payload["llm_api_key"]).strip() != "":
        updates["llm_api_key"] = str(payload["llm_api_key"]).strip()
    elif payload.get("clear_api_key") is True:
        updates["llm_api_key"] = ""

    if "llm_model_name" in payload and payload["llm_model_name"] is not None:
        updates["llm_model_name"] = str(payload["llm_model_name"]).strip()

    if "llm_context_window" in payload and payload["llm_context_window"] is not None:
        updates["llm_context_window"] = str(payload["llm_context_window"])

    if "llm_temperature" in payload and payload["llm_temperature"] is not None:
        updates["llm_temperature"] = str(payload["llm_temperature"])

    if "llm_frequency_penalty" in payload and payload["llm_frequency_penalty"] is not None:
        updates["llm_frequency_penalty"] = str(payload["llm_frequency_penalty"])

    if "llm_presence_penalty" in payload and payload["llm_presence_penalty"] is not None:
        updates["llm_presence_penalty"] = str(payload["llm_presence_penalty"])

    if "llm_top_p" in payload and payload["llm_top_p"] is not None:
        updates["llm_top_p"] = str(payload["llm_top_p"])

    if "enable_realtime_sync" in payload and payload["enable_realtime_sync"] is not None:
        updates["enable_realtime_sync"] = "true" if payload["enable_realtime_sync"] else "false"

    if "realtime_tick_hours" in payload and payload["realtime_tick_hours"] is not None:
        updates["realtime_tick_hours"] = str(payload["realtime_tick_hours"])
        settings.REALTIME_TICK_HOURS = max(1, int(payload["realtime_tick_hours"]))

    if "enable_stream_display" in payload and payload["enable_stream_display"] is not None:
        updates["enable_stream_display"] = "true" if payload["enable_stream_display"] else "false"

    if "enable_phone_simulation" in payload and payload["enable_phone_simulation"] is not None:
        updates["enable_phone_simulation"] = "true" if payload["enable_phone_simulation"] else "false"

    if "theme_mode" in payload and payload["theme_mode"] is not None:
        updates["theme_mode"] = str(payload["theme_mode"]).strip()

    if "theme_color" in payload and payload["theme_color"] is not None:
        updates["theme_color"] = str(payload["theme_color"]).strip()

    save_system_configs(updates, db)

    # 动态热更新或启停后台现实同步演化调度任务
    cfg_all = get_all_system_configs(db)
    is_sync_enabled = cfg_all.get("enable_realtime_sync", "false").lower() == "true"
    try:
        tick_hours = max(1, int(cfg_all.get("realtime_tick_hours", "1")))
    except ValueError:
        tick_hours = 1
    update_scheduler_job(enabled=is_sync_enabled, hours=tick_hours)

    return {"message": "系统配置已成功保存至数据库并即时生效"}


@router.post("/system/fetch-models")
async def fetch_system_models(payload: Dict[str, Any] = Body(default={}), db: Session = Depends(get_db)):
    """根据输入的 Base URL 与 API Key，向远程接口拉取可用模型列表"""
    from app.services.config_service import get_all_system_configs
    from app.services.llm_client import LLMClient

    cfg = get_all_system_configs(db)
    base_url = (payload.get("llm_base_url") or cfg.get("llm_base_url") or "https://api.openai.com/v1").strip()
    api_key = payload.get("llm_api_key")
    if not api_key or str(api_key).strip() == "":
        api_key = cfg.get("llm_api_key", "")
    else:
        api_key = str(api_key).strip()

    try:
        models = await LLMClient.fetch_models(base_url, api_key)
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


