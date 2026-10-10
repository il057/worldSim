import logging
from typing import Optional, Callable, Any
from sqlalchemy.orm import Session
from app.models import Character, CharacterState
from app.schemas import ArbitratorDelta, SimulationPromptConfig
from app.services.llm_client import llm_client, strip_emojis
from app.services.memory import MemoryService
from app.services.prompt_library import build_storyteller_system_prompt, WORD_COUNT_TIERS

logger = logging.getLogger("world_sim.storyteller")

class StorytellerError(Exception):
    def __init__(self, message: str, error_code: str = "PASS2_FAILED", raw_error: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.raw_error = raw_error


class StorytellerService:
    @classmethod
    async def narrate_tick(
        cls,
        db: Session,
        character: Character,
        state: CharacterState,
        delta: ArbitratorDelta,
        config: Optional[SimulationPromptConfig] = None,
        on_chunk: Optional[Callable[[str], Any]] = None,
    ) -> str:
        """
        Pass 2: 场景小说生成器 (Storyteller Engine)
        以第三人称有限视角，将 Pass 1 事实骨架转化为富有环境感官沉浸感的纯净小说正文
        支持文风选择、技法补丁叠加与精细字数篇幅控制
        """
        # 加载 10~15 轮 Deep Working Buffer
        recent_logs = MemoryService.get_tier2_working_buffer(db, character.id, limit=12)
        working_buffer_text = MemoryService.format_tier2_working_buffer(recent_logs)

        # 加载世界书法则
        tier3_lore = MemoryService.get_tier3_lorebook_and_ledger(
            db,
            character.id,
            delta.new_location,
            delta.plot_beat,
        )

        cues_text = "、".join(delta.sensory_cues) if delta.sensory_cues else "阴冷的光线、金属的铁锈味"

        # 解析文风与字数配置
        style_key = config.style_preset if config and config.style_preset else "free"
        word_tier_key = config.word_count_tier if config and config.word_count_tier else "standard"
        tier_info = WORD_COUNT_TIERS.get(word_tier_key, WORD_COUNT_TIERS["standard"])
        
        min_words = config.min_words if (config and config.min_words) else tier_info["min_words"]
        max_words = config.max_words if (config and config.max_words) else tier_info["max_words"]
        patches = config.enabled_patches if config else None
        guidance = config.custom_style_guidance if config else ""
        custom_base = config.pass2_custom_prompt if config else None

        # 检查是否激活手机与社交网络交互
        enable_phone = False
        if config and config.enable_phone_simulation is not None:
            enable_phone = config.enable_phone_simulation
        else:
            from app.services.config_service import get_all_system_configs
            sys_cfg = get_all_system_configs(db)
            enable_phone = sys_cfg.get("enable_phone_simulation", "false").lower() == "true"

        # 动态构建严密的系统提示词
        system_prompt = build_storyteller_system_prompt(
            style_key=style_key,
            word_tier_key=word_tier_key,
            min_words=min_words,
            max_words=max_words,
            enabled_patch_keys=patches,
            custom_guidance=guidance,
            custom_base_prompt=custom_base,
            enable_phone_simulation=enable_phone,
        )

        goals_text = MemoryService.format_active_goals_block(state)
        relationships_text = MemoryService.format_relationships_block(db, character.id)
        try:
            import json
            curr_inv = json.loads(state.inventory_json) if state.inventory_json else []
            inv_str = "、".join(curr_inv) if curr_inv else "空"
        except Exception:
            inv_str = "空"

        user_prompt = (
            f"主角姓名: {character.name}\n"
            f"职业称号: {character.title or '游荡者'}\n"
            f"核心执念 (Inner Drive): {character.inner_drive}\n"
            f"随身背包物品: {inv_str}\n\n"
            f"{goals_text}\n\n"
            f"{relationships_text}\n\n"
            f"{working_buffer_text}\n\n"
            f"{tier3_lore}\n\n"
            f"=== [本轮 Pass 1 客观裁决结果] ===\n"
            f"时间与地点: {delta.new_virtual_time} | {delta.new_location}\n"
            f"生理与休眠判定: {'已进入睡眠状态' if delta.rest_decision.is_sleeping else '清醒活动中'} "
            f"({delta.rest_decision.rest_reason})\n"
            f"客观事实骨架 (Plot Beat): {delta.plot_beat}\n"
            f"感官线索 (Sensory Cues): {cues_text}\n"
            f"心理与神色: {delta.psychological_change}\n\n"
            f"【叙事核心法则】: 必须紧扣主角的【当前推进目标】与【人际关系网（尤其是现场角色）】展开具有戏剧推进力的小说正文！若有在场 NPC，重点描写其言语交锋或互动；\n"
            f"请严格依据设定的文风与规范，生成 {min_words} 至 {max_words} 字的纯净小说正文："
        )

        try:
            prose = await llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                json_mode=False,
                on_chunk=on_chunk,
            )
            cleaned_prose = strip_emojis(prose.strip())
            if not cleaned_prose:
                raise StorytellerError("Pass 2 叙事正文生成为空", error_code="PASS2_EMPTY")
            return cleaned_prose
        except Exception as e:
            logger.error(f"[Pass 2 叙事失败·终端报错] 正文生成异常: {e}", exc_info=True)
            if isinstance(e, StorytellerError):
                raise
            raise StorytellerError(
                message=f"Pass 2 文学正文生成失败: {str(e)}",
                error_code="PASS2_FAILED",
                raw_error=str(e),
            )
