import asyncio
import json
import logging
import re
from typing import List, Dict, Any, Optional, Callable
import httpx
from app.config import settings

logger = logging.getLogger("world_sim.llm")

# 正则表达式剥离可能意外生成的 Emoji
EMOJI_REGEX = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E6-\U0001F1FF"  # flags
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended-a
    "\u2600-\u26FF"          # misc symbols
    "\u2700-\u27BF"          # dingbats
    "]+",
    flags=re.UNICODE,
)


def strip_emojis(text: str) -> str:
    """按规范严格过滤 Emoji 图标"""
    return EMOJI_REGEX.sub("", text)


class LLMClientError(Exception):
    def __init__(self, error_code: str, message: str, status_code: int = 500, raw_error: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.raw_error = raw_error


class LLMClient:
    def __init__(self):
        self.base_url = "https://api.openai.com/v1"
        self.api_key = ""
        self.model_name = "gpt-4o-mini"
        self.context_window = 60000
        self.temperature = 1.0
        self.frequency_penalty = 0.0
        self.presence_penalty = 0.0
        self.top_p = 1.0

    @staticmethod
    async def fetch_models(base_url: str, api_key: str) -> List[str]:
        """向兼容 OpenAI 规范的 /models 接口拉取可用模型列表"""
        clean_url = (base_url or "").rstrip("/")
        if not clean_url:
            raise ValueError("LLM Base URL 不能为空")

        headers = {
            "Content-Type": "application/json",
        }
        if api_key and not api_key.startswith("sk-xxxx"):
            headers["Authorization"] = f"Bearer {api_key.strip()}"

        models: List[str] = []
        async with httpx.AsyncClient(timeout=25.0) as client:
            try:
                # 优先尝试 clean_url/models
                res = await client.get(f"{clean_url}/models", headers=headers)
                if res.status_code == 404 and not clean_url.endswith("/v1"):
                    # 若未包含 /v1 且返回 404，尝试补充 /v1/models
                    res = await client.get(f"{clean_url}/v1/models", headers=headers)

                res.raise_for_status()
                data = res.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise ValueError("API Key 鉴权失败 (401 Unauthorized)，请检查 API Key 是否正确或具有权限")
                elif e.response.status_code == 403:
                    raise ValueError("访问受限 (403 Forbidden)，请检查 API Key 额度或访问权限")
                elif e.response.status_code == 404:
                    raise ValueError("未找到模型列表接口 (404 Not Found)，请确认 Base URL 路径是否正确")
                else:
                    raise ValueError(f"拉取模型列表失败: HTTP {e.response.status_code}")
            except Exception as e:
                raise ValueError(f"连接模型接口异常: {str(e)}")

            raw_list = []
            if isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list):
                    raw_list = data["data"]
                elif "models" in data and isinstance(data["models"], list):
                    raw_list = data["models"]
            elif isinstance(data, list):
                raw_list = data

            for item in raw_list:
                if isinstance(item, dict):
                    mid = item.get("id") or item.get("name") or item.get("model")
                    if mid and isinstance(mid, str):
                        models.append(mid)
                elif isinstance(item, str):
                    models.append(item)

        # 过滤去重并排序
        seen = set()
        unique = []
        for m in models:
            if m not in seen:
                seen.add(m)
                unique.append(m)

        return sorted(unique)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = True,
        on_chunk: Optional[Callable[[str], Any]] = None,
    ) -> str:
        """调用兼容 OpenAI 规范的 Chat Completion 接口"""
        if not self.api_key or self.api_key.startswith("sk-xxxx"):
            logger.warning("[LLM] 未配置有效 LLM_API_KEY，切换至本地规则兜底")
            return self._fallback_completion(messages, json_mode)

        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream, application/json",
            "User-Agent": "WorldSim-Engine/1.0",
        }
        eff_temp = temperature if temperature is not None else self.temperature
        eff_top_p = top_p if top_p is not None else self.top_p
        eff_freq = frequency_penalty if frequency_penalty is not None else self.frequency_penalty
        eff_pres = presence_penalty if presence_penalty is not None else self.presence_penalty

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": eff_temp,
            "top_p": eff_top_p,
            "frequency_penalty": eff_freq,
            "presence_penalty": eff_pres,
            "stream": stream,
        }
        # 不写死 max_tokens：仅当明确指定时才传入
        if max_tokens is not None and max_tokens > 0:
            payload["max_tokens"] = max_tokens
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        timeout_config = httpx.Timeout(timeout=300.0, connect=60.0, read=300.0, write=120.0, pool=60.0)
        limits_config = httpx.Limits(max_keepalive_connections=5, max_connections=10, keepalive_expiry=60.0)

        max_retries = 3
        for attempt in range(max_retries):
            has_received_data = False
            content_parts: List[str] = []
            try:
                async with httpx.AsyncClient(timeout=timeout_config, limits=limits_config) as client:
                    # 模式 A: 非流式单次标准请求 (如 Pass 1 理性因果裁决)
                    if not stream:
                        res = await client.post(
                            f"{self.base_url}/chat/completions",
                            headers=headers,
                            json=payload,
                        )
                        if res.status_code != 200:
                            err_body = res.text
                            logger.error(
                                f"[LLM 终端报错] 接口返回 HTTP {res.status_code}，模型: {self.model_name}，响应正文: {err_body}"
                            )
                            if res.status_code in (401, 403):
                                raise LLMClientError("AUTH_FAILED", "API Key 鉴权失败或无权限", status_code=res.status_code, raw_error=err_body)
                            elif res.status_code == 429:
                                raise LLMClientError("RATE_LIMIT_OR_QUOTA", "API 额度耗尽或请求频次超限", status_code=res.status_code, raw_error=err_body)
                            elif res.status_code == 404:
                                raise LLMClientError("MODEL_NOT_FOUND", "未找到指定模型或 Base URL 路径错误", status_code=res.status_code, raw_error=err_body)
                            else:
                                raise LLMClientError("API_CALL_FAILED", f"API 调用异常 (HTTP {res.status_code})", status_code=res.status_code, raw_error=err_body)

                        data = res.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        if not content or not content.strip():
                            raise LLMClientError("EMPTY_RESPONSE", "模型返回内容为空", status_code=502)
                        return strip_emojis(content.strip())

                    # 模式 B: SSE 实时流式传输 (如 Pass 2 文学正文流式打字输出)
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as res:
                        if res.status_code != 200:
                            err_bytes = await res.aread()
                            err_body = err_bytes.decode("utf-8", errors="ignore")
                            logger.error(
                                f"[LLM 终端报错] 接口返回 HTTP {res.status_code}，模型: {self.model_name}，响应正文: {err_body}"
                            )
                            if res.status_code in (401, 403):
                                raise LLMClientError("AUTH_FAILED", "API Key 鉴权失败或无权限", status_code=res.status_code, raw_error=err_body)
                            elif res.status_code == 429:
                                raise LLMClientError("RATE_LIMIT_OR_QUOTA", "API 额度耗尽或请求频次超限", status_code=res.status_code, raw_error=err_body)
                            elif res.status_code == 404:
                                raise LLMClientError("MODEL_NOT_FOUND", "未找到指定模型或 Base URL 路径错误", status_code=res.status_code, raw_error=err_body)
                            else:
                                raise LLMClientError("API_CALL_FAILED", f"API 调用异常 (HTTP {res.status_code})", status_code=res.status_code, raw_error=err_body)

                        content_type = res.headers.get("content-type", "").lower()
                        # 若服务商返回标准 application/json（非 SSE 流式），直接读取完整正文解析
                        if "application/json" in content_type and "event-stream" not in content_type:
                            raw_bytes = await res.aread()
                            data = json.loads(raw_bytes.decode("utf-8", errors="ignore"))
                            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                            if not content or not content.strip():
                                raise LLMClientError("EMPTY_RESPONSE", "模型返回内容为空", status_code=502)
                            return strip_emojis(content.strip())

                        # 流式聚合解析（SSE）
                        try:
                            async for raw_line in res.aiter_lines():
                                line = raw_line.strip()
                                if not line:
                                    continue
                                if line.startswith("data:"):
                                    data_str = line[5:].strip()
                                    if data_str == "[DONE]":
                                        break
                                    try:
                                        chunk = json.loads(data_str)
                                        choices = chunk.get("choices", [])
                                        if choices:
                                            delta = choices[0].get("delta", {})
                                            c = delta.get("content")
                                            if c is None:
                                                c = choices[0].get("message", {}).get("content")
                                            if c:
                                                content_parts.append(c)
                                                has_received_data = True
                                                if on_chunk:
                                                    try:
                                                        cb_res = on_chunk(c)
                                                        if asyncio.iscoroutine(cb_res):
                                                            await cb_res
                                                    except Exception as cb_err:
                                                        logger.warning(f"[LLM 流式回调异常] {cb_err}")
                                    except Exception:
                                        continue
                        except (httpx.RemoteProtocolError, httpx.ReadError) as stream_err:
                            logger.warning(f"[LLM 流式读取中途断开: {stream_err}] 已尝试保留已收到内容 ({len(content_parts)} 段)")

                        full_content = "".join(content_parts).strip()
                        if not full_content:
                            logger.error(f"[LLM 终端报错] 模型流式返回内容为空")
                            raise LLMClientError("EMPTY_RESPONSE", "模型返回内容为空", status_code=502)

                        return strip_emojis(full_content)

            except (httpx.ConnectTimeout, httpx.ConnectError) as e:
                # 仅在尚未建立 TCP 连接或未传输任何数据时重试（0 消耗）
                if not has_received_data and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 1.5
                    logger.warning(f"[LLM 客户端] 建立网络连接等待超时/失败 ({type(e).__name__}: {e})，正在自动重试 ({attempt + 1}/{max_retries})，等待 {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"[LLM 终端报错] 建立网络连接失败: {e}")
                raise LLMClientError("NETWORK_ERROR", f"网络连接建立失败: {str(e)}", status_code=502, raw_error=str(e))
            except httpx.RemoteProtocolError as e:
                # 若已收到足够有效文本，即使最后关闭时有 TCP 协议断开也直接采纳结果
                if content_parts:
                    full_content = "".join(content_parts).strip()
                    if full_content:
                        logger.info(f"[LLM 客户端] 捕捉到末端协议断开，但已成功聚合完整正文 ({len(full_content)} 字)，采纳生成结果")
                        return strip_emojis(full_content)

                # 若在尚未收到任何数据时服务端掐断连接（如代理服务重置空闲连接），安全重试 1 次
                if not has_received_data and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 1.5
                    logger.warning(f"[LLM 客户端] 握手期间服务端连接断开 ({e})，正在自动重试 ({attempt + 1}/{max_retries})，等待 {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                logger.error(f"[LLM 终端报错] 服务端在响应期间断开连接 (RemoteProtocolError: {e})。")
                raise LLMClientError(
                    "NETWORK_DISCONNECTED",
                    f"服务端在响应期间断开连接 ({str(e)})。已开启流式传输维持连接，请检查代理中转商服务稳定性。",
                    status_code=502,
                    raw_error=str(e),
                )
            except httpx.ReadTimeout as e:
                logger.error(f"[LLM 终端报错] 模型生成读取超时 (超过 300s): {e}。为防止重复计费已停止重试。")
                raise LLMClientError("NETWORK_TIMEOUT", "模型生成耗时超过限制 (300s)，请检查接口服务状态或选择响应更快的模型", status_code=504, raw_error=str(e))
            except httpx.TimeoutException as e:
                logger.error(f"[LLM 终端报错] 网络请求超时: {e}")
                raise LLMClientError("NETWORK_TIMEOUT", f"网络请求超时: {str(e)}", status_code=504, raw_error=str(e))
            except httpx.RequestError as e:
                logger.error(f"[LLM 终端报错] 网络连接失败: {e}")
                raise LLMClientError("NETWORK_ERROR", f"网络连接错误: {str(e)}", status_code=502, raw_error=str(e))
            except LLMClientError:
                raise
            except Exception as e:
                logger.error(f"[LLM 终端报错] 未知异常: {type(e).__name__}: {e}", exc_info=True)
                raise LLMClientError("API_CALL_FAILED", f"接口处理异常: {str(e)}", status_code=500, raw_error=str(e))

    def _fallback_completion(self, messages: List[Dict[str, str]], json_mode: bool) -> str:
        """兜底逻辑：仅在未配置任何 API Key 时提供纯本地初始测试数据"""
        user_msg = messages[-1]["content"] if messages else ""
        system_msg = messages[0]["content"] if len(messages) > 1 else ""

        if json_mode:
            # 判断是否为 Pass 1 裁决请求
            if "Pass 1" in system_msg or "Arbitrator" in system_msg or "裁决" in system_msg:
                return json.dumps({
                    "simulated_hours_passed": 1,
                    "new_virtual_time": "晨光月 1日 09:00",
                    "new_location": "旧工坊残破的长桌前",
                    "rest_decision": {
                        "is_sleeping": False,
                        "sleep_quality": "none",
                        "rest_reason": "精力充沛，维持清醒并继续检视手中的零件"
                    },
                    "health_delta": 0,
                    "stamina_delta": -8,
                    "psychological_change": "由最初的警惕转为专注于眼前的构造",
                    "inventory_delta": {
                        "added": ["带编号的黄铜弹壳"],
                        "removed": ["火柴一根"]
                    },
                    "goal_delta": {
                        "completed": [],
                        "added": ["清理桌案散落的碎屑"],
                        "current_active": ["检修开裂的动力核心", "寻找避开巡逻队的撤离路线"]
                    },
                    "plot_beat": "角色在长桌前清理了散落的机械图纸，拾起一枚残留火药气味的黄铜弹壳，随后将工具收拢至布袋中防备外部动静",
                    "sensory_cues": [
                        "金属机油挥发出的微涩气味",
                        "窗格外初晨冷灰色的微光",
                        "远方蒸汽管道定期的沉重泄压声"
                    ]
                }, ensure_ascii=False)

            # 判断是否为作息画像或角色卡分析请求
            if "Circadian Profile" in system_msg or "作息画像" in system_msg or "快速生成" in system_msg:
                return json.dumps({
                    "name": "格温·艾尔斯",
                    "title": "黑市钟表匠",
                    "persona_summary": "沉默、严谨、对金属机械结构拥有近乎苛刻的直觉，极度缺乏安全感但行事果决。",
                    "inner_drive": "查明旧工坊坍塌事故的真相，偿清导师遗留的违约黑金，寻回失落的动力总成核心。",
                    "circadian_profile": {
                        "chronotype": "夜行型",
                        "typical_rest_window": "05:00 - 12:00",
                        "environment_tolerance": "必须在门锁完备的隐蔽据点或地下工坊浅睡",
                        "sleep_trigger_summary": "常年习惯熬夜工作，仅在黎明前后且精力耗尽时方肯歇息"
                    },
                    "initial_health": 100,
                    "initial_stamina": 85,
                    "initial_inventory": ["黄铜多功能螺丝刀", "怀表机芯残件", "火柴半盒", "陈旧皮革手套"],
                    "initial_goals": ["排查防盗门闩与警报发条", "重新组装受损的差速轮组"],
                    "initial_location": "旧铁道桥下的避雨涵洞",
                    "initial_virtual_time": "晨光月 1日 08:00"
                }, ensure_ascii=False)

            return "{}"

        # Pass 2 文学正文兜底
        return (
            "雨水敲打在生锈的铁皮檐口，细碎的雨声将狭窄工坊内的死寂切得更碎。格温将最后一枚带齿纹的黄铜滚珠"
            "推进滑槽，指节上覆着一层洗不脱的暗色润滑油污。窗格外漫进微凉的湿气，远处高架管道定期喷吐的白汽"
            "在铅灰色的晨光里翻卷。她并未抬头，只是凭借掌心的触感反复摩挲着那枚残留焦痕的弹壳，指尖传来金属特有的"
            "冷硬触感。门外的石子路上传来轻微且滞涩的脚步声，水洼被踩碎的声响让她呼吸微微一顿，握住扳手的手指随即收紧。"
        )


llm_client = LLMClient()
