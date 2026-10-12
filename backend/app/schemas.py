from datetime import datetime
from typing import List, Optional, Any, Dict, Union
from pydantic import BaseModel, Field, field_validator


# -----------------------------
# 作息画像定义
# -----------------------------
class CircadianProfile(BaseModel):
    chronotype: str = Field(..., description="生理节奏倾向: 早起型 | 夜行型 | 昼夜无律型 | 无休眠体质")
    typical_rest_window: str = Field(..., description="常规休眠倾向窗口，例如 23:00 - 07:00")
    environment_tolerance: str = Field(..., description="环境耐受度，如 安全庇护所/旅馆床铺 或 随时随地浅睡")
    sleep_trigger_summary: Optional[str] = Field("", description="休眠触发逻辑简要概述")


# -----------------------------
# 角色卡摄入相关
# -----------------------------
class DetectedRelationship(BaseModel):
    npc_name: str
    relation_type: str = "相识"
    affinity: int = 50
    summary: str = ""
    residence_location: Optional[str] = ""


class DetectedEntity(BaseModel):
    entity_id: str
    name: str
    title: Optional[str] = None
    gender: Optional[str] = Field("保密", description="生理/社会性别 (男 | 女 | 其他/非二元 | 无性别/未知)")
    birthday: Optional[str] = Field("", description="生日或诞生时间（如 '2007年3月15日' 或 '天禧二年五月初三'），用于随虚拟世界时间流逝动态推演周岁")
    appearance: Optional[str] = Field("", description="外貌体征与服饰细节 (身高、体型、发色瞳色、显著身体标志与常驻装束)")
    avatar_url: Optional[str] = None
    persona_summary: str
    inner_drive: str
    circadian_profile: CircadianProfile
    relationships_with_others: Optional[str] = ""
    relationships: List[DetectedRelationship] = Field(default_factory=list, description="该实体主视角下专属的社交关系网（含其他主要角色、公共NPC及替代user的具象化NPC）")
    initial_location: Optional[str] = "初始场景"
    initial_residence: Optional[str] = "常驻居所"
    initial_virtual_time: Optional[str] = "2026年10月10日 08:00"
    initial_health: Optional[int] = 100
    initial_stamina: Optional[int] = 90
    initial_psychological_state: Optional[str] = "警惕且冷静"
    initial_inventory: Optional[List[str]] = []
    initial_goals: Optional[List[str]] = []


class WorldLoreInput(BaseModel):
    category: str = "static"  # static | dynamic
    trigger_keys: Optional[str] = ""
    title: str
    content: str


class WorldLoreUpdate(BaseModel):
    category: Optional[str] = None  # static | dynamic
    trigger_keys: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[int] = None


class CardParseResponse(BaseModel):
    is_multi_entity: bool
    detected_entities: List[DetectedEntity]
    detected_relationships: List[DetectedRelationship] = []
    total_lore_entries: int
    lores: List[WorldLoreInput]
    raw_preview: Optional[Dict[str, Any]] = None
    user_replacement_hint: Optional[str] = None


class CardImportRequest(BaseModel):
    selected_entity: DetectedEntity
    all_entities: List[DetectedEntity] = []
    lores: List[WorldLoreInput] = []
    relationships: List[DetectedRelationship] = []
    initial_location: Optional[str] = None
    initial_residence: Optional[str] = None
    initial_virtual_time: Optional[str] = None
    initial_health: Optional[int] = None
    initial_stamina: Optional[int] = None
    initial_psychological_state: Optional[str] = None
    initial_inventory: Optional[List[str]] = None
    initial_goals: Optional[List[str]] = None


class QuickCharacterRequest(BaseModel):
    name: Optional[str] = Field(default="", description="角色姓名（可选，未填由AI生成）")
    gender: Optional[str] = Field(default="", description="性别（可选，男/女/保密/自定义）")
    birthday: Optional[str] = Field(default="", description="生日或历法时间（可选）")
    role: Optional[str] = Field(default="", description="社会身份或职业（可选）")
    appearance: Optional[str] = Field(default="", description="外貌特征描述（可选）")
    archetype: Optional[str] = Field(default="", description="性格底色与处事风格（可选）")
    world_guidance: Optional[str] = Field(default="", description="世界观、社交圈与人际羁绊引导（可选）")
    initial_situation: Optional[str] = Field(default="", description="开局微观处境与危机（可选）")
    initial_residence: Optional[str] = Field(default="", description="常驻居所/安全据点（可选，未填由AI自主构思）")


# -----------------------------
# 裁决机 Pass 1 结构化输出
# -----------------------------
class RestDecision(BaseModel):
    is_sleeping: bool = False
    sleep_quality: str = "none"  # none | light | deep
    rest_reason: str = ""


class InventoryDelta(BaseModel):
    added: List[str] = []
    removed: List[str] = []


class GoalDelta(BaseModel):
    completed: List[str] = []
    added: List[str] = []
    current_active: List[str] = []


