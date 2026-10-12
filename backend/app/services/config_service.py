import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import SystemConfig
from app.services.llm_client import llm_client

logger = logging.getLogger("world_sim.config")

# 默认配置项
DEFAULT_CONFIGS: Dict[str, str] = {
    "llm_base_url": "https://api.openai.com/v1",
    "llm_api_key": "",
    "llm_model_name": "gpt-4o-mini",
    "llm_context_window": "60000",
    "llm_temperature": "1.0",
    "llm_frequency_penalty": "0.0",
    "llm_presence_penalty": "0.0",
    "llm_top_p": "1.0",
    "enable_realtime_sync": "false",
    "realtime_tick_hours": "1",
    "enable_stream_display": "true",
    "enable_phone_simulation": "false",
    "simulation_prompt_config": "",  # 全局持久化的推演提示词与文风配置 JSON
}


def get_all_system_configs(db: Optional[Session] = None) -> Dict[str, str]:
    """从数据库读取系统配置，缺省项回退至默认配置"""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        rows = db.query(SystemConfig).all()
        config_map = {row.key: row.value for row in rows}

        merged = {}
        for k, default_val in DEFAULT_CONFIGS.items():
            merged[k] = config_map.get(k, default_val)

        return merged
    finally:
        if should_close:
            db.close()


def get_simulation_prompt_config(db: Optional[Session] = None) -> Any:
    """读取保存在系统配置表中的全局推演提示词与文风配置（若不存在则返回标准默认配置）"""
    import json
    from app.schemas import SimulationPromptConfig
    cfg = get_all_system_configs(db)
    raw_prompt_cfg = cfg.get("simulation_prompt_config")
    phone_sim_enabled = cfg.get("enable_phone_simulation", "false").lower() == "true"

    if raw_prompt_cfg and raw_prompt_cfg.strip():
        try:
            data = json.loads(raw_prompt_cfg)
            if isinstance(data, dict):
                data["enable_phone_simulation"] = phone_sim_enabled
                return SimulationPromptConfig(**data)
        except Exception as e:
            logger.warning(f"解析全局 simulation_prompt_config 异常: {e}")
    default_cfg = SimulationPromptConfig()
    default_cfg.enable_phone_simulation = phone_sim_enabled
    return default_cfg


def save_system_configs(updates: Dict[str, Any], db: Optional[Session] = None) -> Dict[str, str]:
    """持久化系统配置至数据库并热更新运行期 client"""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        for key, value in updates.items():
            if value is None:
                continue
            str_val = str(value)
            row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if row:
                row.value = str_val
            else:
                row = SystemConfig(key=key, value=str_val)
                db.add(row)
        db.commit()

        # 加载最新配置并同步至 llm_client
        latest = get_all_system_configs(db)
        sync_config_to_runtime(latest)
        return latest
    finally:
        if should_close:
            db.close()


def sync_config_to_runtime(cfg: Optional[Dict[str, str]] = None) -> None:
    """同步配置至运行期 LLMClient"""
    if cfg is None:
        cfg = get_all_system_configs()

    llm_client.base_url = (cfg.get("llm_base_url") or "").rstrip("/")
    llm_client.api_key = cfg.get("llm_api_key") or ""
    llm_client.model_name = cfg.get("llm_model_name") or "gpt-4o-mini"
    try:
        llm_client.context_window = int(cfg.get("llm_context_window", "60000"))
    except ValueError:
        llm_client.context_window = 60000

    try:
        llm_client.temperature = float(cfg.get("llm_temperature", "1.0"))
    except ValueError:
        llm_client.temperature = 1.0

    try:
        llm_client.frequency_penalty = float(cfg.get("llm_frequency_penalty", "0.0"))
    except ValueError:
        llm_client.frequency_penalty = 0.0

    try:
        llm_client.presence_penalty = float(cfg.get("llm_presence_penalty", "0.0"))
    except ValueError:
        llm_client.presence_penalty = 0.0

    try:
        llm_client.top_p = float(cfg.get("llm_top_p", "1.0"))
    except ValueError:
        llm_client.top_p = 1.0

    from app.config import settings
    settings.ENABLE_REALTIME_SYNC = cfg.get("enable_realtime_sync", "false").lower() == "true"
    try:
        settings.REALTIME_TICK_HOURS = max(1, int(cfg.get("realtime_tick_hours", "1")))
    except ValueError:
        settings.REALTIME_TICK_HOURS = 1

    logger.info(
        "系统 LLM 运行期配置已热更新，模型: %s, 目标: %s, 上下文上限: %d, 温度: %.2f, 频率惩罚: %.2f, 存在惩罚: %.2f, Top P: %.2f, 现实同步演化: %s(每 %d 小时)",
        llm_client.model_name,
        llm_client.base_url,
        llm_client.context_window,
        llm_client.temperature,
        llm_client.frequency_penalty,
        llm_client.presence_penalty,
        llm_client.top_p,
        "开启" if settings.ENABLE_REALTIME_SYNC else "关闭",
        settings.REALTIME_TICK_HOURS,
    )
