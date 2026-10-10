import os
from pydantic_settings import BaseSettings


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "world_sim.db")


class Settings(BaseSettings):
    DATABASE_URL: str = f"sqlite:///{DB_PATH.replace(os.sep, '/')}"
    PORT: int = 8080
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"
    ENABLE_REALTIME_SYNC: bool = False
    REALTIME_TICK_HOURS: int = 1
    STATIC_DIR: str = os.path.join(BASE_DIR, "static")

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
if settings.DATABASE_URL.startswith("sqlite:///./") or settings.DATABASE_URL == "sqlite:///world_sim.db":
    settings.DATABASE_URL = f"sqlite:///{DB_PATH.replace(os.sep, '/')}"
