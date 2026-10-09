import os
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import init_db, SessionLocal
from app.models import Character, CharacterState, WorldLore, StoryLog
from app.routers import cards, characters, simulation
from app.services.scheduler import start_scheduler, shutdown_scheduler


def seed_default_character():
    """若数据库为空，初始化一个默认测试角色以保证即开即用体验"""
    db = SessionLocal()
    try:
        count = db.query(Character).count()
        if count == 0:
            char_id = "c-default-gwen"
            circadian = {
                "chronotype": "夜行型",
                "typical_rest_window": "05:00 - 12:00",
                "environment_tolerance": "隐蔽地下工坊或挂锁单间",
                "sleep_trigger_summary": "习惯于夜幕下调试机芯，黎明破晓前极度疲劳下方才浅眠",
            }
            char = Character(
                id=char_id,
                name="格温·艾尔斯",
                title="黑市钟表匠",
                avatar_url="",
                persona_summary="沉默、严谨、对发条与齿轮咬合拥有近乎神经质的敏感度。外表冷漠戒备，但信守契约底线。",
                inner_drive="查明导师在旧工坊坍塌事故中的死因，寻回遗失的永动发条核心。",
                circadian_profile_json=json.dumps(circadian, ensure_ascii=False),
                is_active=1,
            )
            db.add(char)

            state = CharacterState(
                character_id=char_id,
                virtual_time="霜降月 14日 21:00",
                location="旧铁道桥下的避雨涵洞工坊",
                health=100,
                stamina=85,
                is_sleeping=0,
                psychological_state="沉着专注，略有戒备",
                inventory_json=json.dumps(["多功能黄铜螺丝刀", "怀表机芯残件", "火柴半盒", "陈旧皮革手套"], ensure_ascii=False),
                active_goals_json=json.dumps(["检修开裂的动力核心", "排查涵洞外的巡逻队动向"], ensure_ascii=False),
                completed_goals_json="[]",
                total_ticks=1,
            )
            db.add(state)

            lore1 = WorldLore(
                character_id=char_id,
                category="static",
                trigger_keys="",
                title="铁轨区与废弃蒸汽法理",
                content="铁轨区是下城最边缘的无序夹缝。蒸汽主管道常年在此低沉轰鸣，冷凝水与锈水顺着桥墩滴落，黑市商人与流亡工匠在此互通有无。",
                is_active=1,
            )
            lore2 = WorldLore(
                character_id=char_id,
                category="dynamic",
                trigger_keys="动力核心,发条,机芯",
                title="微型动力机芯技术",
                content="高精度的微型动力机芯能在上满发条后连续驱动精密仪轨七十二小时，由于内嵌禁忌合金，被内城执法官列为一类违禁管制品。",
                is_active=1,
            )
            db.add(lore1)
            db.add(lore2)

            # 初始故事第一章
            delta_init = {
                "simulated_hours_passed": 1,
                "new_virtual_time": "霜降月 14日 21:00",
                "new_location": "旧铁道桥下的避雨涵洞工坊",
                "rest_decision": {"is_sleeping": False, "sleep_quality": "none", "rest_reason": "专注组装零件"},
                "health_delta": 0,
                "stamina_delta": -5,
                "psychological_change": "沉着专注，略有戒备",
                "inventory_delta": {"added": ["多功能黄铜螺丝刀", "怀表机芯残件"], "removed": []},
                "goal_delta": {"completed": [], "added": [], "current_active": ["检修开裂的动力核心", "排查涵洞外的巡逻队动向"]},
                "plot_beat": "格温将煤油灯芯挑亮，用浸过机油的软布擦拭受损的差速轴承，确认了外界暂无逼近的警报脚步声。",
                "sensory_cues": ["煤油灯微弱的硫磺焦味", "雨水顺着生锈铁架滴答作响", "掌心传来的冷铁触感"],
            }
            prose_init = (
                "雨水敲打在生锈的铁皮檐口。格温把最后一枚滚珠卡入嵌槽，指节上沾满乌黑的润滑油脂。"
                "煤油灯的火苗在穿堂风里抖了抖，昏黄的微光顺着长桌延展，将散落的游标卡尺和细齿锉刀染上一层哑光铜色。"
                "她没有停下手里的动作，只是微微屏息聆听着外面的巷道——远处蒸汽主管定期的泄压声沉闷地穿透雨幕，"
                "除此之外，只有积水顺着砖缝汩汩流淌的响动。她将发条旋紧了半圈，金属在掌心回馈出冷硬而精准的抵抗力。"
            )
            story = StoryLog(
                character_id=char_id,
                tick_index=1,
                virtual_time="霜降月 14日 21:00",
                location="旧铁道桥下的避雨涵洞工坊",
                plot_beat=delta_init["plot_beat"],
                narrative_prose=prose_init,
                delta_snapshot_json=json.dumps(delta_init, ensure_ascii=False),
            )
            db.add(story)

            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动阶段
    init_db()
    from app.services.config_service import sync_config_to_runtime
    sync_config_to_runtime()
    seed_default_character()
    start_scheduler()
    yield
    # 关闭阶段
    shutdown_scheduler()


app = FastAPI(
    title="World Simulation Engine",
    description="自主演化世界模拟推演引擎后端",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 API 路由
app.include_router(cards.router)
app.include_router(characters.router)
app.include_router(simulation.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "World Simulation Dual-Clock Engine"}


# 静态前端资源挂载与通配 SPA 回退处理
static_path = settings.STATIC_DIR
assets_path = os.path.join(static_path, "assets")

if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str, request: Request):
    """SPA 客户端路由通配回退兜底"""
    # 避开 API 前缀
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "API endpoint not found"})

    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)

    # 前端尚未构建时的友好状态页
    return JSONResponse(
        status_code=200,
        content={
            "service": "World Simulation Engine API is Running",
            "frontend_status": "Static build dist not yet mounted, please build frontend",
            "docs": "/docs",
            "api_health": "/api/health",
        },
    )
