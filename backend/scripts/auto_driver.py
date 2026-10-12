import os
import sys
import json
import re
import time
import asyncio
import logging
import argparse
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

# 确保 backend 根目录在 Python 模块搜索路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.dirname(current_dir)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.database import SessionLocal, init_db
from app.models import Character, CharacterState, StoryLog, CharacterRelationship
from app.services.simulation import SimulationService
from app.schemas import StepTickResponse
from app.services.config_service import sync_config_to_runtime
from app.services.llm_client import llm_client

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("auto_driver")


def parse_hour_from_time_str(time_str: str) -> Optional[int]:
    """从虚拟时间字符串中提取小时数 (0-23)"""
    if not time_str:
        return None
    match = re.search(r"(\d{1,2}):(\d{2})", time_str)
    if match:
        return int(match.group(1))
    return None


def select_character(db, name_query: Optional[str] = None, char_id: Optional[str] = None) -> Optional[Character]:
    """
    根据名字搜索或交互式选择角色。如果有同名/多个匹配角色，列出简要信息供用户判断。
    严格无 Emoji
    """
    if char_id:
        char = db.query(Character).filter(Character.id == char_id).first()
        if char:
            return char
        logger.warning(f"未找到 ID 为 [{char_id}] 的角色，转为名称检索。")

    if name_query and name_query.strip():
        name_clean = name_query.strip()
        candidates = db.query(Character).filter(Character.name.ilike(f"%{name_clean}%")).all()
    else:
        candidates = db.query(Character).all()

    if not candidates:
        logger.error(f"[错误] 数据库中未找到名称匹配 [{name_query or '全部'}] 的角色。")
        return None

    if len(candidates) == 1:
        chosen = candidates[0]
        logger.info(f"[角色确认] 选定唯一匹配角色: {chosen.name} ({chosen.title or '旅者'}) | ID: {chosen.id}")
        return chosen

    # 多个候选角色，输出简要信息供用户选择
    print("\n" + "=" * 65)
    print(f"检测到 {len(candidates)} 个候选角色，请输入对应序号选择：")
    for idx, c in enumerate(candidates, 1):
        state = db.query(CharacterState).filter(CharacterState.character_id == c.id).first()
        ticks = state.total_ticks if state else 0
        vtime = state.virtual_time if state else "未初始化"
        loc = state.location if state else "未知"
        persona = (c.persona_summary or "").replace("\n", " ").strip()
        if len(persona) > 45:
            persona = persona[:45] + "..."
        created_str = c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "未知"

        print(f"[{idx}] {c.name} ({c.title or '无头衔'}) | ID: {c.id}")
        print(f"    进度: Tick #{ticks} | 当前时间: {vtime} | 地点: {loc}")
        print(f"    执念: {c.inner_drive}")
        print(f"    人设: {persona} (创建于: {created_str})")
        print("-" * 65)
    print("=" * 65)

    while True:
        try:
            choice = input(f"请输入角色序号 (1-{len(candidates)}): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(candidates):
                selected = candidates[int(choice) - 1]
                logger.info(f"[角色选定] 已选定角色: {selected.name} (ID: {selected.id})")
                return selected
            print(f"输入无效，请输入 1 到 {len(candidates)} 之间的数字。")
        except (KeyboardInterrupt, EOFError):
            print("\n已取消角色选择。")
            return None


class AutoDriverPolicy:
    """
    基于现实生活节律与戏剧张力的拟真调度决策器
    严禁包含 Emoji
    """
    def __init__(self):
        self.consecutive_stagnant_ticks = 0
        self.ticks_since_last_incident = 0
        self.ticks_since_last_rest = 0
        self.last_location = ""
        self.last_goals_count = 0

    def decide(self, character: Character, state: CharacterState) -> Tuple[str, Dict[str, Any], str]:
        """
        根据角色当前生理看板与历史跨度决定下一步按钮动作
        返回: (action_type, action_params, decision_reason)
        """
        import random

        curr_hour = parse_hour_from_time_str(state.virtual_time)
        circadian = {}
        try:
            if character.circadian_profile_json:
                circadian = json.loads(character.circadian_profile_json)
        except Exception:
            pass

        rest_window = circadian.get("typical_rest_window", "")
        start_sleep_h = 23
        wake_h = 7
        if rest_window and "-" in rest_window:
            try:
                parts = rest_window.split("-")
                start_sleep_h = int(re.search(r"\d+", parts[0]).group())
                wake_h = int(re.search(r"\d+", parts[1]).group())
            except Exception:
                pass

        # 判断是否处于夜间入睡窗口
        is_in_sleep_window = False
        if curr_hour is not None:
            if start_sleep_h > wake_h:
                is_in_sleep_window = (curr_hour >= start_sleep_h or curr_hour < wake_h)
            else:
                is_in_sleep_window = (start_sleep_h <= curr_hour < wake_h)

        # 1. 深度休眠中 / 夜间入睡判定
        if state.is_sleeping:
            self.ticks_since_last_rest = 0
            return "fast_forward_6h", {"step_type": "hour_6"}, "角色正处于休眠状态，执行深度睡眠与跨夜快进（自适应晨光破晓 06:30~07:30 自然苏醒）"

        # 夜间进入休眠窗口：只要处于入睡窗口且活动充实（>=3刻），无论精力剩多少均自然就寝
        if is_in_sleep_window and (self.ticks_since_last_rest >= 3 or (curr_hour is not None and (curr_hour >= start_sleep_h or curr_hour < 6))):
            self.ticks_since_last_rest = 0
            return "fast_forward_6h", {"step_type": "hour_6"}, f"虚拟时间处于夜间就寝时段 ({state.virtual_time})，遵循生物钟自然洗漱就寝至次日晨光"

        # 2. 白天精力偏低时的生理休整策略（严禁白昼睡大觉）
        is_daytime = curr_hour is not None and (6 <= curr_hour < start_sleep_h)
        if state.stamina <= 20 and is_daytime:
            self.ticks_since_last_rest = 0
            # 白天疲劳时，优先通过智能续写或短微步进，让角色就餐、喝茶、静坐歇脚以恢复精力
            if random.random() < 0.7:
                return "continue", {}, f"日间常态活动疲乏 (当前精力 {state.stamina}/100)，执行智能续写由角色在当前情境中进餐、小憩或放缓节奏自然回血"
            else:
                return "step", {"hours": 0.5}, f"日间短暂停顿修整 (当前精力 {state.stamina}/100)，执行 30 分钟微步进小憩与饮食补给"

        # 3. 检查情节平淡度与戏剧张力
        if state.location == self.last_location:
            self.consecutive_stagnant_ticks += 1
        else:
            self.consecutive_stagnant_ticks = 0
            self.last_location = state.location

        self.ticks_since_last_incident += 1
        self.ticks_since_last_rest += 1

        if self.ticks_since_last_incident >= 10 and (self.consecutive_stagnant_ticks >= 6 or self.ticks_since_last_incident >= 16):
            # 确保不在即将就寝的深夜生硬天降陨石破坏作息
            if not is_in_sleep_window:
                self.ticks_since_last_incident = 0
                self.consecutive_stagnant_ticks = 0
                return "trigger_incident", {}, "情节连续平淡或地点停滞过久，触发突发事件打破死水（由 AI 自主衍生变数）"

        # 4. 常规日常行动推进（弹性微步进与自由续写）
        if random.random() < 0.75:
            return "continue", {}, "日常行动推进，执行智能续写（由大模型自主裁决 30~90 分钟弹性时间尺度与行动闭环）"
        else:
            # 弹性微步进：30分钟、45分钟、60分钟或90分钟
            step_choice = random.choice([0.5, 0.75, 1.0, 1.5])
            mins = int(step_choice * 60)
            return "step", {"hours": step_choice}, f"精细环境探索与互动，执行 +{step_choice}h ({mins}分钟) 弹性微步进推演"


async def execute_action_with_retry(
    db,
    character_id: str,
    action_type: str,
    action_params: Dict[str, Any],
    config: Optional[Any] = None,
    max_retries: int = 3,
) -> StepTickResponse:
    """带指数退避重试的执行器"""
    for attempt in range(1, max_retries + 1):
        try:
            if action_type == "continue":
                return await SimulationService.run_continue(db, character_id, config=config)
            elif action_type == "step":
                return await SimulationService.run_step(db, character_id, hours=action_params.get("hours", 1), config=config)
            elif action_type == "fast_forward_6h":
                return await SimulationService.fast_forward(db, character_id, step_type="hour_6", config=config)
            elif action_type == "fast_forward_24h":
                return await SimulationService.fast_forward(db, character_id, step_type="day_1", config=config)
            elif action_type == "trigger_incident":
                return await SimulationService.trigger_inciting_incident(db, character_id, config=config)
            else:
                raise ValueError(f"未知动作类型: {action_type}")
        except Exception as e:
            logger.warning(f"[重试机制] 第 {attempt}/{max_retries} 次执行动作 [{action_type}] 失败: {e}")
            if attempt == max_retries:
                raise
            await asyncio.sleep(2 ** attempt)


def find_best_existing_journal(logs_dir: str, char_name: str, char_id: str) -> Optional[str]:
    """在 logs 目录下寻找同一角色的历史详实纪实文档（无论带有多少 ticks 后缀）"""
    if not os.path.exists(logs_dir):
        return None
    candidates = []
    for f in os.listdir(logs_dir):
        if not f.endswith(".txt"):
            continue
        # 匹配包含该角色名字或ID的文件
        if char_name in f or char_id[:8] in f:
            full_path = os.path.join(logs_dir, f)
            try:
                size = os.path.getsize(full_path)
                if size > 100:  # 排除仅有标头的空文件
                    candidates.append((size, full_path))
            except Exception:
                pass
    if candidates:
        # 按文件大小降序排序，选取信息量最大的作为基底
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    return None


def init_journal_file(db, filepath: str, character: Character, state: CharacterState, target_ticks: int):
    """
    初始化持久化记录文档：
    1. 若目标文件已存在，直接追加新批次标记，绝不覆盖已有记录；
    2. 若目标文件不存在，优先自动寻找并继承历史文件（如带 _20ticks 等旧文件）的全部丰富信息（含耗时、归因、生理、背包）；
    3. 若无历史文件，从数据库回填全量历史并解析 delta 详细还原生理与行囊。
    """
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

    # 1. 如果目标文件已存在，直接无缝追加
    if os.path.exists(filepath):
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"\n--- [接续推进批次: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 目标推进至 Tick #{target_ticks}] ---\n\n")
        return

    logs_dir = os.path.dirname(os.path.abspath(filepath))

    # 2. 检查是否有历史旧命名的纪实文件可供无损继承
    best_legacy = find_best_existing_journal(logs_dir, character.name, character.id)
    if best_legacy and os.path.abspath(best_legacy) != os.path.abspath(filepath):
        logger.info(f"[无损继承] 自动继承历史纪实文档完整信息: {os.path.basename(best_legacy)}")
        try:
            with open(best_legacy, "r", encoding="utf-8") as rf:
                legacy_content = rf.read()
            with open(filepath, "w", encoding="utf-8") as wf:
                wf.write(legacy_content)
                wf.write(f"\n--- [接续推进批次: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 目标推进至 Tick #{target_ticks}] ---\n\n")
            return
        except Exception as e:
            logger.warning(f"读取历史纪实文件失败: {e}，转为数据库全量还原")

    # 3. 若无历史文件，从数据库回填全量历史（解析 delta 详细还原各项元数据）
    header = f"""================================================================================
WorldSim 虚拟世界长程推演纪实报告 (面向评审/HR完整记录)
================================================================================
角色姓名: {character.name} ({character.title or '无头衔'}) | 角色ID: {character.id}
核心执念: {character.inner_drive}
人设概要: {character.persona_summary}
起始进度: Tick #{state.total_ticks} | 目标推进刻数: Tick #{target_ticks}
初始时空: {state.virtual_time} | 初始据点: {state.location}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header)
        
    history_logs = (
        db.query(StoryLog)
        .filter(StoryLog.character_id == character.id)
        .order_by(StoryLog.tick_index.asc())
        .all()
    )
    if history_logs:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"--- [历史推演回溯归档: 共 {len(history_logs)} 刻] ---\n\n")
            for hl in history_logs:
                delta = {}
                try:
                    delta = json.loads(hl.delta_snapshot_json) if hl.delta_snapshot_json else {}
                except Exception:
                    pass
                inv_added = delta.get("inventory_delta", {}).get("added", [])
                inv_removed = delta.get("inventory_delta", {}).get("removed", [])
                goals = delta.get("goal_delta", {}).get("current_active", [])
                rest_dec = delta.get("rest_decision", {})
                block = f"""--------------------------------------------------------------------------------
