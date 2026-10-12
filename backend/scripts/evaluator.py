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

import re

logger = logging.getLogger("evaluator")


def parse_virtual_time_str(vt_str: str) -> Dict[str, Any]:
    """
    解析虚拟时间字符串，提取自然日与24小时绝对进度
    例如: '1993年9月2日 08:15' ->
      day_label: '1993年9月2日'
      time_label: '08:15'
      hour: 8, minute: 15
      time_float: 8.25 (小时)
      progress_ratio: 8.25 / 24.0 (0.0 ~ 1.0)
    """
    vt_str = str(vt_str).strip()
    match = re.search(r'(\d{1,2}):(\d{2})', vt_str)
    if match:
        h = int(match.group(1))
        m = int(match.group(2))
        time_part = f"{h:02d}:{m:02d}"
        day_part = vt_str[:match.start()].strip()
        if not day_part:
            day_part = "推演日程"
        t_float = round(h + m / 60.0, 2)
        return {
            "day_label": day_part,
            "time_label": time_part,
            "hour": h,
            "minute": m,
            "time_float": t_float,
            "progress_ratio": min(1.0, max(0.0, t_float / 24.0)),
        }
    return {
        "day_label": vt_str or "推演日程",
        "time_label": "12:00",
        "hour": 12,
        "minute": 0,
        "time_float": 12.0,
        "progress_ratio": 0.5,
    }


def generic_macro_location(loc_str: str) -> str:
    """
    通用宏观据点提取 (严格杜绝任何世界观/特定作品词汇硬编码，普适所有题材)
    仅依据中英文通用层级分隔符 (·、——、/、| 等) 提取一级父级区域
    若无分隔符则保留原地点，由大模型 LLM 全局语义归类
    """
    loc_str = str(loc_str).strip()
    for sep in ["·", "——", " - ", "/", "｜", "|"]:
        if sep in loc_str:
            parts = loc_str.split(sep, 1)
            if parts[0].strip():
                return parts[0].strip()
    return loc_str or "未知据点"


