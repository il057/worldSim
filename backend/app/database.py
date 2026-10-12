from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# SQLite configuration: check_same_thread=False for async/FastAPI concurrency
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # 动态检测并自动补齐 SQLite 角色表字段（平滑数据迁移）
    if settings.DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                cursor = conn.execute(text("PRAGMA table_info(characters)"))
                columns = [row[1] for row in cursor.fetchall()]
                if columns:
                    if "gender" not in columns:
                        conn.execute(text("ALTER TABLE characters ADD COLUMN gender VARCHAR(32) DEFAULT '保密'"))
                    if "birthday" not in columns:
                        conn.execute(text("ALTER TABLE characters ADD COLUMN birthday VARCHAR(64) DEFAULT ''"))
                    if "appearance" not in columns:
                        conn.execute(text("ALTER TABLE characters ADD COLUMN appearance TEXT DEFAULT ''"))
                    conn.commit()

                # 动态检测并自动补齐角色人际关系表字段
                rel_cursor = conn.execute(text("PRAGMA table_info(character_relationships)"))
                rel_columns = [row[1] for row in rel_cursor.fetchall()]
                if rel_columns:
                    if "residence_location" not in rel_columns:
                        conn.execute(text("ALTER TABLE character_relationships ADD COLUMN residence_location VARCHAR(128) DEFAULT ''"))
                    if "last_interacted_virtual_time" not in rel_columns:
                        conn.execute(text("ALTER TABLE character_relationships ADD COLUMN last_interacted_virtual_time VARCHAR(64) DEFAULT ''"))
                    if "is_archived" not in rel_columns:
                        conn.execute(text("ALTER TABLE character_relationships ADD COLUMN is_archived INTEGER DEFAULT 0"))
                    conn.commit()

                # 动态检测并自动补齐角色即时状态表据点字段
                state_cursor = conn.execute(text("PRAGMA table_info(character_states)"))
                state_columns = [row[1] for row in state_cursor.fetchall()]
                if state_columns and "residence" not in state_columns:
                    conn.execute(text("ALTER TABLE character_states ADD COLUMN residence VARCHAR(128) DEFAULT ''"))
                    conn.commit()
        except Exception as e:
            import logging
            logging.getLogger("world_sim.db").warning(f"SQLite 自动列补齐检测提示: {e}")
