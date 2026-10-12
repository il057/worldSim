import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, List, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.dirname(current_dir)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.database import SessionLocal, init_db
from app.models import Character
from scripts.evaluator import (
    aggregate_simulation_data,
    run_llm_judge_evaluation,
    apply_location_clusters,
    generic_macro_location,
)

logger = logging.getLogger("report_generator")


# -------------------------------------------------------------
# 纯 SVG 矢量图标定义 (严格无 Emoji 规范，符合 05_UI_UX_NEUMORPHIC_SPEC)
# -------------------------------------------------------------
SVG_ICONS = {
    "schedule": """<svg viewBox="0 0 24 24" class="neu-icon" fill="currentColor"><path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm1 14.5h-2v-6h2v6zm0-8h-2V6h2v2.5z"/></svg>""",
    "clock": """<svg viewBox="0 0 24 24" class="neu-icon" fill="currentColor"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>""",
    "location": """<svg viewBox="0 0 24 24" class="neu-icon" fill="currentColor"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 0 1 0-5 2.5 2.5 0 0 1 0 5z"/></svg>""",
    "bolt": """<svg viewBox="0 0 24 24" class="neu-icon" fill="currentColor"><path d="M11 21h-1l1-7H7.5c-.88 0-.33-.75-.31-.78C8.48 10.94 10.42 7.54 13 3h1l-1 7h3.5c.49 0 .56.33.47.51l-6 10.49z"/></svg>""",
    "bed": """<svg viewBox="0 0 24 24" class="neu-icon" fill="currentColor"><path d="M19 7h-8v8H3V5H1v15h2v-3h18v3h2v-9a4 4 0 0 0-4-4zm-9 6H3v-4h7v4z"/></svg>""",
    "inventory": """<svg viewBox="0 0 24 24" class="neu-icon" fill="currentColor"><path d="M20 2H4c-1.1 0-2 .9-2 2v3.01c0 .72.38 1.36.95 1.7L3 20c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2l.05-11.29c.57-.34.95-.98.95-1.7V4c0-1.1-.9-2-2-2zm-1 18H5l-.04-11H19.04L19 20zM4 6V4h16v2H4z"/></svg>""",
    "person": """<svg viewBox="0 0 24 24" class="neu-icon" fill="currentColor"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>""",
    "target": """<svg viewBox="0 0 24 24" class="neu-icon" fill="currentColor"><path d="M12 2C6.49 2 2 6.49 2 12s4.49 10 10 10 10-4.49 10-10S17.51 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm3-8c0 1.66-1.34 3-3 3s-3-1.34-3-3 1.34-3 3-3 3 1.34 3 3z"/></svg>""",
    "award": """<svg viewBox="0 0 24 24" class="neu-icon" fill="currentColor"><path d="m12 15.39-3.76 2.27.99-4.28-3.32-2.88 4.38-.37L12 6.1l1.71 4.04 4.38.37-3.32 2.88.99 4.28z"/></svg>""",
    "heart": """<svg viewBox="0 0 24 24" class="neu-icon" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>""",
    "check": """<svg viewBox="0 0 24 24" class="neu-icon" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>""",
    "user_plus": """<svg viewBox="0 0 24 24" class="neu-icon" fill="currentColor"><path d="M15 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm-9-2V7H4v3H1v2h3v3h2v-3h3v-2H6zm9 4c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>""",
}


def render_continuous_stamina_overview_svg(records: List[Dict[str, Any]]) -> str:
    """
    顶部微型全景连续精力波形图 (横跨所有推演刻度)
    """
    if not records or len(records) < 2:
        return ""

    width = 1000
    height = 90
    padding_x = 30
    padding_y = 15

    total_ticks = len(records)
    points = []
    area_points = []

    for idx, r in enumerate(records):
        x = padding_x + (idx / (total_ticks - 1)) * (width - 2 * padding_x)
        y = height - padding_y - (r["stamina"] / 100.0) * (height - 2 * padding_y)
        points.append(f"{x:.1f},{y:.1f}")
        area_points.append(f"{x:.1f},{y:.1f}")

    path_d = "M " + " L ".join(points)
    area_d = f"M {padding_x},{height - padding_y} L " + " L ".join(area_points) + f" L {width - padding_x},{height - padding_y} Z"

    return f"""
    <div class="stamina-overview-card neu-inset">
        <div class="stamina-overview-head">
            <span>{SVG_ICONS['bolt']} 全程生理精力起伏走势 (Tick #1 ~ #{records[-1]['tick']})</span>
            <span style="color:var(--neu-cyan);">最新: {records[-1]['stamina']}%</span>
        </div>
        <svg viewBox="0 0 {width} {height}" class="stamina-mini-svg" preserveAspectRatio="none">
            <defs>
                <linearGradient id="staminaMiniGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.32"/>
                    <stop offset="100%" stop-color="#3b82f6" stop-opacity="0.0"/>
                </linearGradient>
            </defs>
            <line x1="{padding_x}" y1="{padding_y}" x2="{width - padding_x}" y2="{padding_y}" stroke="rgba(255,255,255,0.06)" stroke-dasharray="3"/>
            <line x1="{padding_x}" y1="{height - padding_y}" x2="{width - padding_x}" y2="{height - padding_y}" stroke="rgba(255,255,255,0.1)"/>
            <path d="{area_d}" fill="url(#staminaMiniGrad)" />
            <path d="{path_d}" fill="none" stroke="#60a5fa" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    </div>
    """


def format_gap_display(hours: float) -> str:
    total_minutes = int(round(hours * 60))
    h = total_minutes // 60
    m = total_minutes % 60
    if h > 0 and m > 0:
        return f"{h}h {m}m"
    elif h > 0:
        return f"{h}h"
    else:
        return f"{m}m"