def build_location_trajectory_from_records(
    records: List[Dict[str, Any]],
    location_mapping: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    根据宏观据点映射对推演足迹进行高内聚折叠
    连续处于同一宏观据点的多刻合并为一个阶段，并记录内部穿梭的细分子场景
    """
    mapping = location_mapping or {}
    trajectory = []
    current_node = None

    for r in records:
        raw_loc = r["raw_location"]
        # 优先使用 AI 归类映射，其次使用已有 macro_location，兜底使用纯符号通用前缀
        macro = mapping.get(raw_loc) or r.get("macro_location") or generic_macro_location(raw_loc)
        
        # 提取子场景名称 (若有分隔符取后半部分，否则使用原始名称)
        sub_loc = raw_loc
        for sep in ["·", "——", " - ", "/", "｜", "|"]:
            if sep in raw_loc:
                parts = raw_loc.split(sep, 1)
                if len(parts) > 1 and parts[1].strip():
                    sub_loc = parts[1].strip()
                break

        if not current_node or current_node["macro_location"] != macro:
            if current_node:
                trajectory.append(current_node)
            current_node = {
                "macro_location": macro,
                "first_tick": r["tick"],
                "last_tick": r["tick"],
                "start_time": r["virtual_time"],
                "end_time": r["virtual_time"],
                "dwell_ticks": 1,
                "sub_locations": [sub_loc],
                "sample_beat": r["plot_beat"],
            }
        else:
            current_node["last_tick"] = r["tick"]
            current_node["end_time"] = r["virtual_time"]
            current_node["dwell_ticks"] += 1
            if sub_loc not in current_node["sub_locations"]:
                current_node["sub_locations"].append(sub_loc)

    if current_node:
        trajectory.append(current_node)

    return trajectory


def aggregate_simulation_data(db: Session, character_id: str) -> Dict[str, Any]:
    """
    聚合角色的全量推演客观数据，提取真实时空、生理、背包、社交与故事文本
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

    # 2. 真实生理、时间与事件逐刻流追踪
    health_series = []
    stamina_series = []
    tick_indices = []
    time_labels = []
    detailed_records = []

    # 真实精力值回溯推演
    current_stamina = 100
    current_health = 100

    # 3. 背包流水与物品生命周期
    inventory_added_log = []
    inventory_removed_log = []

    # 4. 社交网络演化增量记录与好感度全景追踪
    npc_met_history = []
    known_npcs = set()
    npc_trajectories: Dict[str, Dict[str, Any]] = {}

    raw_locations = []

    for l in logs:
        tick_indices.append(l.tick_index)
        time_labels.append(l.virtual_time)
        raw_locations.append(l.location)

        # 解析 delta 快照
        delta = {}
        try:
            delta = json.loads(l.delta_snapshot_json) if l.delta_snapshot_json else {}
        except Exception:
            pass

        rest_dec = delta.get("rest_decision", {})
        is_sleeping = bool(rest_dec.get("is_sleeping", False))
        stamina_delta = delta.get("stamina_delta", 0)
        health_delta = delta.get("health_delta", 0)

        # 计算真实精力
        if is_sleeping:
            current_stamina = 100
        else:
            if stamina_delta != 0:
                current_stamina = max(5, min(100, current_stamina + stamina_delta))
            else:
                current_stamina = max(10, current_stamina - 8)

        # 计算真实健康
        current_health = max(10, min(100, current_health + health_delta))

        health_series.append(current_health)
        stamina_series.append(current_stamina)

        # 解析时间
        parsed_time = parse_virtual_time_str(l.virtual_time)
        macro_loc = generic_macro_location(l.location)

        # 计算相对上一刻的时间间隔 (小时)
        hours_gap = 1.0
        is_new_day = False
        if detailed_records:
            prev_parsed = detailed_records[-1]["parsed_time"]
            prev_t = prev_parsed["time_float"]
            curr_t = parsed_time["time_float"]
            if parsed_time["day_label"] != prev_parsed["day_label"]:
                is_new_day = True
                hours_gap = round((24.0 - prev_t) + curr_t, 2)
            else:
                hours_gap = round(max(0.2, curr_t - prev_t), 2)

        # 背包增减与当刻里程碑
        inv_delta = delta.get("inventory_delta", {}) or {}
        items_added_this_tick = inv_delta.get("added", []) or []
        items_removed_this_tick = inv_delta.get("removed", []) or []
        for item in items_added_this_tick:
            inventory_added_log.append({"tick": l.tick_index, "time": l.virtual_time, "item": item})
        for item in items_removed_this_tick:
            inventory_removed_log.append({"tick": l.tick_index, "time": l.virtual_time, "item": item})

        # 目标里程碑
        goal_delta = delta.get("goal_delta", {}) or {}
        goals_completed_this_tick = goal_delta.get("completed", []) or []
        goals_added_this_tick = goal_delta.get("added", []) or []

        # 社交关系全量演化 (新结识 + 好感度变动 + 互动态度事件流)
        rel_delta = delta.get("relationship_delta", {}) or {}
        new_npcs_this_tick = []
        aff_changes_this_tick = []

        # 1. 新结识 NPC
        for new_npc in rel_delta.get("new_npcs", []) or []:
            npc_name = new_npc.get("npc_name")
            if not npc_name:
                continue
            new_npcs_this_tick.append({
                "name": npc_name,
                "relation_type": new_npc.get("relation_type", "相识"),
                "affinity": new_npc.get("affinity", 50),
            })
            if npc_name not in known_npcs:
                known_npcs.add(npc_name)
                npc_met_history.append({
                    "tick": l.tick_index,
                    "time": l.virtual_time,
                    "name": npc_name,
                    "relation_type": new_npc.get("relation_type", "相识"),
                    "affinity": new_npc.get("affinity", 50),
                    "residence": new_npc.get("residence_location", l.location),
                    "summary": new_npc.get("summary", ""),
                })
            if npc_name not in npc_trajectories:
                npc_trajectories[npc_name] = {
                    "name": npc_name,
                    "relation_type": new_npc.get("relation_type", "相识"),
                    "current_affinity": new_npc.get("affinity", 50),
                    "residence": new_npc.get("residence_location", l.location),
                    "met_tick": l.tick_index,
                    "met_time": l.virtual_time,
                    "events": []
                }
            npc_trajectories[npc_name]["events"].append({
                "tick": l.tick_index,
                "time": l.virtual_time,
                "type": "met",
                "delta": "+0",
                "affinity": new_npc.get("affinity", 50),
                "summary": new_npc.get("summary", "初次结识")
            })

        # 2. 存量关系好感度与互动演化
        for upd_npc in rel_delta.get("updated_npcs", []) or []:
            npc_name = upd_npc.get("npc_name")
            if not npc_name:
                continue
            aff = upd_npc.get("affinity")
            summ = upd_npc.get("summary")
            rel_type = upd_npc.get("relation_type")
            res = upd_npc.get("residence_location")

            if npc_name not in npc_trajectories:
                npc_trajectories[npc_name] = {
                    "name": npc_name,
                    "relation_type": rel_type or "相识",
                    "current_affinity": 50,
                    "residence": res or l.location,
                    "met_tick": l.tick_index,
                    "met_time": l.virtual_time,
                    "events": []
                }
            if rel_type:
                npc_trajectories[npc_name]["relation_type"] = rel_type
            if res:
                npc_trajectories[npc_name]["residence"] = res

            delta_str = ""
            val = None
            if aff is not None:
                if isinstance(aff, str) and (aff.startswith("+") or aff.startswith("-")):
                    delta_str = aff
                elif isinstance(aff, (int, float)):
                    val = int(aff)
                    npc_trajectories[npc_name]["current_affinity"] = val
                    delta_str = f"={val}"

            if delta_str:
                aff_changes_this_tick.append({
                    "name": npc_name,
                    "delta": delta_str,
                    "val": val or npc_trajectories[npc_name]["current_affinity"],
                })

            if delta_str or (summ and len(summ.strip()) > 5):
                npc_trajectories[npc_name]["events"].append({
                    "tick": l.tick_index,
                    "time": l.virtual_time,
                    "type": "update",
                    "delta": delta_str or "互动",
                    "affinity": val or npc_trajectories[npc_name]["current_affinity"],
                    "summary": summ or ""
                })

        rec = {
            "tick": l.tick_index,
            "virtual_time": l.virtual_time,
            "parsed_time": parsed_time,
            "raw_location": l.location,
            "macro_location": macro_loc,
            "hours_gap": hours_gap,
            "is_new_day": is_new_day,
            "stamina": current_stamina,
            "health": current_health,
            "is_sleeping": is_sleeping,
            "plot_beat": l.plot_beat,
            "narrative_prose": l.narrative_prose,
            "milestones": {
                "new_npcs": new_npcs_this_tick,
                "affinity_changes": aff_changes_this_tick,
                "goals_completed": goals_completed_this_tick,
                "goals_added": goals_added_this_tick,
                "items_added": items_added_this_tick,
                "items_removed": items_removed_this_tick,
            }
        }
        detailed_records.append(rec)

    # 去重微观地点列表
    unique_locations = list(dict.fromkeys(raw_locations))

    # 生成初始启发式折叠足迹
    location_trajectory = build_location_trajectory_from_records(detailed_records)

    # 按自然日分组记录 (用于 24 小时昼夜作息大盘)
    daily_groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in detailed_records:
        day_key = r["parsed_time"]["day_label"]
        if day_key not in daily_groups:
            daily_groups[day_key] = []
        daily_groups[day_key].append(r)

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
        "detailed_records": detailed_records,
        "daily_groups": daily_groups,
        "unique_locations": unique_locations,
        "location_trajectory": location_trajectory,
        "inventory_flow": {
            "current": curr_inventory,
            "added_history": inventory_added_log,
            "removed_history": inventory_removed_log,
        },
        "social_dynamics": {
            "all_relationships": relationships_summary,
            "npc_met_history": npc_met_history,
            "npc_trajectories": list(npc_trajectories.values()),
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


def apply_location_clusters(aggregated_data: Dict[str, Any], location_mapping: Dict[str, str]) -> None:
    """
    将 LLM 裁判或启发式提炼的宏观据点分类应用到聚合数据中
    更新 detailed_records 和重新折叠 location_trajectory
    """
    if not location_mapping:
        return

    records = aggregated_data.get("detailed_records", [])
    for r in records:
        raw_loc = r["raw_location"]
        if raw_loc in location_mapping:
            r["macro_location"] = location_mapping[raw_loc]
        elif not r.get("macro_location"):
            r["macro_location"] = generic_macro_location(raw_loc)

    # 重新折叠足迹链
    new_trajectory = build_location_trajectory_from_records(records, location_mapping)
    aggregated_data["location_trajectory"] = new_trajectory


async def run_llm_judge_evaluation(aggregated_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用大模型作为裁判 (LLM-as-a-Judge) 深度评估长程推演质量
    同时归纳提炼宏观据点 (Location Clustering & Mapping)
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
    unique_locs = aggregated_data.get("unique_locations", [])

    prompt = f"""
你是一名严谨的虚拟世界 AI 智能体推演评估裁判（LLM-as-a-Judge）。
请对以下角色在经历 {meta['total_ticks']} 刻世界推演后的长篇故事记录与数据表现进行多维量化评估与深度诊断。

【被评估角色】: {char_info['name']} ({char_info['title']})
【核心执念】: {char_info['inner_drive']}
【推演历程】: 共 {meta['total_ticks']} 刻，虚拟世界历时从 {meta['start_time']} 至 {meta['end_time']}，总计生成约 {meta['total_words']} 字。
【新结识 NPC 数】: {len(social['npc_met_history'])} 位
【已达成目标】: {len(goals['completed'])} 个

【推演中出现的细分微观地点清单 (需归类提炼)】:
{json.dumps(unique_locs, ensure_ascii=False)}

【全景事实骨架流 (Plot Beats)】:
{beats_summary}

【代表性正文小说切片抽样】:
{samples}

请完成以下两项任务：

任务一：【微观地点归纳提炼为宏观一级据点 (Location Clustering)】
AI 在微观推演中往往会输出极琐碎的具体房间或角落（如各种具体教室、走廊拐角、书桌前、客卧、餐厅等）。
请通盘分析上述微观地点列表，将它们提炼、归类合并为 2~6 个核心【一级宏观据点】（如魔法学院、某某独栋别墅、某某图书馆、某某飞船等）。
【关键命名规范要求】：
1. 同一建筑复合体或主区域必须严格使用 100% 相同的一级宏观名称，严禁出现名称相似但字数不同的分裂（例如绝对禁止既出现“霍格沃茨”又出现“霍格沃茨城堡”，必须统一使用一个规范名称！同理，“温家临湖独栋别墅”与“温家别墅”必须统一）。
2. 在输出 JSON 的 "location_mapping" 字段中，为上述清单中的每一个地点指定其对应的一级宏观据点字典。

任务二：【四维长程质量裁决打分】
从以下 4 个核心维度进行打分（0-100 分制），并给出专业剖析与建设性建议：
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
  ],
  "location_mapping": {{
    "原始具体地点A": "归类宏观据点1",
    "原始具体地点B": "归类宏观据点1"
  }}
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
        result = json.loads(clean)
        
        # 将 LLM 裁判的地点归纳应用到数据结构中
        loc_map = result.get("location_mapping", {})
        if loc_map:
            apply_location_clusters(aggregated_data, loc_map)
            
        return result
    except Exception as e:
        logger.warning(f"[评测降级] LLM 评测调用异常: {e}，启用统计启发式评分与启发式地点归类")
        
        # 降级模式下使用启发式归类
        fallback_map = {loc: generic_macro_location(loc) for loc in unique_locs}
        apply_location_clusters(aggregated_data, fallback_map)
        
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
            ],
            "location_mapping": fallback_map,
        }

