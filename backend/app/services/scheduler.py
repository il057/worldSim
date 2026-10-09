import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import settings
from app.database import SessionLocal
from app.models import Character
from app.services.simulation import SimulationService

logger = logging.getLogger("world_sim.scheduler")

scheduler = AsyncIOScheduler()


async def scheduled_realtime_tick():
    """现实时钟驱动定时任务：按设定周期遍历激活角色进行自动演化"""
    logger.info("触发真实时钟定时演化 Tick...")
    db = SessionLocal()
    try:
        active_chars = db.query(Character).filter(Character.is_active == 1).all()
        for char in active_chars:
            try:
                logger.info(f"正在对角色 {char.name}({char.id}) 执行自适应定时推演...")
                await SimulationService.run_step(db, char.id, hours=settings.REALTIME_TICK_HOURS)
            except Exception as e:
                logger.error(f"角色 {char.name} 定时推演异常: {e}")
    finally:
        db.close()


def start_scheduler():
    """启动调度器"""
    if not scheduler.running:
        scheduler.add_job(
            scheduled_realtime_tick,
            "interval",
            hours=settings.REALTIME_TICK_HOURS,
            id="realtime_world_tick",
            replace_existing=True,
        )
        scheduler.start()
        logger.info(f"双轨时钟引擎后台调度器已启动，每 {settings.REALTIME_TICK_HOURS} 小时自动推进一次。")


def shutdown_scheduler():
    """关闭调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("双轨时钟引擎后台调度器已停止。")