[Tick #{hl.tick_index:03d}] 虚拟时间: {hl.virtual_time} | 地点: {hl.location}
决策动作: 历史已存档推演
生理状态: 休眠={'是' if rest_dec.get('is_sleeping') else '否'} | 心理变化: {delta.get('psychological_change', '稳定')}
行囊变动: [+{', '.join(inv_added) if inv_added else '无'} | -{', '.join(inv_removed) if inv_removed else '无'}]
当前目标: {', '.join(goals) if goals else '进行中'}

【事实骨架 (Pass 1 Plot Beat)】:
{hl.plot_beat}

【场景小说正文 (Pass 2 Narrative Prose)】:
{hl.narrative_prose}

"""
                f.write(block)
            f.write(f"--- [后续推演实时推进追踪] ---\n\n")


def append_tick_to_journal(
    filepath: str,
    tick: int,
    action_type: str,
    reason: str,
    res: StepTickResponse,
    cost_time: float,
):
    """实时追加单刻推演切片到 txt 文档中，确保进程意外中止时不丢记录"""
    state = res.current_state
    log = res.story_log
    inv = state.inventory if isinstance(state.inventory, list) else []
    goals = state.active_goals if isinstance(state.active_goals, list) else []

    action_name_map = {
        "continue": "智能续写 (Continue)",
        "step": "微步进 (+1h)",
        "fast_forward_6h": "深度休眠跨夜快进 (+6h)",
        "fast_forward_24h": "阶段跃迁快进 (+24h)",
        "trigger_incident": "突发事件 (Trigger Incident)",
    }
    action_display = action_name_map.get(action_type, action_type)

    block = f"""--------------------------------------------------------------------------------
[Tick #{tick:03d}] 虚拟时间: {state.virtual_time} | 地点: {state.location}
决策动作: {action_display} (耗时: {cost_time:.1f}s)
决策归因: {reason}
生理看板: 健康 {state.health}/100 | 精力 {state.stamina}/100 | 休眠状态: {'是' if state.is_sleeping else '否'}
随身行囊: [{', '.join(inv) if inv else '空'}] ({len(inv)}/8件)
当前目标: {', '.join(goals) if goals else '探索中'}

【事实骨架 (Pass 1 Plot Beat)】:
{log.plot_beat}

【场景小说正文 (Pass 2 Narrative Prose)】:
{log.narrative_prose}

"""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(block)


async def run_auto_driver(
    name: Optional[str] = None,
    character_id: Optional[str] = None,
    target_ticks: int = 100,
    output_txt: Optional[str] = None,
    style_preset: Optional[str] = None,
    enable_phone: Optional[bool] = None,
):
    init_db()
    sync_config_to_runtime()

    if not llm_client.api_key or llm_client.api_key.startswith("sk-xxxx"):
        logger.error("[启动中断] 未检测到有效的 LLM_API_KEY！请在系统设置中配置有效 API Key！")
        return

    db = SessionLocal()
    try:
        from app.services.config_service import get_simulation_prompt_config
        prompt_config = get_simulation_prompt_config(db)
        if style_preset and style_preset.strip():
            prompt_config.style_preset = style_preset.strip()
        if enable_phone is not None:
            prompt_config.enable_phone_simulation = enable_phone

        char = select_character(db, name_query=name, char_id=character_id)
        if not char:
            return

        state = db.query(CharacterState).filter(CharacterState.character_id == char.id).first()
        if not state:
            logger.error(f"[错误] 未找到角色状态记录: {char.id}")
            return

        current_ticks = state.total_ticks

        # 确定持久化 TXT 文件路径：为每个角色使用统一命名的长程纪实文档，避免 target_ticks 改变导致分流
        if not output_txt:
            logs_dir = os.path.join(backend_root, "logs")
            same_name_chars = db.query(Character).filter(Character.name == char.name).count()
            if same_name_chars > 1:
                base_name = f"simulation_journal_{char.name}_{char.id[:8]}.txt"
            else:
                base_name = f"simulation_journal_{char.name}.txt"
            output_txt = os.path.join(logs_dir, base_name)

        init_journal_file(db, output_txt, char, state, target_ticks)

        logger.info(f"==================================================")
        logger.info(f"[世界推演自动化驱动器启动]")
        logger.info(f"LLM 运行引擎: 模型=[{llm_client.model_name}] | 接口=[{llm_client.base_url}]")
        logger.info(f"文学演义风格: [{prompt_config.style_preset}] | 字数档位: [{prompt_config.word_count_tier}] ({prompt_config.min_words}~{prompt_config.max_words}字)")
        logger.info(f"手机与社交拟真: [{'已激活' if prompt_config.enable_phone_simulation else '未开启'}]")
        logger.info(f"激活文学技法补丁 ({len(prompt_config.enabled_patches or [])}项): {prompt_config.enabled_patches}")
        if prompt_config.custom_style_guidance:
            logger.info(f"个性化文风指引: {prompt_config.custom_style_guidance}")
        logger.info(f"选定角色: {char.name} ({char.title or '旅者'}) | ID: {char.id}")
        logger.info(f"当前进度: Tick #{current_ticks} -> 目标刻数: Tick #{target_ticks}")
        logger.info(f"持久化记录文档: {output_txt}")
        logger.info(f"==================================================")

        if current_ticks >= target_ticks:
            logger.info(f"[提示] 当前角色已达到或超过目标刻数 ({current_ticks} >= {target_ticks})，无需推进。")
            print(f"\n[推演纪实已就绪] 可随时查阅持久化文档: {output_txt}")
            return

        policy = AutoDriverPolicy()
        policy.last_location = state.location

        while current_ticks < target_ticks:
            db.refresh(state)
            action_type, action_params, reason = policy.decide(char, state)

            next_tick_target = current_ticks + 1
            logger.info(f"--- [Tick 推进中: #{next_tick_target} / {target_ticks}] ---")
            logger.info(f"决策引擎动作: [{action_type}] | 决策归因: {reason}")

            start_t = time.time()
            try:
                res = await execute_action_with_retry(
                    db, char.id, action_type, action_params, config=prompt_config
                )
                cost_t = time.time() - start_t
                current_ticks = res.current_state.total_ticks
                story_beat = res.story_log.plot_beat
                prose_len = len(res.story_log.narrative_prose)

                # 实时同步持久化保存到 TXT
                append_tick_to_journal(output_txt, current_ticks, action_type, reason, res, cost_t)

                logger.info(
                    f"[Tick #{current_ticks} 成功] "
                    f"时空: {res.current_state.virtual_time} | 地点: {res.current_state.location} | "
                    f"精力: {res.current_state.stamina}/100 | 耗时: {cost_t:.1f}s | 正文字数: {prose_len}"
                )
                logger.info(f"剧情骨架: {story_beat[:80]}...")
            except Exception as e:
                logger.error(f"[推演异常中断] Tick #{next_tick_target} 推进失败: {e}", exc_info=True)
                break

        logger.info(f"==================================================")
        logger.info(f"[世界推演推进流程结束] 最终到达刻数: Tick #{current_ticks}")
        logger.info(f"纪实文本文件已完整保存至: {output_txt}")
        logger.info(f"==================================================")
        print(f"\n[推演完成/中断保存] 纪实文本已实时持久化至:\n{output_txt}\n")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="WorldSim 自动化世界推演驱动器 (严禁 Emoji)")
    parser.add_argument("--name", type=str, default=None, help="角色姓名 (支持模糊搜索，有同名会列出交互选择)")
    parser.add_argument("--character-id", type=str, default=None, help="目标角色 ID (兼容直接指定 ID)")
    parser.add_argument("--target-ticks", type=int, default=100, help="推进的目标刻数 (默认 100)")
    parser.add_argument("--output", type=str, default=None, help="持久化保存的 TXT 文档路径 (默认位于 backend/logs/)")
    parser.add_argument("--style", type=str, default=None, help="覆盖文学演义流派预设 (如: light_witty, dark_humor, bustling_hearth, free 等)")
    parser.add_argument("--enable-phone", dest="enable_phone", action="store_true", default=None, help="强制激活手机与社交网络拟真")
    parser.add_argument("--disable-phone", dest="enable_phone", action="store_false", default=None, help="强制关闭手机与社交网络拟真")
    args = parser.parse_args()

    asyncio.run(
        run_auto_driver(
            name=args.name,
            character_id=args.character_id,
            target_ticks=args.target_ticks,
            output_txt=args.output,
            style_preset=args.style,
            enable_phone=args.enable_phone,
        )
    )


if __name__ == "__main__":
    main()