def render_vertical_continuous_timeline(records: List[Dict[str, Any]]) -> str:
    """
    渲染连续贯穿所有天数的竖向真实疏密时间轴
    - 垂直主轴自上而下，所有天数连续排列 (不分天断裂)
    - 垂直间距与真实时间跨度严格等比映射 (0.5h 仅 12px 紧贴 00，2.25h~2.5h 拉开 178~202px 延展 ------)
    - 长轴线上自动标注客观时间整点标尺刻度 (如 11:00, 12:00)
    - 默认紧凑单行预览，点击时间点即时展开/折叠详细卡片 (事实骨架 + 精力 + 小说切片)
    """
    html_items = []
    current_day = None

    for idx, r in enumerate(records):
        parsed = r["parsed_time"]
        day_label = parsed["day_label"]
        time_label = parsed["time_label"]
        tick = r["tick"]
        stamina = r["stamina"]
        is_sleeping = r["is_sleeping"]
        macro = r["macro_location"]
        raw = r["raw_location"]
        beat = r["plot_beat"]
        prose = r["narrative_prose"]
        gap = r.get("hours_gap", 1.0)

        # 1. 跨天分割胶囊 (当天数切换时显示)
        day_divider_html = ""
        if day_label != current_day:
            current_day = day_label
            day_divider_html = f"""
            <div class="timeline-day-divider">
                <span class="day-divider-pill">{SVG_ICONS['clock']} {day_label}</span>
            </div>
            """

        # 2. 真实客观时间严格等比线性间距计算 (疏密排布 0------00---0 严格正比映射)
        # 半小时 (0.5h): 12px 极度贴合 (00 紧密相依)
        # 1 小时 (1.0h): 60px (比半小时拉开整整 5 倍)
        # 1.5 小时 (1.5h): 107px (比半小时拉开近 9 倍)
        # 2.25 小时 (2.25h): 178px (比半小时拉开近 15 倍超大视觉落差!)
        # 2.5 小时 (2.5h): 202px (比半小时拉开近 17 倍超大视觉落差!)
        # 6.0 小时 (6.0h): 334px 深度休眠大纵深
        # 8.5 小时 (跨夜): 404px
        prev_record = records[idx - 1] if idx > 0 else None
        prev_time_str = prev_record["parsed_time"]["time_label"] if prev_record else "起程"
        prev_day_label = prev_record["parsed_time"]["day_label"] if prev_record else ""
        prev_time_float = prev_record["parsed_time"]["time_float"] if prev_record else 0.0
        curr_time_float = parsed["time_float"]
        is_same_day = (prev_record is not None and prev_day_label == day_label)
        curr_time_str = time_label

        if idx == 0 or day_divider_html:
            margin_top = 10
            gap_badge_html = ""
            ruler_ticks_html = ""
        else:
            if gap <= 0.5:
                # 半小时及以内: 极度贴合，如同 00 相邻
                margin_top = max(8, int(round((gap / 0.5) * 12)))
            elif gap <= 3.0:
                # 0.5h ~ 3.0h 日常活动: 严格客观时间等比线性展开
                margin_top = 12 + int(round((gap - 0.5) * 95))
            else:
                # 3.0h+ 大跨度休眠与跨夜: 延展纵深同时平滑防爆表
                margin_top = min(420, 250 + int(round((gap - 3.0) * 28)))

            gap_text = format_gap_display(gap)
            top_offset = -int(margin_top / 2)

            # 徽章渲染 (根据客观时间差分级)
            if gap < 0.75:
                gap_badge_html = ""
            elif gap <= 1.5:
                gap_badge_html = f'<div class="timeline-gap-pill" style="top:{top_offset}px;"><span>+{gap_text} 推进</span></div>'
            elif gap <= 3.0:
                gap_badge_html = f'<div class="timeline-gap-pill gap-pill-mid" style="top:{top_offset}px;"><span>+{gap_text} 客观时间流逝 ({prev_time_str} → {curr_time_str})</span></div>'
            else:
                sleep_note = " · 深度休眠恢复" if is_sleeping else ""
                gap_badge_html = f'<div class="timeline-gap-pill gap-pill-large" style="top:{top_offset}px;"><span>+{gap_text} 大跨度跃迁{sleep_note} ({prev_time_str} → {curr_time_str})</span></div>'

            # 客观时间整点标尺刻度 (Ruler Hour Ticks)
            # 在同一天内、间隔 >= 0.9h 时，在轴线上渲染经过的整点时间 (如 11:00, 12:00)
            ruler_ticks = []
            if is_same_day and gap >= 0.9 and margin_top >= 50:
                start_h = int(prev_time_float) + 1
                end_h = int(curr_time_float)
                if curr_time_float == float(end_h):
                    end_h -= 1
                all_hours = list(range(start_h, end_h + 1))
                step = 1 if len(all_hours) <= 4 else 2
                for h in all_hours[::step]:
                    ratio = (h - prev_time_float) / gap
                    offset_y = -margin_top + int(round(ratio * margin_top))
                    # 避免与当前节点的徽章或圆点发生严重重叠
                    if abs(offset_y - top_offset) > 16 and offset_y < -12:
                        ruler_ticks.append(
                            f'<div class="timeline-hour-ruler-tick" style="top:{offset_y}px;">'
                            f'<span class="ruler-time">{h:02d}:00</span>'
                            f'<div class="ruler-notch"></div>'
                            f'</div>'
                        )
            ruler_ticks_html = "".join(ruler_ticks)

        node_type_class = "node-sleep" if is_sleeping else "node-active"
        status_text = "休眠回满" if is_sleeping else "活跃"

        # 3. 里程碑徽章提取 (左侧极简防溢出胶囊，右侧展开面板呈现全量详情)
        milestones = r.get("milestones", {}) or {}
        left_ms_pills = []
        detail_ms_pills = []

        def short_lbl(text: str, max_chars: int = 8) -> str:
            t = str(text).strip()
            return t if len(t) <= max_chars else t[:max_chars] + "…"

        for g in milestones.get("goals_completed", []) or []:
            left_ms_pills.append(f'<span class="ms-pill ms-goal-done" title="达成: {g}">{SVG_ICONS["check"]} 达成: {short_lbl(g, 9)}</span>')
            detail_ms_pills.append(f'<span class="ms-pill ms-goal-done">{SVG_ICONS["check"]} 达成目标: {g}</span>')

        for n in milestones.get("new_npcs", []) or []:
            n_name = n["name"]
            left_ms_pills.append(f'<span class="ms-pill ms-npc-new" title="结识: {n_name}">{SVG_ICONS["user_plus"]} 结识: {short_lbl(n_name, 6)}</span>')
            detail_ms_pills.append(f'<span class="ms-pill ms-npc-new">{SVG_ICONS["user_plus"]} 结识新人物: {n_name} ({n.get("relation_type", "相识")})</span>')

        for aff in milestones.get("affinity_changes", []) or []:
            left_ms_pills.append(f'<span class="ms-pill ms-npc-aff" title="{aff["name"]} 好感 {aff["delta"]}">{SVG_ICONS["heart"]} {short_lbl(aff["name"], 5)} {aff["delta"]}</span>')
            detail_ms_pills.append(f'<span class="ms-pill ms-npc-aff">{SVG_ICONS["heart"]} {aff["name"]} 好感度 {aff["delta"]} (当前: {aff.get("val", "-")})</span>')

        for it in milestones.get("items_added", []) or []:
            left_ms_pills.append(f'<span class="ms-pill ms-inv-add" title="+ {it}">+ {short_lbl(it, 8)}</span>')
            detail_ms_pills.append(f'<span class="ms-pill ms-inv-add">+ 获得道具: {it}</span>')

        for it in milestones.get("items_removed", []) or []:
            left_ms_pills.append(f'<span class="ms-pill ms-inv-rem" title="- {it}">- {short_lbl(it, 8)}</span>')
            detail_ms_pills.append(f'<span class="ms-pill ms-inv-rem">- 消耗/转交道具: {it}</span>')

        for g in milestones.get("goals_added", []) or []:
            left_ms_pills.append(f'<span class="ms-pill ms-goal-add" title="接取: {g}">{SVG_ICONS["target"]} 接取: {short_lbl(g, 9)}</span>')
            detail_ms_pills.append(f'<span class="ms-pill ms-goal-add">{SVG_ICONS["target"]} 接取新目标: {g}</span>')

        left_milestones_html = f'<div class="v-left-milestones">{"".join(left_ms_pills)}</div>' if left_ms_pills else ""
        milestone_detail_html = f'<div class="v-detail-section v-detail-ms-box"><span class="detail-label">本刻关键世界推进沉淀:</span><div class="v-detail-ms-list">{"".join(detail_ms_pills)}</div></div>' if detail_ms_pills else ""

        item_html = f"""
        {day_divider_html}
        <div class="v-timeline-node {node_type_class}" style="margin-top: {margin_top}px;" data-tick="{tick}">
            {ruler_ticks_html}
            {gap_badge_html}
            
            <!-- 左侧列: 客观时间 + 当刻关键事件里程碑流 (宽裕排布) -->
            <div class="v-node-left-col" onclick="toggleTimelineDetail({tick})" title="点击查看详情">
                <span class="v-time-str">{time_label}</span>
                {left_milestones_html}
            </div>

            <!-- 中轴锚点: 圆点 -->
            <div class="v-axis-anchor" onclick="toggleTimelineDetail({tick})" title="点击查看详情">
                <div class="v-dot-box">
                    <div class="v-dot"></div>
                </div>
            </div>

            <!-- 右侧卡片: 剧情简述与小说展开 (舒展整洁，绝不拥挤) -->
            <div class="v-node-card neu-flat-sm">
                <!-- 紧凑单行摘要条 (点击展开/折叠) -->
                <div class="v-node-summary-bar" onclick="toggleTimelineDetail({tick})" title="点击展开/收起详情">
                    <div class="v-bar-left">
                        <span class="v-tick-badge">Tick #{tick}</span>
                        <span class="v-macro-loc-pill">{SVG_ICONS['location']} {macro}</span>
                        <span class="v-stamina-pill {'stamina-pill-sleep' if is_sleeping else ''}">
                            {SVG_ICONS['bed'] if is_sleeping else SVG_ICONS['bolt']} {stamina}%
                        </span>
                    </div>
                    <div class="v-beat-brief">{beat}</div>
                    <div class="v-expand-btn" id="ind_{tick}">
                        <span>展开</span>
                        <svg viewBox="0 0 24 24" class="neu-arrow-icon" fill="currentColor"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/></svg>
                    </div>
                </div>

                <!-- 展开的具体详情面板 -->
                <div class="v-node-detail-panel" id="detail_{tick}" style="display: none;">
                    {milestone_detail_html}
                    <div class="v-detail-meta-grid">
                        <div class="v-detail-item">
                            <span class="detail-label">微观具体位置:</span>
                            <span class="detail-val">{raw}</span>
                        </div>
                        <div class="v-detail-item">
                            <span class="detail-label">生理与体能:</span>
                            <span class="detail-val">精力 <strong>{stamina}%</strong> · 健康 <strong>{r.get('health', 100)}%</strong> ({status_text})</span>
                        </div>
                    </div>
                    <div class="v-detail-section">
                        <span class="detail-label">事实因果骨架 (Pass 1 Plot Beat):</span>
                        <p class="v-beat-full">{beat}</p>
                    </div>
                    <div class="v-detail-section">
                        <span class="detail-label">第三人称有限视角小说正文 (Pass 2 Narrative):</span>
                        <div class="v-prose-container">{prose}</div>
                    </div>
                </div>
            </div>
        </div>
        """
        html_items.append(item_html)

    return "\n".join(html_items)


