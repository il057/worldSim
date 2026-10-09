import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import Character, CharacterState
from app.schemas import ArbitratorDelta, RestDecision, InventoryDelta, GoalDelta, SimulationPromptConfig
from app.services.llm_client import llm_client
from app.services.memory import MemoryService
from app.services.prompt_library import build_arbitrator_system_prompt

logger = logging.getLogger("world_sim.arbitrator")


def extract_and_parse_json(raw: str) -> Dict[str, Any]:
    """清洗并提取文本中的 JSON 对象，自动兼容 Markdown 语法与多余前后缀"""
    clean = raw.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
        clean = clean.strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\})", clean, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


class ArbitrationError(Exception):
    def __init__(self, message: str, error_code: str = "PASS1_FAILED", raw_response: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.raw_response = raw_response


class ArbitratorService:
    @staticmethod
    def advance_virtual_time_str(curr_time_str: str, hours: int) -> str:
        """
        严密解析并推进虚拟时间，支持任意年/月/日/时/分格式，
        自动处理跨日进位，并彻底剔除任何类似 (+5h) 的冗余垃圾后缀。
        """
        if not curr_time_str:
            return "2024年10月9日 08:00"

        # 1. 彻底清理所有历史残留的 (+Xh) 或 (+X小时) 等任何累加后缀
        clean_str = re.sub(r"\s*\(\+\d+[hH小时]+\)", "", curr_time_str).strip()

        # 2. 尝试标准年月日时分匹配: 如 2024年10月9日 23:45 或 2024-10-09 23:45
        date_match = re.search(r"(\d{4})[年\-](\d{1,2})[月\-](\d{1,2})[日\s]+(?:[^\d]*?)(\d{1,2}):(\d{2})", clean_str)
        if date_match:
            y, m, d, hh, mm = map(int, date_match.groups())
            try:
                dt = datetime(y, m, d, hh, mm) + timedelta(hours=hours)
                return dt.strftime("%Y年%m月%d日 %H:%M")
            except Exception:
                pass

        # 3. 尝试通用时分匹配与跨日处理: 如 23:45, 08:00
        time_match = re.search(r"(\d{1,2}):(\d{2})", clean_str)
        if time_match:
            h = int(time_match.group(1))
            m = int(time_match.group(2))
            total_h = h + hours
            new_h = total_h % 24
            days_passed = total_h // 24
            new_time_part = f"{new_h:02d}:{m:02d}"

            # 检查是否有具体日期日号: 如 "9日", "14日"
            day_match = re.search(r"(\d{1,2})日", clean_str)
            if day_match and days_passed > 0:
                curr_day = int(day_match.group(1))
                new_day = curr_day + days_passed
                res = re.sub(r"\d{1,2}日", f"{new_day}日", clean_str)
                res = re.sub(r"\d{1,2}:\d{2}", new_time_part, res)
                return res
            elif days_passed > 0:
                res = re.sub(r"\d{1,2}:\d{2}", new_time_part, clean_str)
                if "翌日" not in res and days_passed == 1:
                    res = re.sub(r"(\d{1,2}:\d{2})", r"翌日 \1", res)
                return res
            else:
                return re.sub(r"\d{1,2}:\d{2}", new_time_part, clean_str)

        return clean_str

    @classmethod
    async def decide_tick(
        cls,
        db: Session,
        character: Character,
        state: CharacterState,
        hours_passed: int,
        forced_incident_prompt: Optional[str] = None,
        config: Optional[SimulationPromptConfig] = None,
    ) -> ArbitratorDelta:
        """
        Pass 1: 纯理性逻辑裁决机 (Arbitrator Engine)
        结合生理精力、作息画像与世界法则，输出严格合法的结构化 State Delta
        """
        # 构建三层输入
        tier1_text = MemoryService.format_tier1_living_state(character, state)
        recent_logs = MemoryService.get_tier2_working_buffer(db, character.id, limit=5)
        tier2_text = MemoryService.format_tier2_working_buffer(recent_logs)
        tier3_text = MemoryService.get_tier3_lorebook_and_ledger(
            db,
            character.id,
            state.location,
            " ".join([l.plot_beat for l in recent_logs]),
        )

        incident_injection = ""
        if forced_incident_prompt:
            incident_injection = (
                f"\n【突发事件强力驱动】: 本轮用户触发了突发事件观察信号！"
                f"由世界引擎自主构思并强行注入的核心危机/奇遇为:\n{forced_incident_prompt}\n"
                f"你必须在本次裁决中以此突发事件为最高主导因，迫使角色产生针对性的生理、目标或位置变动！\n"
            )

        pass1_custom = config.pass1_custom_prompt if config else None
        system_prompt = build_arbitrator_system_prompt(pass1_custom)
        expected_time = cls.advance_virtual_time_str(state.virtual_time, hours_passed)
        goals_text = MemoryService.format_active_goals_block(state)
        relationships_text = MemoryService.format_relationships_block(db, character.id)

        user_prompt = (
            f"{tier1_text}\n\n"
            f"{goals_text}\n\n"
            f"{relationships_text}\n\n"
            f"{tier2_text}\n\n"
            f"{tier3_text}\n\n"
            f"本次推进流逝跨度: {hours_passed} 小时\n"
            f"建议基准推移时间: {expected_time}\n"
            f"{incident_injection}\n"
            f"请结合当前推进目标与人际关系网（在场角色），执行因果逻辑裁决并输出结构化 JSON："
        )

        raw = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            json_mode=True,
            temperature=0.3,
            stream=False,
        )

        try:
            data = extract_and_parse_json(raw)
            # 解析为结构化模型
            rest_data = data.get("rest_decision", {})
            inv_data = data.get("inventory_delta", {})
            goal_data = data.get("goal_delta", {})

            return ArbitratorDelta(
                simulated_hours_passed=data.get("simulated_hours_passed", hours_passed),
                new_virtual_time=data.get("new_virtual_time", expected_time),
                new_location=data.get("new_location", state.location),
                rest_decision=RestDecision(
                    is_sleeping=bool(rest_data.get("is_sleeping", False)),
                    sleep_quality=rest_data.get("sleep_quality", "none"),
                    rest_reason=rest_data.get("rest_reason", "维持现状"),
                ),
                health_delta=int(data.get("health_delta", 0)),
                stamina_delta=int(data.get("stamina_delta", -8 * hours_passed if not rest_data.get("is_sleeping") else 25)),
                psychological_change=data.get("psychological_change", "警惕且专注"),
                inventory_delta=InventoryDelta(
                    added=inv_data.get("added", []),
                    removed=inv_data.get("removed", []),
                ),
                goal_delta=GoalDelta(
                    completed=goal_data.get("completed", []),
                    added=goal_data.get("added", []),
                    current_active=goal_data.get("current_active", json.loads(state.active_goals_json) if state.active_goals_json else []),
                ),
                plot_beat=data.get("plot_beat", f"角色在 {state.location} 度过了 {hours_passed} 小时并审视周围环境。"),
                sensory_cues=data.get("sensory_cues", ["冷硬的空气", "生锈铁器的气味", "远处的风声"]),
            )
        except Exception as e:
            logger.error(
                f"[Pass 1 裁决失败·终端报错] JSON 解析失败: {e}\n模型原始响应内容:\n{raw}",
                exc_info=True,
            )
            raise ArbitrationError(
                message=f"Pass 1 裁决数据解析失败: {str(e)}",
                error_code="PASS1_FAILED",
                raw_response=raw,
            )
