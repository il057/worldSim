from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Character(Base):
    __tablename__ = "characters"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    title = Column(String(128), nullable=True)
    avatar_url = Column(Text, nullable=True)
    gender = Column(String(32), nullable=True, default="保密")
    birthday = Column(String(64), nullable=True, default="")
    appearance = Column(Text, nullable=True, default="")
    persona_summary = Column(Text, nullable=False)
    inner_drive = Column(Text, nullable=False)
    circadian_profile_json = Column(Text, nullable=False)
    initial_snapshot_json = Column(Text, nullable=True)  # 开局全量初始设置快照（用于纯净重置历史）
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    state = relationship("CharacterState", back_populates="character", uselist=False, cascade="all, delete-orphan")
    story_logs = relationship("StoryLog", back_populates="character", cascade="all, delete-orphan", order_by="StoryLog.tick_index")
    world_lores = relationship("WorldLore", back_populates="character", cascade="all, delete-orphan")
    relationships = relationship("CharacterRelationship", back_populates="character", cascade="all, delete-orphan")


class CharacterState(Base):
    __tablename__ = "character_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(String(64), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, unique=True)
    virtual_time = Column(String(128), nullable=False)
    location = Column(String(256), nullable=False)
    residence = Column(String(128), default="")  # 当前阶段安身据点/住所（支持随远行游历动态迁移）
    health = Column(Integer, default=100)
    stamina = Column(Integer, default=100)
    is_sleeping = Column(Integer, default=0)
    psychological_state = Column(Text, nullable=False)
    inventory_json = Column(Text, nullable=False, default="[]")
    active_goals_json = Column(Text, nullable=False, default="[]")
    completed_goals_json = Column(Text, nullable=False, default="[]")
    total_ticks = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    character = relationship("Character", back_populates="state")


class StoryLog(Base):
    __tablename__ = "story_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(String(64), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    tick_index = Column(Integer, nullable=False)
    virtual_time = Column(String(128), nullable=False)
    location = Column(String(256), nullable=False)
    plot_beat = Column(Text, nullable=False)
    narrative_prose = Column(Text, nullable=False)
    delta_snapshot_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    character = relationship("Character", back_populates="story_logs")

    __table_args__ = (
        Index("idx_story_logs_char_tick", "character_id", "tick_index"),
    )


class WorldLore(Base):
    __tablename__ = "world_lores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(String(64), ForeignKey("characters.id", ondelete="CASCADE"), nullable=True)
    category = Column(String(32), nullable=False)  # static | dynamic
    trigger_keys = Column(Text, nullable=True)      # comma separated keys
    title = Column(String(256), nullable=False)
    content = Column(Text, nullable=False)
    is_active = Column(Integer, default=1)

    character = relationship("Character", back_populates="world_lores")


class CharacterRelationship(Base):
    __tablename__ = "character_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(String(64), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    npc_name = Column(String(128), nullable=False)
    relation_type = Column(String(64), nullable=False)  # 同行者 | 契约者 | 故人 | 敌对
    affinity = Column(Integer, default=50)              # -100 to 100
    summary = Column(Text, nullable=False)
    is_present = Column(Integer, default=0)
    residence_location = Column(String(128), default="")           # 常驻地或流动状态（如 "晨曦镇学徒工坊" 或 "四海行踪不定/云游"）
    last_interacted_virtual_time = Column(String(64), default="") # 最后交互的虚拟时间
    is_archived = Column(Integer, default=0)                      # 0: 活跃关系; 1: 已因时过境迁自然淡化归档
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    character = relationship("Character", back_populates="relationships")


class SystemConfig(Base):
    __tablename__ = "system_configs"

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