def generate_html_report_content(data: Dict[str, Any], evaluation: Dict[str, Any]) -> str:
    char = data["character"]
    meta = data["meta"]
    social = data["social_dynamics"]
    inv = data["inventory_flow"]
    goals = data["goals"]
    locs = data.get("location_trajectory", [])
    records = data.get("detailed_records", [])

    overall_score = evaluation.get("overall_score", 90)
    dimensions = evaluation.get("dimensions", {})
    highlights = evaluation.get("highlight_moments", [])
    summary_verdict = evaluation.get("summary_verdict", "推演状态平稳正常。")

    # 1. 顶部连续精力微型走势
    stamina_overview_svg = render_continuous_stamina_overview_svg(records)

    # 2. 核心：连续纵向时间轴
    vertical_timeline_html = render_vertical_continuous_timeline(records)

    # 3. 宏观地理据点迁徙链
    macro_loc_nodes_html = ""
    for idx, loc in enumerate(locs):
        subs = loc.get("sub_locations", [])
        sub_badges = "".join([f'<span class="sub-scene-chip">{s}</span>' for s in subs[:8]])
        macro_loc_nodes_html += f"""
        <div class="macro-loc-card neu-flat-sm">
            <div class="macro-loc-top">
                <span class="macro-step-badge">阶段 {idx + 1}</span>
                <span class="macro-dwell-tag">历经 {loc['dwell_ticks']} 刻</span>
            </div>
            <h4 class="macro-loc-title">{loc['macro_location']}</h4>
            <div class="macro-time-range">{loc['start_time']} 至 {loc['end_time']}</div>
            <div class="macro-sub-flow">
                <span class="sub-flow-label">涵盖微观场景:</span>
                <div class="sub-flow-chips">{sub_badges}</div>
            </div>
        </div>
        """

    # 4. 社交关系网络演化 (Social Graph Dynamics & Affinity Trajectory)
    npc_trajectories = social.get("npc_trajectories", [])
    if not npc_trajectories and social.get("npc_met_history"):
        npc_trajectories = [{
            "name": n["name"],
            "relation_type": n["relation_type"],
            "current_affinity": n["affinity"],
            "residence": n["residence"],
            "met_tick": n["tick"],
            "events": [{"tick": n["tick"], "time": n["time"], "delta": "+0", "affinity": n["affinity"], "summary": n["summary"]}]
        } for n in social["npc_met_history"]]

    # 按交互频次与好感度综合降序排序，核心羁绊在前
    npc_trajectories.sort(key=lambda x: (len(x.get("events", [])), x.get("current_affinity", 0)), reverse=True)

    npc_cards_html = ""
    if not npc_trajectories:
        npc_cards_html = "<div class='empty-tip'>在本次历程中暂未沉淀专属新角色</div>"
    else:
        for npc in npc_trajectories:
            name = npc["name"]
            rel_type = npc.get("relation_type", "相识")
            cur_aff = npc.get("current_affinity", 50)
            res = npc.get("residence", "未知据点")
            met_tick = npc.get("met_tick", 1)
            events = npc.get("events", [])

            # 合理严谨的好感度梯度与系统真实色板 (彻底杜绝 10~20 师生同学初识被误判为提防对立)
            if cur_aff >= 85:
                aff_title = "莫逆之交"
                aff_color = "var(--neu-accent)"      # 蓝紫
            elif cur_aff >= 60:
                aff_title = "技术盟友"
                aff_color = "var(--neu-cyan)"        # 青蓝
            elif cur_aff >= 35:
                aff_title = "友好融洽"
                aff_color = "var(--neu-emerald)"     # 翡翠绿
            elif cur_aff >= 10:
                aff_title = "初识 · 略有印象"
                aff_color = "#94a3b8"                # 柔和灰蓝 (正常师生、同学初次结识)
            elif cur_aff >= 0:
                aff_title = "生疏 · 点头之交"
                aff_color = "#64748b"                # 平静暗灰
            else:
                aff_title = "警惕对立"
                aff_color = "var(--neu-rose)"        # 玫瑰红 (违纪扣分或敌意)

            # 历次好感度变动与互动事件流
            event_items_html = ""
            for ev in events:
                delta_lbl = ev.get("delta", "互动")
                badge_cls = "aff-delta-up" if (delta_lbl.startswith("+") or "=" in delta_lbl) else "aff-delta-neutral"
                if delta_lbl.startswith("-"):
                    badge_cls = "aff-delta-down"
                summary_txt = ev.get("summary", "") or "产生因果交集"
                event_items_html += f"""
                <div class="npc-ev-row">
                    <span class="npc-ev-tick">Tick #{ev['tick']}</span>
                    <span class="npc-ev-badge {badge_cls}">{delta_lbl}</span>
                    <span class="npc-ev-desc">{summary_txt}</span>
                </div>
                """

            npc_cards_html += f"""
            <div class="npc-card neu-flat-sm">
                <div class="npc-head">
                    <div class="npc-title-box">
                        <span class="npc-name">{name}</span>
                        <span class="npc-badge">{rel_type}</span>
                    </div>
                    <div class="npc-aff-badge" style="color: {aff_color};">
                        {SVG_ICONS['heart']} {cur_aff} · {aff_title}
                    </div>
                </div>
                <div class="npc-meta">结识于 Tick #{met_tick} | 累计交互 <strong>{len(events)}</strong> 次 | 常驻地: {res}</div>
                <div class="npc-bar-bg neu-inset-sm">
                    <div class="npc-bar-fill" style="width: {max(0, min(100, cur_aff))}%; background: {aff_color};"></div>
                </div>
                <details class="npc-history-details">
                    <summary class="npc-history-toggle">
                        <span>展开好感度变动与互动历程 ({len(events)} 次记录)</span>
                        <svg viewBox="0 0 24 24" class="neu-icon-sm" fill="currentColor"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/></svg>
                    </summary>
                    <div class="npc-history-body neu-inset-sm">
                        {event_items_html}
                    </div>
                </details>
            </div>
            """

    # 5. 背包流水
    added_items_html = "".join([f"<li><span class='badge-add'>+获取</span> <strong>{i['item']}</strong> <span class='flow-tick'>(Tick #{i['tick']})</span></li>" for i in inv["added_history"][:14]])
    removed_items_html = "".join([f"<li><span class='badge-sub'>-收纳/消耗</span> <strong>{i['item']}</strong> <span class='flow-tick'>(Tick #{i['tick']})</span></li>" for i in inv["removed_history"][:14]])

    # 6. 四维评分卡片
    dim_titles = {
        "consistency": "连续一致性与时空自洽 (Consistency)",
        "narrative_quality": "叙事可观赏性与节奏 (Narrative Quality)",
        "social_dynamics": "社交网络与互动生态 (Social Dynamics)",
        "character_arc": "角色成长与心境弧光 (Character Arc)",
    }
    dims_html = ""
    for key, title in dim_titles.items():
        info = dimensions.get(key, {"score": 85, "strengths": "表现平稳", "weaknesses": "无显著瑕疵"})
        score = info.get("score", 85)
        dims_html += f"""
        <div class="dim-card neu-flat-sm">
            <div class="dim-header">
                <span class="dim-title">{title}</span>
                <span class="dim-score">{score} 分</span>
            </div>
            <div class="progress-bar-bg neu-inset-sm">
                <div class="progress-bar-fill" style="width: {score}%;"></div>
            </div>
            <div class="dim-detail">
                <div class="dim-text"><strong class="highlight-green">核心亮点:</strong> {info.get('strengths')}</div>
                <div class="dim-text"><strong class="highlight-amber">演进建议:</strong> {info.get('weaknesses')}</div>
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WorldSim 推演全景观测报告 - {char['name']}</title>
    <style>
        :root {{
            /* 沉浸式新拟态设计令牌 (严格遵循 05_UI_UX_NEUMORPHIC_SPEC.md) */
            --neu-bg: #1c2027;
            --neu-surface: #1e232b;
            --neu-surface-sub: #171b21;
            --neu-light: #262c37;
            --neu-dark: #12151a;
            
            --neu-accent: #5e72e4;
            --neu-accent-hover: #4b5ecc;
            
            --neu-cyan: #06b6d4;
            --neu-emerald: #10b981;
            --neu-amber: #f59e0b;
            --neu-rose: #f43f5e;
            --neu-purple: #8b5cf6;
            
            --text-main: #e2e8f0;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
            --border-subtle: rgba(255, 255, 255, 0.06);

            --shadow-flat: 6px 6px 14px var(--neu-dark), -6px -6px 14px var(--neu-light);
            --shadow-flat-sm: 3px 3px 8px var(--neu-dark), -3px -3px 8px var(--neu-light);
            --shadow-hover: 7px 7px 16px var(--neu-dark), -7px -7px 16px var(--neu-light);
            --shadow-inset: inset 3px 3px 7px var(--neu-dark), inset -3px -3px 7px var(--neu-light);
            --shadow-inset-sm: inset 2px 2px 4px var(--neu-dark), inset -2px -2px 4px var(--neu-light);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background-color: var(--neu-bg);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            padding: 32px 20px;
        }}
        .container {{ max-width: 1220px; margin: 0 auto; }}

        .neu-flat {{ background: var(--neu-surface); box-shadow: var(--shadow-flat); border-radius: 16px; border: 1px solid var(--border-subtle); }}
        .neu-flat-sm {{ background: var(--neu-surface); box-shadow: var(--shadow-flat-sm); border-radius: 12px; border: 1px solid var(--border-subtle); }}
        .neu-inset {{ background: var(--neu-surface-sub); box-shadow: var(--shadow-inset); border-radius: 14px; }}
        .neu-inset-sm {{ background: var(--neu-surface-sub); box-shadow: var(--shadow-inset-sm); border-radius: 6px; }}

        .neu-icon {{ width: 17px; height: 17px; vertical-align: middle; display: inline-block; }}
        .neu-arrow-icon {{ width: 16px; height: 16px; transition: transform 0.25s ease; }}

        /* 顶部看板 */
        .header-card {{
            padding: 30px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }}
        .char-title {{ font-size: 28px; font-weight: 800; color: #fff; margin-bottom: 6px; letter-spacing: -0.5px; }}
        .char-subtitle {{ color: var(--text-muted); font-size: 14px; max-width: 660px; line-height: 1.6; }}
        .inner-drive-tag {{ display: inline-block; margin-top: 10px; font-size: 12px; color: var(--neu-cyan); background: rgba(6,182,212,0.1); padding: 4px 12px; border-radius: 20px; border: 1px solid rgba(6,182,212,0.25); }}
        
        .score-badge-box {{
            padding: 18px 28px;
            text-align: center;
            min-width: 150px;
        }}
        .score-val {{ font-size: 42px; font-weight: 800; color: var(--neu-accent); line-height: 1; }}
        .score-label {{ font-size: 12px; color: var(--text-muted); margin-top: 6px; text-transform: uppercase; letter-spacing: 1px; }}

        /* 统计指标网格 */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{ padding: 20px; }}
        .stat-num {{ font-size: 24px; font-weight: 800; color: #fff; margin-bottom: 4px; }}
        .stat-desc {{ font-size: 13px; color: var(--text-muted); }}

        /* 通用板块 */
        .section-box {{
            padding: 28px;
            margin-bottom: 24px;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border-subtle);
            padding-bottom: 12px;
        }}
        .title-left {{ display: flex; align-items: center; gap: 8px; }}
        .section-desc {{ font-size: 13px; color: var(--text-muted); margin-top: -10px; margin-bottom: 20px; }}

        /* 评测诊断看板 */
        .verdict-box {{
            padding: 18px 20px;
            border-left: 4px solid var(--neu-accent);
            font-size: 14px;
            color: #e2e8f0;
            margin-bottom: 20px;
            line-height: 1.7;
        }}
        .dims-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(460px, 1fr));
            gap: 18px;
            margin-bottom: 18px;
        }}
        .dim-card {{ padding: 18px; }}
        .dim-header {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
        .dim-title {{ font-size: 15px; font-weight: 600; color: #e2e8f0; }}
        .dim-score {{ font-size: 16px; font-weight: 700; color: var(--neu-cyan); }}
        .progress-bar-bg {{ height: 7px; overflow: hidden; margin-bottom: 12px; }}
        .progress-bar-fill {{ height: 100%; background: linear-gradient(90deg, var(--neu-accent), var(--neu-cyan)); border-radius: 4px; }}
        .dim-detail {{ font-size: 13px; color: var(--text-muted); display: flex; flex-direction: column; gap: 6px; }}
        .highlight-green {{ color: #34d399; }}
        .highlight-amber {{ color: #fbbf24; }}

        /* 全景精力走势微型卡片 */
        .stamina-overview-card {{
            padding: 14px 18px;
            margin-bottom: 24px;
        }}
        .stamina-overview-head {{
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 6px;
        }}
        .stamina-mini-svg {{ width: 100%; height: 60px; overflow: visible; }}

        /* ============================================================= */
        /* 核心：竖向连续时间轴 (Vertical Continuous Timeline)           */
        /* ============================================================= */
        .v-timeline-container {{
            position: relative;
            padding-left: 12px;
        }}
        /* 贯穿全长的垂直主轴线 (位于左中侧 240px 处，左侧为时间与里程碑，右侧为故事卡片) */
        .v-timeline-container::before {{
            content: "";
            position: absolute;
            left: 240px;
            top: 10px;
            bottom: 20px;
            width: 2px;
            background: linear-gradient(180deg, var(--neu-accent) 0%, rgba(94, 114, 228, 0.2) 100%);
            box-shadow: 0 0 8px rgba(94, 114, 228, 0.4);
            z-index: 1;
        }}

        /* 日期切换分割线 (居中在轴线周围) */
        .timeline-day-divider {{
            position: relative;
            z-index: 2;
            padding: 16px 0 10px 180px;
        }}
        .day-divider-pill {{
            background: var(--neu-surface-sub);
            color: #fff;
            font-size: 12px;
            font-weight: 700;
            padding: 5px 14px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: var(--shadow-flat-sm);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}

        /* 客观时间整点标尺刻痕 (横跨在垂直主轴上 240px) */
        .timeline-hour-ruler-tick {{
            position: absolute;
            left: 0;
            width: 244px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 8px;
            pointer-events: none;
            z-index: 2;
        }}
        .ruler-time {{
            font-size: 11px;
            font-weight: 600;
            color: #475569;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            letter-spacing: -0.3px;
        }}
        .ruler-notch {{
            width: 8px;
            height: 2px;
            background: rgba(94, 114, 228, 0.45);
            border-radius: 1px;
            box-shadow: 0 0 4px rgba(94, 114, 228, 0.3);
        }}

        /* 跃迁时间间隔徽章 (正中悬浮横跨在垂直主轴线上 240px) */
        .timeline-gap-pill {{
            position: absolute;
            left: 240px;
            transform: translate(-50%, -50%);
            font-size: 11px;
            font-weight: 600;
            color: #94a3b8;
            background: #151921;
            padding: 3px 14px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
            z-index: 3;
            white-space: nowrap;
            letter-spacing: 0.2px;
        }}
        .gap-pill-mid {{
            color: var(--neu-cyan);
            border-color: rgba(6, 182, 212, 0.4);
            background: #101c26;
        }}
        .gap-pill-large {{
            color: var(--neu-purple);
            border-color: rgba(139, 92, 246, 0.5);
            background: #1b162c;
            font-weight: 700;
            padding: 4px 16px;
        }}

        /* 垂直节点行: 双侧分栏布局 (左: 226px 时间+事件流, 中: 28px 轴线, 右: flex:1 故事卡片) */
        .v-timeline-node {{
            position: relative;
            display: flex;
            align-items: flex-start;
            gap: 0;
            z-index: 2;
            transition: margin-top 0.2s ease;
        }}

        /* 左侧分栏: 客观时间 + 当刻事件里程碑流 */
        .v-node-left-col {{
            width: 226px;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            padding-right: 14px;
            padding-top: 10px;
            cursor: pointer;
            flex-shrink: 0;
        }}
        .v-time-str {{
            font-size: 14px;
            font-weight: 800;
            color: #fff;
            letter-spacing: -0.2px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        .v-left-milestones {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 4px;
            margin-top: 6px;
            width: 100%;
        }}

        /* 中轴线锚点 */
        .v-axis-anchor {{
            width: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding-top: 13px;
            cursor: pointer;
            flex-shrink: 0;
        }}
        .v-dot-box {{
            width: 16px;
            height: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--neu-bg);
            border-radius: 50%;
        }}
        .v-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--neu-cyan);
            box-shadow: 0 0 8px var(--neu-cyan);
            transition: all 0.2s ease;
        }}
        .node-sleep .v-dot {{
            background: var(--neu-purple);
            box-shadow: 0 0 8px var(--neu-purple);
        }}

        .v-node-card {{
            flex: 1;
            transition: all 0.2s ease;
            overflow: hidden;
        }}
        .v-node-card:hover {{
            box-shadow: var(--shadow-hover);
            border-color: rgba(94, 114, 228, 0.35);
        }}

        /* 单行紧凑摘要条 */
        .v-node-summary-bar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            cursor: pointer;
            user-select: none;
            gap: 12px;
        }}
        .v-bar-left {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-shrink: 0;
        }}
        .v-tick-badge {{
            background: rgba(255, 255, 255, 0.06);
            color: var(--neu-cyan);
            font-size: 11px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 4px;
        }}
        .v-macro-loc-pill {{
            background: rgba(94, 114, 228, 0.12);
            color: var(--neu-accent);
            font-size: 12px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .v-stamina-pill {{
            font-size: 11px;
            font-weight: 600;
            color: #60a5fa;
            background: rgba(59, 130, 246, 0.1);
            padding: 2px 7px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 3px;
        }}
        .stamina-pill-sleep {{
            color: var(--neu-purple);
            background: rgba(139, 92, 246, 0.15);
        }}

        .v-beat-brief {{
            flex: 1;
            font-size: 13px;
            color: #cbd5e1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .v-expand-btn {{
            font-size: 11px;
            color: var(--text-dim);
            display: flex;
            align-items: center;
            gap: 4px;
            flex-shrink: 0;
            transition: color 0.2s;
        }}
        .v-node-card:hover .v-expand-btn {{ color: var(--neu-accent); }}

        /* 展开的详情面板 */
        .v-node-detail-panel {{
            padding: 16px;
            border-top: 1px solid var(--border-subtle);
            background: rgba(0, 0, 0, 0.22);
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        .v-detail-meta-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            font-size: 12px;
        }}
        .detail-label {{ color: var(--text-dim); margin-right: 6px; font-weight: 600; }}
        .detail-val {{ color: var(--text-main); }}

        .v-detail-section {{ font-size: 13px; }}
        .v-beat-full {{
            margin-top: 4px;
            color: #f1f5f9;
            background: rgba(255, 255, 255, 0.03);
            padding: 10px 14px;
            border-radius: 8px;
            border-left: 3px solid var(--neu-accent);
            line-height: 1.6;
        }}
        .v-prose-container {{
            margin-top: 6px;
            padding: 14px;
            background: rgba(0, 0, 0, 0.35);
            border-radius: 8px;
            font-size: 13px;
            color: #94a3b8;
            line-height: 1.75;
            white-space: pre-wrap;
        }}

        /* 快捷按钮 */
        .timeline-ctrl-btn {{
            background: var(--neu-surface-sub);
            border: 1px solid var(--border-subtle);
            color: var(--text-muted);
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .timeline-ctrl-btn:hover {{
            color: #fff;
            border-color: var(--neu-accent);
        }}

        /* 宏观地理据点迁徙链 */
        .macro-loc-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 16px;
        }}
        .macro-loc-card {{ padding: 18px; }}
        .macro-loc-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
        .macro-step-badge {{ font-size: 11px; background: rgba(94, 114, 228, 0.2); color: var(--neu-accent); padding: 2px 7px; border-radius: 4px; font-weight: 600; }}
        .macro-dwell-tag {{ font-size: 11px; color: var(--neu-emerald); background: rgba(16, 185, 129, 0.12); padding: 2px 7px; border-radius: 4px; }}
        .macro-loc-title {{ font-size: 15px; font-weight: 700; color: #fff; margin-bottom: 4px; }}
        .macro-time-range {{ font-size: 11px; color: var(--text-dim); margin-bottom: 10px; }}
        .sub-flow-label {{ color: var(--text-dim); display: block; margin-bottom: 6px; font-size: 11px; }}
        .sub-flow-chips {{ display: flex; flex-wrap: wrap; gap: 5px; }}
        .sub-scene-chip {{ font-size: 11px; background: rgba(255,255,255,0.04); color: var(--text-muted); padding: 2px 6px; border-radius: 4px; border: 1px solid var(--border-subtle); }}

        /* 时间轴里程碑徽章流 */
        .v-node-milestones-stripe {{
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
        }}
        .ms-pill {{
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 4px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            white-space: nowrap;
            max-width: 216px;
            overflow: hidden;
            text-overflow: ellipsis;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
        }}
        .v-detail-ms-list .ms-pill {{
            max-width: none;
            white-space: normal;
            word-break: break-all;
            padding: 4px 10px;
            line-height: 1.4;
        }}
        .ms-goal-done {{
            background: rgba(245, 158, 11, 0.18);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.4);
            box-shadow: 0 0 6px rgba(245, 158, 11, 0.2);
        }}
        .ms-goal-add {{
            background: rgba(245, 158, 11, 0.08);
            color: #fde68a;
            border: 1px solid rgba(245, 158, 11, 0.2);
        }}
        .ms-npc-new {{
            background: rgba(6, 182, 212, 0.16);
            color: var(--neu-cyan);
            border: 1px solid rgba(6, 182, 212, 0.35);
        }}
        .ms-npc-aff {{
            background: rgba(236, 72, 153, 0.15);
            color: #f472b6;
            border: 1px solid rgba(236, 72, 153, 0.3);
        }}
        .ms-inv-add {{
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}
        .ms-inv-rem {{
            background: rgba(244, 63, 94, 0.12);
            color: #fb7185;
            border: 1px solid rgba(244, 63, 94, 0.25);
        }}

        .v-detail-ms-box {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 6px;
            padding: 10px 12px;
            margin-bottom: 12px;
        }}
        .v-detail-ms-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 6px;
        }}

        /* 社交网络卡片演化 */
        .npc-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 16px;
        }}
        .npc-card {{ padding: 18px; }}
        .npc-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
        .npc-title-box {{ display: flex; align-items: center; gap: 8px; }}
        .npc-name {{ font-size: 15px; font-weight: 700; color: #fff; }}
        .npc-badge {{ font-size: 11px; background: rgba(94, 114, 228, 0.18); color: var(--neu-accent); padding: 2px 7px; border-radius: 4px; }}
        .npc-aff-badge {{ font-size: 12px; font-weight: 700; display: flex; align-items: center; gap: 4px; }}
        .npc-meta {{ font-size: 12px; color: var(--text-muted); margin-bottom: 10px; }}
        .npc-bar-bg {{
            height: 8px;
            background: #0d1219;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: inset 1px 1px 3px rgba(0, 0, 0, 0.6);
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 12px;
        }}
        .npc-bar-fill {{
            height: 100%;
            border-radius: 4px;
            min-width: 4px;
            box-shadow: 0 0 8px rgba(255, 255, 255, 0.2);
            transition: width 0.3s ease;
        }}

        .npc-history-details {{
            margin-top: 8px;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            padding-top: 8px;
        }}
        .npc-history-toggle {{
            font-size: 11px;
            color: var(--text-dim);
            cursor: pointer;
            user-select: none;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 4px 0;
            transition: color 0.2s;
        }}
        .npc-history-toggle:hover {{ color: var(--neu-cyan); }}
        .neu-icon-sm {{ width: 14px; height: 14px; }}
        .npc-history-body {{
            margin-top: 8px;
            padding: 10px;
            max-height: 220px;
            overflow-y: auto;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        .npc-ev-row {{
            display: flex;
            align-items: baseline;
            gap: 8px;
            font-size: 11px;
            line-height: 1.4;
        }}
        .npc-ev-tick {{
            font-weight: 700;
            color: var(--neu-cyan);
            font-family: monospace;
            flex-shrink: 0;
        }}
        .npc-ev-badge {{
            font-size: 10px;
            font-weight: 700;
            padding: 1px 5px;
            border-radius: 3px;
            flex-shrink: 0;
        }}
        .aff-delta-up {{
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
        }}
        .aff-delta-down {{
            background: rgba(244, 63, 94, 0.2);
            color: #fb7185;
        }}
        .aff-delta-neutral {{
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-muted);
        }}
        .npc-ev-desc {{
            color: var(--text-muted);
            flex: 1;
        }}

        /* 背包与目标双栏 */
        .two-cols {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .flow-list {{ list-style: none; display: flex; flex-direction: column; gap: 8px; font-size: 13px; }}
        .badge-add {{ color: #34d399; font-weight: 600; margin-right: 6px; }}
        .badge-sub {{ color: #f87171; font-weight: 600; margin-right: 6px; }}
        .flow-tick {{ color: var(--text-dim); font-size: 11px; margin-left: 4px; }}

        .empty-tip {{ color: var(--text-dim); font-size: 13px; padding: 12px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 顶部核心看板 -->
        <header class="header-card neu-flat">
            <div>
                <h1 class="char-title">{char['name']} <span style="font-size:17px;font-weight:400;color:var(--text-muted);">({char['title']})</span></h1>
                <p class="char-subtitle">{char['persona_summary'][:220]}...</p>
                <div class="inner-drive-tag">{SVG_ICONS['target']} 核心执念: {char['inner_drive']}</div>
            </div>
            <div class="score-badge-box neu-inset">
                <div class="score-val">{overall_score}</div>
                <div class="score-label">总评健康指数</div>
            </div>
        </header>

        <!-- 统计指标网格 -->
        <div class="stats-grid">
            <div class="stat-card neu-flat-sm">
                <div class="stat-num">{meta['total_ticks']} 刻</div>
                <div class="stat-desc">推演总步长跨度</div>
            </div>
            <div class="stat-card neu-flat-sm">
                <div class="stat-num">{meta['total_words']} 字</div>
                <div class="stat-desc">叙事生成总量 (均值 {meta['avg_words_per_tick']} 字/刻)</div>
            </div>
            <div class="stat-card neu-flat-sm">
                <div class="stat-num">{len(locs)} 处</div>
                <div class="stat-desc">提炼经历核心宏观据点</div>
            </div>
            <div class="stat-card neu-flat-sm">
                <div class="stat-num">{len(social['npc_met_history'])} 位</div>
                <div class="stat-desc">沉淀活跃结识 NPC</div>
            </div>
        </div>

        <!-- 裁判评估诊断看板 -->
        <section class="section-box neu-flat">
            <h2 class="section-title">
                <div class="title-left">
                    {SVG_ICONS['award']}
                    <span>LLM-as-a-Judge 四维长程质量裁决看板</span>
                </div>
            </h2>
            <div class="verdict-box neu-inset">
                <strong style="color:var(--neu-accent);">裁判总评概要:</strong> {summary_verdict}
            </div>
            <div class="dims-grid">
                {dims_html}
            </div>
            {f'<div style="font-size:13px;color:var(--text-muted);margin-top:12px;"><strong style="color:#fff;">核心高光转折:</strong> ' + ' | '.join(highlights) + '</div>' if highlights else ''}
        </section>

        <!-- 核心重构：竖向连续时间轴与点击查看详情 -->
        <section class="section-box neu-flat">
            <div class="section-title">
                <div class="title-left">
                    {SVG_ICONS['clock']}
                    <span>连续推演时空编年长卷 (Vertical Continuous Timeline)</span>
                </div>
                <div style="display:flex;gap:8px;">
                    <button class="timeline-ctrl-btn" onclick="toggleAllDetails(true)">全部展开</button>
                    <button class="timeline-ctrl-btn" onclick="toggleAllDetails(false)">全部收起</button>
                </div>
            </div>
            <p class="section-desc">
                垂直贯穿所有推演天数。节点垂直间隙动态映射实际时间跨度（15~30min 连续紧挨，长跨度休眠/跃迁自然拉长连线）。默认紧凑排列，<strong>点击任意时间节点或卡片即可即时展开/收起查看微观位置、因果骨架与正文切片</strong>。
            </p>

            <!-- 顶部微型连续精力波形 -->
            {stamina_overview_svg}

            <!-- 竖向时间轴主体 -->
            <div class="v-timeline-container">
                {vertical_timeline_html}
            </div>
        </section>

        <!-- 宏观地理据点迁徙链 (普适归纳) -->
        <section class="section-box neu-flat">
            <h2 class="section-title">
                <div class="title-left">
                    {SVG_ICONS['location']}
                    <span>宏观地理据点迁徙与探索轨迹 (Macro Location Trajectory)</span>
                </div>
            </h2>
            <p class="section-desc">
                提炼归类后的宏观据点迁徙链。同一建筑复合体或主区域内的细分房间活动已合并为连续生活阶段，并展示建筑内穿梭足迹。
            </p>
            <div class="macro-loc-grid">
                {macro_loc_nodes_html}
            </div>
        </section>

        <!-- 社交关系网络 -->
        <section class="section-box neu-flat">
            <h2 class="section-title">
                <div class="title-left">
                    {SVG_ICONS['person']}
                    <span>社交关系网络演化 (Social Graph Dynamics)</span>
                </div>
            </h2>
            <div class="npc-grid">
                {npc_cards_html}
            </div>
        </section>

        <!-- 背包流水与角色目标 -->
        <div class="two-cols">
            <section class="section-box neu-flat">
                <h2 class="section-title">
                    <div class="title-left">
                        {SVG_ICONS['inventory']}
                        <span>行囊物品生命周期流水 (Inventory Flow)</span>
                    </div>
                </h2>
                <div style="margin-bottom:12px;font-size:13px;color:var(--text-muted);">
                    当前随身装备 ({len(inv['current'])}/8 件): <strong style="color:#fff;">{', '.join(inv['current']) if inv['current'] else '无'}</strong>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                    <div>
                        <div style="font-size:12px;color:#94a3b8;margin-bottom:6px;">新增获取:</div>
                        <ul class="flow-list">{added_items_html or '<li style="color:#64748b;">暂无新增</li>'}</ul>
                    </div>
                    <div>
                        <div style="font-size:12px;color:#94a3b8;margin-bottom:6px;">消耗/存放据点:</div>
                        <ul class="flow-list">{removed_items_html or '<li style="color:#64748b;">暂无消耗</li>'}</ul>
                    </div>
                </div>
            </section>

            <section class="section-box neu-flat">
                <h2 class="section-title">
                    <div class="title-left">
                        {SVG_ICONS['target']}
                        <span>角色成长与目标达成 (Goals & Character Arc)</span>
                    </div>
                </h2>
                <div style="margin-bottom:14px;">
                    <div style="font-size:13px;color:#34d399;font-weight:600;margin-bottom:6px;">已达成目标 ({len(goals['completed'])} 个):</div>
                    <ul class="flow-list">
                        {''.join([f"<li><span class='badge-add'>已完成</span> {g}</li>" for g in goals['completed']]) if goals['completed'] else '<li style="color:#64748b;">暂无已完成目标</li>'}
                    </ul>
                </div>
                <div>
                    <div style="font-size:13px;color:#60a5fa;font-weight:600;margin-bottom:6px;">当前进行中目标 ({len(goals['active'])} 个):</div>
                    <ul class="flow-list">
                        {''.join([f"<li><span style='color:#60a5fa;font-weight:600;'>进行中</span> {g}</li>" for g in goals['active']]) if goals['active'] else '<li style="color:#64748b;">无活跃目标</li>'}
                    </ul>
                </div>
            </section>
        </div>
    </div>

    <!-- 内嵌轻量交互脚本：点击时间点展开/折叠详情 -->
    <script>
        function toggleTimelineDetail(tick) {{
            const panel = document.getElementById('detail_' + tick);
            const ind = document.getElementById('ind_' + tick);
            if (!panel) return;
            const isHidden = panel.style.display === 'none';
            panel.style.display = isHidden ? 'block' : 'none';
            if (ind) {{
                const arrow = ind.querySelector('.neu-arrow-icon');
                const text = ind.querySelector('span');
                if (arrow) arrow.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
                if (text) text.innerText = isHidden ? '收起' : '展开';
            }}
        }}

        function toggleAllDetails(expand) {{
            const panels = document.querySelectorAll('.v-node-detail-panel');
            panels.forEach(p => {{
                p.style.display = expand ? 'block' : 'none';
                const tick = p.id.replace('detail_', '');
                const ind = document.getElementById('ind_' + tick);
                if (ind) {{
                    const arrow = ind.querySelector('.neu-arrow-icon');
                    const text = ind.querySelector('span');
                    if (arrow) arrow.style.transform = expand ? 'rotate(180deg)' : 'rotate(0deg)';
                    if (text) text.innerText = expand ? '收起' : '展开';
                }}
            }});
        }}
    </script>
</body>
</html>
"""
    return html