class NPCRelationshipDeltaItem(BaseModel):
    npc_name: str
    relation_type: Optional[str] = None
    affinity: Optional[Union[int, str]] = None  # 支持最新绝对值(int)或相对增减量(如 "+5", "-2")；为 None 时严格继承上一刻数值
    summary: Optional[str] = None
    is_present: Optional[bool] = None
    residence_location: Optional[str] = None  # 常驻据点或流动状态（如 "晨曦镇学徒工坊" 或 "四海行踪不定/云游"）

    @field_validator("affinity", mode="before")
    @classmethod
    def parse_affinity_val(cls, v):
        if v is None or v == "":
            return None
        return v

    @field_validator("relation_type", mode="before")
    @classmethod
    def parse_relation_type_val(cls, v):
        if v is None or not str(v).strip():
            return None
        return str(v).strip()

    @field_validator("residence_location", mode="before")
    @classmethod
    def parse_residence_val(cls, v):
        if v is None or not str(v).strip():
            return None
        return str(v).strip()


class RelationshipDelta(BaseModel):
    new_npcs: List[NPCRelationshipDeltaItem] = []
    updated_npcs: List[NPCRelationshipDeltaItem] = []
    pruned_npcs: List[str] = []  # 因时过境迁、久未联系或主角远行而自然淡出活跃圈的 NPC 姓名数组


class ArbitratorDelta(BaseModel):
    simulated_hours_passed: float = 1.0
    new_virtual_time: str
    new_location: str
    new_residence: Optional[str] = None  # 本轮推演后主角的最新安身据点/庇护所（若发生据点迁移或流浪时更新）
    rest_decision: RestDecision
    health_delta: int = 0
    stamina_delta: int = 0
    psychological_change: str
    inventory_delta: InventoryDelta = Field(default_factory=InventoryDelta)
    goal_delta: GoalDelta = Field(default_factory=GoalDelta)
    relationship_delta: RelationshipDelta = Field(default_factory=RelationshipDelta)
    plot_beat: str
    sensory_cues: List[str]


# -----------------------------
# 状态看板与故事切片
# -----------------------------
class CharacterStateView(BaseModel):
    id: int
    character_id: str
    virtual_time: str
    location: str
    residence: Optional[str] = ""
    health: int
    stamina: int
    is_sleeping: int
    psychological_state: str
    inventory: List[str]
    active_goals: List[str]
    completed_goals: List[str]
    total_ticks: int
    updated_at: Optional[datetime] = None


class StoryLogView(BaseModel):
    id: int
    character_id: str
    tick_index: int
    virtual_time: str
    location: str
    plot_beat: str
    narrative_prose: str
    delta_snapshot: ArbitratorDelta
    created_at: Optional[datetime] = None


class StoryLogUpdateRequest(BaseModel):
    narrative_prose: str
    plot_beat: Optional[str] = None


class CharacterRelationshipView(BaseModel):
    id: int
    npc_name: str
    relation_type: str
    affinity: int
    summary: str
    is_present: int
    residence_location: Optional[str] = ""
    last_interacted_virtual_time: Optional[str] = ""
    is_archived: int = 0


class CharacterDetailView(BaseModel):
    id: str
    name: str
    title: Optional[str] = None
    avatar_url: Optional[str] = None
    persona_summary: str
    inner_drive: str
    circadian_profile: CircadianProfile
    is_active: int
    state: Optional[CharacterStateView] = None
    relationships: List[CharacterRelationshipView] = []
    world_lores_count: int = 0


# -----------------------------
# 推进请求与提示词/文风配置
# -----------------------------
class SimulationPromptConfig(BaseModel):
    style_preset: Optional[str] = "free"
    word_count_tier: Optional[str] = "standard"
    min_words: Optional[int] = 500
    max_words: Optional[int] = 800
    enabled_patches: Optional[List[str]] = Field(
        default_factory=lambda: ["plain_sketch", "living_dialogue", "anti_summary", "living_grounding", "camera_focus"]
    )
    custom_style_guidance: Optional[str] = ""
    pass1_custom_prompt: Optional[str] = None
    pass2_custom_prompt: Optional[str] = None
    enable_phone_simulation: Optional[bool] = None


class SimStepRequest(BaseModel):
    character_id: str
    hours: int = 1
    config: Optional[SimulationPromptConfig] = None


class SimContinueRequest(BaseModel):
    character_id: str
    config: Optional[SimulationPromptConfig] = None


class SimFastForwardRequest(BaseModel):
    character_id: str
    step_type: str  # hour_6 | day_1
    config: Optional[SimulationPromptConfig] = None


class SimTriggerIncidentRequest(BaseModel):
    character_id: str
    incident_description: Optional[str] = None
    config: Optional[SimulationPromptConfig] = None


class StepTickResponse(BaseModel):
    character_id: str
    story_log: StoryLogView
    current_state: CharacterStateView


class TimelinePageResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[StoryLogView]
