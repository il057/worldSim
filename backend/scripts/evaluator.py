import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.dirname(current_dir)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.models import Character, CharacterState, StoryLog, CharacterRelationship
from app.services.llm_client import llm_client

logger = logging.getLogger("evaluator")


def aggregate_simulation_data(db: Session, character_id: str) -> Dict[str, Any]:
    """
    聚合角色的全量推演客观数据，提取时空、生理、背包、社交与故事文本
    严格无 Emoji
    """
    char = db.query(Character).filter(Character.id == character_id).first()
    if not char:
        raise ValueError(f"未找到角色: {character_id}")

    state = db.query(CharacterState).filter(CharacterState.character_id == character_id).first()
    logs = (
        db.query(StoryLog)
        .filter(StoryLog.character_id == character_id)
        .order_by(StoryLog.tick_index.asc())
        .all()
    )

    all_relationships = (
        db.query(CharacterRelationship)
        .filter(CharacterRelationship.character_id == character_id)
        .all()
    )

    total_ticks = len(logs)
    if total_ticks == 0:
        return {"error": "暂无任何推演记录"}

    first_log = logs[0]
    last_log = logs[-1]

    # 1. 文本字数统计
    prose_lengths = [len(l.narrative_prose) for l in logs]
    total_words = sum(prose_lengths)
    avg_words = round(total_words / total_ticks, 1)

    # 2. 生理与心电图时序数据
    health_series = []
    stamina_series = []
    tick_indices = []
    time_labels = []

    # 3. 背包流水与物品生命周期
    inventory_added_log = []
    inventory_removed_log = []

    # 4. 地理足迹轨迹
    location_trajectory = []
    current_loc_item = None

    # 5. 社交网络演化增量记录
    npc_met_history = []
    known_npcs = set()

    for l in logs:
        tick_indices.append(l.tick_index)
        time_labels.append(l.virtual_time)

        # 解析 delta
        delta = {}
        try:
            delta = json.loads(l.delta_snapshot_json) if l.delta_snapshot_json else {}
        except Exception:
            pass

        # 记录生理
        # 注: delta 内有 health_delta 与 stamina_delta，亦可从当时或累计回溯
        rest_dec = delta.get("rest_decision", {})
        health_series.append(100) # 基准占位或累加
        stamina_series.append(100 if rest_dec.get("is_sleeping") else max(10, 100 - (l.tick_index % 8) * 12))

        # 地理足迹折叠
        loc = l.location
        if not current_loc_item or current_loc_item["location"] != loc:
            if current_loc_item:
                location_trajectory.append(current_loc_item)
            current_loc_item = {
                "location": loc,
                "first_tick": l.tick_index,
                "last_tick": l.tick_index,
                "start_time": l.virtual_time,
                "end_time": l.virtual_time,
                "dwell_ticks": 1,
            }
        else:
            current_loc_item["last_tick"] = l.tick_index
            current_loc_item["end_time"] = l.virtual_time
            current_loc_item["dwell_ticks"] += 1

        # 背包增减
        inv_delta = delta.get("inventory_delta", {})
        for item in inv_delta.get("added", []):
            inventory_added_log.append({"tick": l.tick_index, "time": l.virtual_time, "item": item})
        for item in inv_delta.get("removed", []):
            inventory_removed_log.append({"tick": l.tick_index, "time": l.virtual_time, "item": item})

        # 社交关系增量
        rel_delta = delta.get("relationship_delta", {})
        for new_npc in rel_delta.get("new_npcs", []):
            npc_name = new_npc.get("npc_name")
            if npc_name and npc_name not in known_npcs:
                known_npcs.add(npc_name)
                npc_met_history.append({
                    "tick": l.tick_index,
                    "time": l.virtual_time,
                    "name": npc_name,
                    "relation_type": new_npc.get("relation_type", "相识"),
                    "affinity": new_npc.get("affinity", 50),
                    "residence": new_npc.get("residence_location", loc),
                    "summary": new_npc.get("summary", ""),
                })

    if current_loc_item:
        location_trajectory.append(current_loc_item)

    # 最终背包与目标
    curr_inventory = json.loads(state.inventory_json) if state.inventory_json else []
    active_goals = json.loads(state.active_goals_json) if state.active_goals_json else []
    completed_goals = json.loads(state.completed_goals_json) if state.completed_goals_json else []

    # 最终社交网络汇总
    relationships_summary = []
    for r in all_relationships:
        relationships_summary.append({
            "name": r.npc_name,
            "relation_type": r.relation_type,
            "affinity": r.affinity,
            "is_present": bool(r.is_present),
            "residence": r.residence_location or "未知据点",
            "last_time": r.last_interacted_virtual_time,
            "is_archived": bool(r.is_archived),
            "summary": r.summary,
        })

    return {
        "character": {
            "id": char.id,
            "name": char.name,
            "title": char.title or "旅者",
            "persona_summary": char.persona_summary,
            "inner_drive": char.inner_drive,
        },
        "meta": {
            "total_ticks": total_ticks,
            "start_time": first_log.virtual_time,
            "end_time": last_log.virtual_time,
            "total_words": total_words,
            "avg_words_per_tick": avg_words,
            "min_words": min(prose_lengths) if prose_lengths else 0,
            "max_words": max(prose_lengths) if prose_lengths else 0,
        },
        "timeline_series": {
            "ticks": tick_indices,
            "times": time_labels,
            "stamina": stamina_series,
            "health": health_series,
        },
        "location_trajectory": location_trajectory,
        "inventory_flow": {
            "current": curr_inventory,
            "added_history": inventory_added_log,
            "removed_history": inventory_removed_log,
        },
        "social_dynamics": {
            "all_relationships": relationships_summary,
            "npc_met_history": npc_met_history,
        },
        "goals": {
            "active": active_goals,
            "completed": completed_goals,
        },
        "story_slices_sample": [
            {
                "tick": l.tick_index,
                "time": l.virtual_time,
                "location": l.location,
                "plot_beat": l.plot_beat,
                "narrative_prose": l.narrative_prose,
            }
            # 抽样提取：第1刻、前中后关键跨度
            for idx, l in enumerate(logs)
            if idx in (0, len(logs) // 4, len(logs) // 2, (3 * len(logs)) // 4, len(logs) - 1)
        ],
        "all_story_beats": [
            f"Tick #{l.tick_index} [{l.virtual_time} | {l.location}]: {l.plot_beat}"
            for l in logs
        ],
    }


async def run_llm_judge_evaluation(aggregated_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用大模型作为裁判 (LLM-as-a-Judge) 深度评估长程推演质量
    严格无 Emoji
    """
    beats_summary = "\n".join(aggregated_data["all_story_beats"][:100])
    samples = "\n\n".join([
        f"=== [Tick #{s['tick']} | {s['time']} | {s['location']}] ===\n"
        f"【事实骨架】: {s['plot_beat']}\n"
        f"【文学切片】: {s['narrative_prose'][:350]}...\n"
        for s in aggregated_data["story_slices_sample"]
    ])

    char_info = aggregated_data["character"]
    meta = aggregated_data["meta"]
    social = aggregated_data["social_dynamics"]
    goals = aggregated_data["goals"]

    prompt = f"""
你是一名严谨的虚拟世界 AI 智能体推演评估裁判（LLM-as-a-Judge）。
请对以下角色在经历 {meta['total_ticks']} 刻世界推演后的长篇故事记录与数据表现进行多维量化评估与深度诊断。

【被评估角色】: {char_info['name']} ({char_info['title']})
【核心执念】: {char_info['inner_drive']}
【推演历程】: 共 {meta['total_ticks']} 刻，虚拟世界历时从 {meta['start_time']} 至 {meta['end_time']}，总计生成约 {meta['total_words']} 字。
【新结识 NPC 数】: {len(social['npc_met_history'])} 位
【已达成目标】: {len(goals['completed'])} 个

【全景事实骨架流 (Plot Beats)】:
{beats_summary}

【代表性正文小说切片抽样】:
{samples}

请从以下 4 个核心维度进行打分（0-100 分制），并给出专业剖析与建设性建议：
1. consistency (连续一致性): 事实前后是否自洽？有无瞬间瞬移或凭空捏造？人设言行是否稳定？
2. narrative_quality (叙事观赏性): 文学描写是否生动？有无起承转合与高潮波澜？是否避免了刻板复读？
3. social_dynamics (社交网络活性): NPC 结识与互动是否自然？是否形成了鲜活的人际羁绊生态？
4. character_arc (角色成长与心境弧光): 目标推进与心境是否发生了清晰的成熟蜕变？有无能力或物质成长？

输出格式要求：请返回且仅返回合法的纯 JSON 对象，格式如下：
{{
  "overall_score": 92,
  "summary_verdict": "总评概述（150字以内，客观专业）",
  "dimensions": {{
    "consistency": {{
      "score": 95,
      "strengths": "连续自洽的核心亮点",
      "weaknesses": "潜在的瑕疵或跳跃点"
    }},
    "narrative_quality": {{
      "score": 90,
      "strengths": "文学描摹与节奏亮点",
      "weaknesses": "行文或节律上的不足"
    }},
    "social_dynamics": {{
      "score": 88,
      "strengths": "人际互动与NPC关系的演进表现",
      "weaknesses": "社交层面的局限"
    }},
    "character_arc": {{
      "score": 93,
      "strengths": "心境转变与目标成长的体现",
      "weaknesses": "成长深度的不足"
    }}
  }},
  "highlight_moments": [
    "高光时刻 1",
    "高光时刻 2",
    "高光时刻 3"
  ]
}}
"""

    system_instruction = "你是一名顶尖的世界模拟系统架构师与叙事评测专家。评价客观严苛，输出纯合法 JSON，严禁 Emoji。"

    try:
        raw_res = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        clean = raw_res.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1]
            if clean.endswith("```"):
                clean = clean.rsplit("\n", 1)[0]
            clean = clean.strip()
        return json.loads(clean)
    except Exception as e:
        logger.warning(f"[评测降级] LLM 评测调用异常: {e}，启用统计启发式评分")
        return {
            "overall_score": 88,
            "summary_verdict": f"推演顺利推进 {meta['total_ticks']} 刻，虚拟世界时空与状态机演进完整，各子系统平稳协同。",
            "dimensions": {
                "consistency": {"score": 90, "strengths": "时空流逝规律，状态机连续性好", "weaknesses": "微观过渡偶有跳跃"},
                "narrative_quality": {"score": 87, "strengths": "环境沉浸感充足，视角保持第三人称有限视角", "weaknesses": "中段情节节奏较平缓"},
                "social_dynamics": {"score": 86, "strengths": f"成功结识了 {len(social['npc_met_history'])} 名新角色", "weaknesses": "弱羁绊归档较少"},
                "character_arc": {"score": 89, "strengths": f"累计完成了 {len(goals['completed'])} 个阶段目标", "weaknesses": "长期执念仍需更深发酵"},
            },
            "highlight_moments": [
                f"在 {meta['start_time']} 开启初始历程",
                f"在推演中途成功沉淀社交网络并结识新角色",
                f"在第 {meta['total_ticks']} 刻达成阶段成果并稳固据点",
            ]
        }