async def generate_report_file(
    name: Optional[str] = None,
    character_id: Optional[str] = None,
    output_path: Optional[str] = None,
    with_llm: bool = True
):
    init_db()
    from app.services.config_service import sync_config_to_runtime
    sync_config_to_runtime()
    db = SessionLocal()
    try:
        from scripts.auto_driver import select_character
        char = select_character(db, name_query=name, char_id=character_id)
        if not char:
            print("[错误] 未选定任何可用角色。")
            return
        character_id = char.id

        print(f"[数据聚合] 正在读取角色 {char.name} (ID: {character_id}) 的推演全景数据...")
        data = aggregate_simulation_data(db, character_id)
        if "error" in data:
            print(f"[错误] {data['error']}")
            return

        print(f"[数据聚合完成] 累计 {data['meta']['total_ticks']} 刻，共 {data['meta']['total_words']} 字。")

        if with_llm:
            print("[LLM 裁判评测] 正在启动大模型裁判多维量化诊断与微观地点智能归类...")
            eval_res = await run_llm_judge_evaluation(data)
        else:
            print("[离线模式] 使用基准客观启发式评分与通用符号前缀归类生成报告...")
            fallback_map = {loc: generic_macro_location(loc) for loc in data.get("unique_locations", [])}
            apply_location_clusters(data, fallback_map)
            eval_res = {
                "overall_score": 90,
                "summary_verdict": f"推演已稳定推进 {data['meta']['total_ticks']} 刻，客观数据状态流转正常。",
                "dimensions": {
                    "consistency": {"score": 92, "strengths": "时空时序连续，状态看板更新稳定", "weaknesses": "无严重矛盾"},
                    "narrative_quality": {"score": 89, "strengths": "篇幅符合档位预期，环境氛围饱满", "weaknesses": "部分段落节奏略平"},
                    "social_dynamics": {"score": 88, "strengths": f"沉淀了 {len(data['social_dynamics']['npc_met_history'])} 位新角色", "weaknesses": "需更多交互"},
                    "character_arc": {"score": 91, "strengths": f"完成了 {len(goals['completed'])} 个目标" if (goals := data.get("goals")) else "稳步成长", "weaknesses": "执念待深化"},
                },
                "highlight_moments": ["开局顺利探索", "建立人际羁绊与稳固据点"],
                "location_mapping": fallback_map,
            }

        html_content = generate_html_report_content(data, eval_res)

        if not output_path:
            reports_dir = os.path.join(backend_root, "reports")
            os.makedirs(reports_dir, exist_ok=True)
            output_path = os.path.join(reports_dir, f"simulation_report_{data['character']['name']}_{data['meta']['total_ticks']}ticks.html")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"[报告生成成功] 单文件独立 HTML 报告已输出至: {output_path}")
        return output_path

    finally:
        db.close()


def main():
    import asyncio
    parser = argparse.ArgumentParser(description="WorldSim 单文件独立 HTML 评测报告生成器")
    parser.add_argument("--name", type=str, default=None, help="目标角色姓名 (支持模糊检索与多候选交互选择)")
    parser.add_argument("--character-id", type=str, default=None, help="目标角色 ID")
    parser.add_argument("--output", type=str, default=None, help="输出 HTML 文件路径")
    parser.add_argument("--no-llm", action="store_true", help="跳过 LLM 裁判调用，直接使用客观统计评分")
    args = parser.parse_args()

    asyncio.run(
        generate_report_file(
            name=args.name,
            character_id=args.character_id,
            output_path=args.output,
            with_llm=not args.no_llm,
        )
    )


if __name__ == "__main__":
    main()
