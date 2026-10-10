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
    if not settings.ENABLE_REALTIME_SYNC:
        logger.info("现实时钟同步演化未开启，跳过本次定时演化。")
        return

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


def update_scheduler_job(enabled: bool, hours: int = 1):
    """动态更新或启停后台现实时间同步演化调度任务"""
    JOB_ID = "realtime_world_tick"
    settings.ENABLE_REALTIME_SYNC = enabled
    settings.REALTIME_TICK_HOURS = max(1, hours)

    if not scheduler.running:
        return

    job = scheduler.get_job(JOB_ID)
    if enabled:
        if job:
            scheduler.reschedule_job(JOB_ID, trigger="interval", hours=settings.REALTIME_TICK_HOURS)
            logger.info(f"现实同步演化调度任务已更新周期: 每 {settings.REALTIME_TICK_HOURS} 小时触发一次。")
        else:
            scheduler.add_job(
                scheduled_realtime_tick,
                "interval",
                hours=settings.REALTIME_TICK_HOURS,
                id=JOB_ID,
                replace_existing=True,
            )
            logger.info(f"现实同步演化调度任务已开启挂载: 每 {settings.REALTIME_TICK_HOURS} 小时自动推进一次。")
    else:
        if job:
            scheduler.remove_job(JOB_ID)
            logger.info("现实同步演化调度任务已移除，后台自动推演已暂停（杜绝产生额外 API 费用）。")
        else:
            logger.info("现实同步演化调度任务当前处于关闭状态。")


def start_scheduler():
    """启动调度器"""
    if not scheduler.running:
        scheduler.start()
        logger.info("双轨时钟引擎后台调度器框架已启动。")
    
    from app.services.config_service import get_all_system_configs
    cfg = get_all_system_configs()
    enabled = cfg.get("enable_realtime_sync", "false").lower() == "true"
    try:
        hours = max(1, int(cfg.get("realtime_tick_hours", str(settings.REALTIME_TICK_HOURS))))
    except ValueError:
        hours = 1
    update_scheduler_job(enabled=enabled, hours=hours)


def shutdown_scheduler():
    """关闭调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("双轨时钟引擎后台调度器已停止。")
