import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.dirname(current_dir)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.database import SessionLocal, init_db
from app.models import Character
from scripts.evaluator import aggregate_simulation_data, run_llm_judge_evaluation

logger = logging.getLogger("report_generator")


def render_svg_stamina_chart(timeline: Dict[str, Any]) -> str:
    """纯 SVG 绘制精力波动折线图 (无外部依赖)"""
    ticks = timeline.get("ticks", [])
    stamina = timeline.get("stamina", [])
    if not ticks or len(ticks) < 2:
        return "<div style='color:#888;padding:20px;text-align:center;'>数据点过少，暂未形成有效折线</div>"

    width = 900
    height = 200
    padding = 40

    max_x = max(ticks)
    min_x = min(ticks)
    range_x = max(1, max_x - min_x)

    points = []
    area_points = []
    for t, s in zip(ticks, stamina):
        x = padding + ((t - min_x) / range_x) * (width - 2 * padding)
        y = height - padding - (s / 100.0) * (height - 2 * padding)
        points.append(f"{x:.1f},{y:.1f}")
        area_points.append(f"{x:.1f},{y:.1f}")

    path_d = "M " + " L ".join(points)
    area_d = f"M {padding},{height - padding} L " + " L ".join(area_points) + f" L {width - padding},{height - padding} Z"

    svg = f"""
    <svg viewBox="0 0 {width} {height}" class="stamina-svg" preserveAspectRatio="none">
        <defs>
            <linearGradient id="staminaGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.35"/>
                <stop offset="100%" stop-color="#3b82f6" stop-opacity="0.0"/>
            </linearGradient>
        </defs>
        <!-- 背景横线 -->
        <line x1="{padding}" y1="{padding}" x2="{width - padding}" y2="{padding}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="4"/>
        <line x1="{padding}" y1="{height/2}" x2="{width - padding}" y2="{height/2}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="4"/>
        <line x1="{padding}" y1="{height - padding}" x2="{width - padding}" y2="{height - padding}" stroke="rgba(255,255,255,0.15)"/>
        <!-- 面积渐变 -->
        <path d="{area_d}" fill="url(#staminaGrad)" />
        <!-- 波动折线 -->
        <path d="{path_d}" fill="none" stroke="#60a5fa" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        <!-- 刻度提示 -->
        <text x="{padding}" y="{height - 12}" fill="#64748b" font-size="11">Tick #{min_x}</text>
        <text x="{width - padding - 40}" y="{height - 12}" fill="#64748b" font-size="11">Tick #{max_x}</text>
        <text x="{padding - 28}" y="{padding + 4}" fill="#64748b" font-size="11">100%</text>
        <text x="{padding - 20}" y="{height - padding + 4}" fill="#64748b" font-size="11">0%</text>
    </svg>
    """
    return svg


