import json
import uuid
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Character, CharacterState, WorldLore, CharacterRelationship
from app.schemas import (
    CardParseResponse,
    CardImportRequest,
    QuickCharacterRequest,
    CharacterDetailView,
)
from app.services.ingestion import IngestionService

router = APIRouter(prefix="/api/v1", tags=["Cards & Characters Ingestion"])


@router.post("/cards/parse", response_model=CardParseResponse)
async def parse_card(file: UploadFile = File(...)):
    """上传酒馆角色卡文件 (JSON / PNG 格式)，后端执行正则剥离、头像提取与多实体识别"""
    try:
        content_bytes = await file.read()
        avatar_data_url = None
        data = None

        # 1. 尝试作为 PNG 解析
        if content_bytes.startswith(b"\x89PNG\r\n\x1a\n") or (file.filename and file.filename.lower().endswith(".png")):
            data, avatar_data_url = IngestionService.extract_png_data(content_bytes)

        # 2. 若未从 PNG 中提取到数据，尝试直接作为 JSON 读取
        if not data:
            try:
                data = json.loads(content_bytes.decode("utf-8"))
            except Exception:
                # 尝试正则匹配 JSON 块
                import re
                text_decoded = content_bytes.decode("latin-1", errors="ignore")
                json_matches = re.findall(r'(\{"(?:name|spec|data)"[\s\S]*?\})', text_decoded)
                if json_matches:
                    data = json.loads(json_matches[0])
                else:
                    raise HTTPException(status_code=400, detail="未能识别角色卡有效数据（支持标准 JSON 或内嵌酒馆数据的 PNG）")

        parse_result = await IngestionService.parse_character_card(data, avatar_data_url=avatar_data_url)
        return parse_result
    except Exception as e:
        import logging
        logging.getLogger("world_sim.cards").error(f"[Card Parse Error] {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"角色卡 AI 深度解析失败: {str(e)}")


@router.post("/cards/import", response_model=Dict[str, Any], status_code=201)
async def import_card(req: CardImportRequest, db: Session = Depends(get_db)):
    """用户选定 POV 主角后执行落库，次要实体自动降维为 NPC 关系网"""
    selected = req.selected_entity
    char_id = f"c-{uuid.uuid4().hex[:8]}"

    new_char = Character(
        id=char_id,
        name=selected.name,
        title=selected.title or "漫游者",
        avatar_url=selected.avatar_url,
        gender=selected.gender or "保密",
        birthday=selected.birthday or "",
        appearance=selected.appearance or "",
        persona_summary=selected.persona_summary,
        inner_drive=selected.inner_drive,
        circadian_profile_json=selected.circadian_profile.model_dump_json(),
        is_active=1,
    )
    db.add(new_char)

    # 初始状态（优先采用用户在前端微调的值，其次采用实体自适应提取的值）
    final_location = req.initial_location or selected.initial_location or "常驻安全据点"
    final_time = req.initial_virtual_time or selected.initial_virtual_time or "晨光月 1日 08:00"
    final_health = req.initial_health if req.initial_health is not None else (selected.initial_health or 100)
    final_stamina = req.initial_stamina if req.initial_stamina is not None else (selected.initial_stamina or 90)
    final_psycho = req.initial_psychological_state or selected.initial_psychological_state or "警惕且冷静"
    final_inventory = req.initial_inventory if req.initial_inventory is not None else (selected.initial_inventory or ["随身物件"])
    final_goals = req.initial_goals if req.initial_goals is not None else (selected.initial_goals or ["审视四周环境", "梳理关键线索"])

    init_state = CharacterState(
        character_id=char_id,
        virtual_time=final_time,
        location=final_location,
        health=max(0, min(100, final_health)),
        stamina=max(0, min(100, final_stamina)),
        is_sleeping=0,
        psychological_state=final_psycho,
        inventory_json=json.dumps(final_inventory, ensure_ascii=False),
        active_goals_json=json.dumps(final_goals, ensure_ascii=False),
        completed_goals_json="[]",
        total_ticks=0,
    )
    db.add(init_state)

    # 导入世界书设定条目
    for lore in req.lores:
        db.add(
            WorldLore(
                character_id=char_id,
                category=lore.category,
                trigger_keys=lore.trigger_keys,
                title=lore.title,
                content=lore.content,
                is_active=1,
            )
        )

    # 注入 NPC 关系网（优先采用前端微调传入的专属关系列表，其次采用选定实体的关系列表）
    persisted_npc_names = set()
    target_relationships = req.relationships if req.relationships else (selected.relationships or [])
    for rel in target_relationships:
        if rel.npc_name and rel.npc_name != selected.name and rel.npc_name not in persisted_npc_names:
            persisted_npc_names.add(rel.npc_name)
            db.add(
                CharacterRelationship(
                    character_id=char_id,
                    npc_name=rel.npc_name,
                    relation_type=rel.relation_type or "相识",
                    affinity=rel.affinity if rel.affinity is not None else 50,
                    summary=rel.summary or "",
                    is_present=0,
                )
            )

    # 降维多人卡中未选中的次要主角实体为关联 NPC（防漏保护，优先继承专属好感与评价）
    for entity in req.all_entities:
        if entity.entity_id != selected.entity_id and entity.name != selected.name and entity.name not in persisted_npc_names:
            persisted_npc_names.add(entity.name)
            found_rel = next((r for r in (selected.relationships or []) if r.npc_name == entity.name), None)
            rel_type = found_rel.relation_type if found_rel else "主要同行者"
            rel_aff = found_rel.affinity if found_rel else 50
            rel_sum = found_rel.summary if (found_rel and found_rel.summary) else entity.persona_summary
            db.add(
                CharacterRelationship(
                    character_id=char_id,
                    npc_name=entity.name,
                    relation_type=rel_type,
                    affinity=rel_aff,
                    summary=rel_sum,
                    is_present=0,
                )
            )

    # 保存全量开局设置快照，供重置历史时 100% 还原开局原始生态
    initial_snapshot = {
        "gender": selected.gender or "保密",
        "birthday": selected.birthday or "",
        "appearance": selected.appearance or "",
        "virtual_time": final_time,
        "location": final_location,
        "health": max(0, min(100, final_health)),
        "stamina": max(0, min(100, final_stamina)),
        "is_sleeping": 0,
        "psychological_state": final_psycho,
        "inventory": final_inventory,
        "active_goals": final_goals,
        "initial_npc_names": list(persisted_npc_names),
    }
    new_char.initial_snapshot_json = json.dumps(initial_snapshot, ensure_ascii=False)

    db.commit()
    db.refresh(new_char)

    return {
        "character_id": new_char.id,
        "name": new_char.name,
        "message": "角色卡导入与降维落库完成",
    }


@router.post("/characters/generate-quick", response_model=Dict[str, Any], status_code=201)
async def generate_quick_character(req: QuickCharacterRequest, db: Session = Depends(get_db)):
    """极简表单（4 维度）通过 AI 一键衍生全套标准化角色实体、状态与作息"""
    gen_data = await IngestionService.generate_from_quick_form(req)

    char_id = f"c-{uuid.uuid4().hex[:8]}"
    circadian_data = gen_data.get("circadian_profile", {})

    new_char = Character(
        id=char_id,
        name=gen_data.get("name", req.name),
        title=gen_data.get("title", req.role),
        avatar_url="",
        persona_summary=gen_data.get("persona_summary", req.archetype),
        inner_drive=gen_data.get("inner_drive", "在危机中维持生存。"),
        circadian_profile_json=json.dumps(circadian_data, ensure_ascii=False),
        is_active=1,
    )
    db.add(new_char)

    # 初始状态
    init_state = CharacterState(
        character_id=char_id,
        virtual_time=gen_data.get("initial_virtual_time", "晨光月 1日 08:00"),
        location=gen_data.get("initial_location", "荒原旧废墟据点"),
        health=gen_data.get("initial_health", 100),
        stamina=gen_data.get("initial_stamina", 85),
        is_sleeping=0,
        psychological_state="沉着审慎",
        inventory_json=json.dumps(gen_data.get("initial_inventory", ["行囊", "折刀"]), ensure_ascii=False),
        active_goals_json=json.dumps(gen_data.get("initial_goals", ["排查周边动静"]), ensure_ascii=False),
        completed_goals_json="[]",
        total_ticks=0,
    )
    db.add(init_state)

    # 附带的世界书条目
    lore_entry = gen_data.get("initial_lore")
    if lore_entry and isinstance(lore_entry, dict):
        db.add(
            WorldLore(
                character_id=char_id,
                category="static",
                trigger_keys="",
                title=lore_entry.get("title", "世界法则背景"),
                content=lore_entry.get("content", ""),
                is_active=1,
            )
        )

    new_char.initial_snapshot_json = json.dumps({
        "virtual_time": gen_data.get("initial_virtual_time", "2024年10月9日 08:00"),
        "location": gen_data.get("initial_location", "荒原旧废墟据点"),
        "health": gen_data.get("initial_health", 100),
        "stamina": gen_data.get("initial_stamina", 85),
        "is_sleeping": 0,
        "psychological_state": "沉着审慎",
        "inventory": gen_data.get("initial_inventory", ["行囊", "折刀"]),
        "active_goals": gen_data.get("initial_goals", ["排查周边动静"]),
        "initial_npc_names": [],
    }, ensure_ascii=False)

    db.commit()
    db.refresh(new_char)

    return {
        "character_id": new_char.id,
        "name": new_char.name,
        "message": "AI 标准化角色快速衍生创建完成",
    }