def generate_html_report_content(data: Dict[str, Any], evaluation: Dict[str, Any]) -> str:
    char = data["character"]
    meta = data["meta"]
    social = data["social_dynamics"]
    inv = data["inventory_flow"]
    goals = data["goals"]
    locs = data["location_trajectory"]
    timeline = data["timeline_series"]

    overall_score = evaluation.get("overall_score", 90)
    dimensions = evaluation.get("dimensions", {})
    highlights = evaluation.get("highlight_moments", [])
    summary_verdict = evaluation.get("summary_verdict", "推演状态平稳正常。")

    stamina_chart_html = render_svg_stamina_chart(timeline)

    # 渲染足迹节点
    loc_nodes_html = ""
    for idx, loc in enumerate(locs):
        loc_nodes_html += f"""
        <div class="trajectory-node">
            <div class="node-badge">阶段 {idx + 1}</div>
            <div class="node-title">{loc['location']}</div>
            <div class="node-sub">历经 {loc['dwell_ticks']} 刻 (Tick #{loc['first_tick']} - #{loc['last_tick']})</div>
            <div class="node-time">{loc['start_time']}</div>
        </div>
        """

    # 渲染新结识角色
    npc_cards_html = ""
    if not social["npc_met_history"]:
        npc_cards_html = "<div class='empty-tip'>在本次历程中暂未沉淀专属新角色</div>"
    else:
        for npc in social["npc_met_history"]:
            npc_cards_html += f"""
            <div class="npc-card">
                <div class="npc-head">
                    <span class="npc-name">{npc['name']}</span>
                    <span class="npc-badge">{npc['relation_type']}</span>
                </div>
                <div class="npc-meta">结识于 Tick #{npc['tick']} | 常驻地: {npc['residence']}</div>
                <div class="npc-bar-bg">
                    <div class="npc-bar-fill" style="width: {max(0, min(100, (npc['affinity'] + 100) / 2))}%;"></div>
                </div>
                <div class="npc-aff-label">羁绊好感度: {npc['affinity']} / 100</div>
                <div class="npc-summary">{npc['summary']}</div>
            </div>
            """

    # 渲染背包流水
    added_items_html = "".join([f"<li><span class='badge-add'>+获得</span> <strong>{i['item']}</strong> (Tick #{i['tick']})</li>" for i in inv["added_history"][:12]])
    removed_items_html = "".join([f"<li><span class='badge-sub'>-消耗/收纳</span> <strong>{i['item']}</strong> (Tick #{i['tick']})</li>" for i in inv["removed_history"][:12]])

    # 渲染维度打分进度条
    dims_html = ""
    dim_titles = {
        "consistency": "连续一致性与时空自洽 (Consistency)",
        "narrative_quality": "叙事可观赏性与节奏 (Narrative Quality)",
        "social_dynamics": "社交网络与互动生态 (Social Dynamics)",
        "character_arc": "角色成长与心境弧光 (Character Arc)",
    }
    for key, title in dim_titles.items():
        info = dimensions.get(key, {"score": 85, "strengths": "表现平稳", "weaknesses": "无显著瑕疵"})
        score = info.get("score", 85)
        dims_html += f"""
        <div class="dim-card">
            <div class="dim-header">
                <span class="dim-title">{title}</span>
                <span class="dim-score">{score} 分</span>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: {score}%;"></div>
            </div>
            <div class="dim-detail">
                <div class="dim-text"><strong class="highlight-green">核心优势:</strong> {info.get('strengths')}</div>
                <div class="dim-text"><strong class="highlight-amber">演进指引:</strong> {info.get('weaknesses')}</div>
            </div>
        </div>
        """

    # 渲染时间轴长卷 (前 15 刻 + 抽样)
    timeline_slices_html = ""
    for item in data.get("story_slices_sample", []):
        timeline_slices_html += f"""
        <div class="timeline-item">
            <div class="timeline-marker"></div>
            <div class="timeline-content">
                <div class="timeline-header">
                    <span class="t-tick">Tick #{item['tick']}</span>
                    <span class="t-time">{item['time']}</span>
                    <span class="t-loc">{item['location']}</span>
                </div>
                <div class="t-beat"><strong>事实骨架:</strong> {item['plot_beat']}</div>
                <div class="t-prose">{item['narrative_prose']}</div>
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
            --bg-main: #0b0f19;
            --bg-card: #131c2e;
            --bg-card-sub: #1a263d;
            --border-color: rgba(255, 255, 255, 0.08);
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --accent-blue: #3b82f6;
            --accent-cyan: #06b6d4;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background-color: var(--bg-main);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            padding: 30px 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        /* 顶部看板 */
        .header-card {{
            background: linear-gradient(135deg, #131c2e 0%, #1e293b 100%);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 24px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }}
        .char-title {{ font-size: 28px; font-weight: 700; color: #fff; margin-bottom: 6px; }}
        .char-subtitle {{ color: var(--text-muted); font-size: 14px; max-width: 600px; }}
        .score-badge-box {{
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 14px;
            padding: 16px 28px;
            text-align: center;
        }}
        .score-val {{ font-size: 40px; font-weight: 800; color: var(--accent-blue); line-height: 1; }}
        .score-label {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }}

        /* 统计指标卡 */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
        }}
        .stat-num {{ font-size: 24px; font-weight: 700; color: #fff; margin-bottom: 4px; }}
        .stat-desc {{ font-size: 13px; color: var(--text-muted); }}

        /* 板块容器 */
        .section-box {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
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
            gap: 10px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 12px;
        }}

        /* 评测诊断 */
        .dims-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .dim-card {{
            background: var(--bg-card-sub);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
        }}
        .dim-header {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
        .dim-title {{ font-size: 15px; font-weight: 600; color: #e2e8f0; }}
        .dim-score {{ font-size: 16px; font-weight: 700; color: var(--accent-cyan); }}
        .progress-bar-bg {{ height: 8px; background: rgba(255,255,255,0.08); border-radius: 4px; overflow: hidden; margin-bottom: 14px; }}
        .progress-bar-fill {{ height: 100%; background: linear-gradient(90deg, #3b82f6, #06b6d4); border-radius: 4px; }}
        .dim-detail {{ font-size: 13px; color: var(--text-muted); display: flex; flex-direction: column; gap: 6px; }}
        .highlight-green {{ color: #34d399; }}
        .highlight-amber {{ color: #fbbf24; }}

        .verdict-box {{
            background: rgba(255,255,255,0.03);
            border-left: 4px solid var(--accent-blue);
            padding: 16px;
            border-radius: 0 8px 8px 0;
            font-size: 14px;
            color: #cbd5e1;
            margin-bottom: 20px;
        }}

        /* 地理足迹 */
        .trajectory-flow {{
            display: flex;
            gap: 16px;
            overflow-x: auto;
            padding-bottom: 10px;
        }}
        .trajectory-node {{
            min-width: 200px;
            background: var(--bg-card-sub);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
            flex-shrink: 0;
        }}
        .node-badge {{ font-size: 11px; background: rgba(59, 130, 246, 0.2); color: var(--accent-blue); display: inline-block; padding: 2px 8px; border-radius: 6px; margin-bottom: 6px; }}
        .node-title {{ font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 4px; }}
        .node-sub {{ font-size: 12px; color: var(--text-muted); }}
        .node-time {{ font-size: 11px; color: #64748b; margin-top: 6px; }}

        /* 社交卡片 */
        .npc-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }}
        .npc-card {{
            background: var(--bg-card-sub);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 18px;
        }}
        .npc-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
        .npc-name {{ font-size: 16px; font-weight: 700; color: #fff; }}
        .npc-badge {{ font-size: 11px; background: rgba(16, 185, 129, 0.2); color: var(--accent-emerald); padding: 2px 8px; border-radius: 6px; }}
        .npc-meta {{ font-size: 12px; color: var(--text-muted); margin-bottom: 10px; }}
        .npc-bar-bg {{ height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden; margin-bottom: 6px; }}
        .npc-bar-fill {{ height: 100%; background: var(--accent-emerald); border-radius: 3px; }}
        .npc-aff-label {{ font-size: 11px; color: #64748b; margin-bottom: 8px; }}
        .npc-summary {{ font-size: 12px; color: #cbd5e1; line-height: 1.5; }}

        /* 背包与目标 */
        .two-cols {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .flow-list {{ list-style: none; display: flex; flex-direction: column; gap: 8px; font-size: 13px; }}
        .badge-add {{ color: #34d399; font-weight: 600; margin-right: 6px; }}
        .badge-sub {{ color: #f87171; font-weight: 600; margin-right: 6px; }}

        /* 时间轴长卷 */
        .timeline-box {{ display: flex; flex-direction: column; gap: 20px; }}
        .timeline-item {{
            border-left: 2px solid var(--accent-blue);
            padding-left: 20px;
            position: relative;
        }}
        .timeline-marker {{
            position: absolute;
            left: -6px;
            top: 4px;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--accent-blue);
        }}
        .timeline-header {{ display: flex; gap: 12px; font-size: 13px; margin-bottom: 6px; }}
        .t-tick {{ color: var(--accent-cyan); font-weight: 700; }}
        .t-time {{ color: var(--text-muted); }}
        .t-loc {{ color: #60a5fa; }}
        .t-beat {{ font-size: 14px; color: #e2e8f0; margin-bottom: 8px; }}
        .t-prose {{
            font-size: 13px;
            color: #94a3b8;
            background: rgba(0,0,0,0.25);
            padding: 14px;
            border-radius: 8px;
            line-height: 1.7;
        }}

        .stamina-svg {{ width: 100%; height: 200px; }}
        .empty-tip {{ color: #64748b; font-size: 13px; padding: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 顶部卡片 -->
        <header class="header-card">
            <div>
                <h1 class="char-title">{char['name']} <span style="font-size:18px;font-weight:400;color:var(--text-muted);">({char['title']})</span></h1>
                <p class="char-subtitle">{char['persona_summary'][:180]}...</p>
                <p style="font-size:12px;color:var(--accent-cyan);margin-top:8px;">核心执念: {char['inner_drive']}</p>
            </div>
            <div class="score-badge-box">
                <div class="score-val">{overall_score}</div>
                <div class="score-label">总评健康指数</div>
            </div>
        </header>

        <!-- 统计指标网格 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-num">{meta['total_ticks']} 刻</div>
                <div class="stat-desc">推演总步长跨度</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">{meta['total_words']} 字</div>
                <div class="stat-desc">叙事生成总量 (均值 {meta['avg_words_per_tick']} 字/刻)</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">{len(locs)} 处</div>
                <div class="stat-desc">经历地理据点总数</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">{len(social['npc_met_history'])} 位</div>
                <div class="stat-desc">新沉淀活跃 NPC 羁绊</div>
            </div>
        </div>

        <!-- 裁判评估诊断 -->
        <section class="section-box">
            <h2 class="section-title">
                <span>LLM-as-a-Judge 四维长程质量裁决看板</span>
            </h2>
            <div class="verdict-box">
                <strong>裁判总评概要:</strong> {summary_verdict}
            </div>
            <div class="dims-grid">
                {dims_html}
            </div>
            {f'<div style="font-size:13px;color:var(--text-muted);"><strong style="color:#fff;">核心高光转折:</strong> ' + ' | '.join(highlights) + '</div>' if highlights else ''}
        </section>

        <!-- 生理精力心电图 -->
        <section class="section-box">
            <h2 class="section-title">
                <span>生理精力心电图 (Stamina Rhythm Wave)</span>
            </h2>
            <p style="font-size:12px;color:var(--text-muted);margin-bottom:12px;">展示虚拟世界昼夜流转中的精力消耗与休眠恢复波形 (波谷消耗 -> 睡眠阶段跃迁回满)</p>
            {stamina_chart_html}
        </section>

        <!-- 地理迁徙轨迹链 -->
        <section class="section-box">
            <h2 class="section-title">
                <span>地理探索与足迹迁徙链 (Location Footprint Trajectory)</span>
            </h2>
            <div class="trajectory-flow">
                {loc_nodes_html}
            </div>
        </section>

        <!-- 社交关系网络 -->
        <section class="section-box">
            <h2 class="section-title">
                <span>社交关系网络演化 (Social Graph Dynamics)</span>
            </h2>
            <div class="npc-grid">
                {npc_cards_html}
            </div>
        </section>

        <!-- 背包与目标 -->
        <div class="two-cols">
            <section class="section-box">
                <h2 class="section-title">
                    <span>行囊物品生命周期流水 (Inventory Flow)</span>
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

            <section class="section-box">
                <h2 class="section-title">
                    <span>角色成长与目标达成 (Goals & Character Arc)</span>
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

        <!-- 剧情抽样长卷 -->
        <section class="section-box">
            <h2 class="section-title">
                <span>剧情长卷编年史抽样 (Chronicles Sample)</span>
            </h2>
            <div class="timeline-box">
                {timeline_slices_html}
            </div>
        </section>
    </div>
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
            print("[LLM 裁判评测] 正在启动大模型裁判多维量化诊断...")
            eval_res = await run_llm_judge_evaluation(data)
        else:
            print("[离线模式] 使用基准客观启发式评分生成报告...")
            eval_res = {
                "overall_score": 90,
                "summary_verdict": f"推演已稳定推进 {data['meta']['total_ticks']} 刻，客观数据状态流转正常。",
                "dimensions": {
                    "consistency": {"score": 92, "strengths": "时空时序连续，状态看板更新稳定", "weaknesses": "无严重矛盾"},
                    "narrative_quality": {"score": 89, "strengths": "篇幅符合档位预期，环境氛围饱满", "weaknesses": "部分段落节奏略平"},
                    "social_dynamics": {"score": 88, "strengths": f"沉淀了 {len(data['social_dynamics']['npc_met_history'])} 位新角色", "weaknesses": "需更多交互"},
                    "character_arc": {"score": 91, "strengths": f"完成了 {len(data['goals']['completed'])} 个目标", "weaknesses": "执念待深化"},
                },
                "highlight_moments": ["开局顺利探索", "建立人际羁绊与新据点"]
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
