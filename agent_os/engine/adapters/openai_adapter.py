"""
Agent OS v7.0 — OpenAI-compatible Model Adapter
=================================================
支持 OpenAI、DeepSeek、以及任何 OpenAI-compatible API。

用法：
    adapter = OpenAIAdapter(api_key="sk-...", model="deepseek-chat")
    response = await adapter.call(messages, tools, system="...")
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import requests

from ..core_loop import Message, MessageRole, ModelAdapter, ModelResponse, StopReason

logger = logging.getLogger("agent-os.engine.adapters.openai")


class OpenAIAdapter(ModelAdapter):
    """
    OpenAI-compatible 模型适配器

    支持：
    - OpenAI (GPT-4o, GPT-4o-mini, o3, o4-mini)
    - DeepSeek (deepseek-chat, deepseek-reasoner)
    - 任何 OpenAI-compatible API
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 60.0,
        default_max_tokens: int = 4096,
        default_temperature: float = 0.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.default_max_tokens = default_max_tokens
        self.default_temperature = default_temperature
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    async def _convert_messages(
        self,
        messages: List[Message],
        system: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """将内部 Message 列表转换为 OpenAI API 格式"""
        result: List[Dict[str, Any]] = []

        # 系统提示作为独立消息（OpenAI 格式）
        if system:
            result.append({"role": "system", "content": system})

        for msg in messages:
            d: Dict[str, Any] = {"role": msg.role.value, "content": msg.content}
            if msg.tool_calls:
                d["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                d["tool_call_id"] = msg.tool_call_id
            if msg.name:
                d["name"] = msg.name
            result.append(d)

        return result

    def _convert_response(self, raw: Dict[str, Any]) -> ModelResponse:
        """将 OpenAI API 响应转换为内部 ModelResponse"""
        choice = raw["choices"][0]
        message = choice.get("message", {})
        finish_reason = choice.get("finish_reason", "stop")

        # 映射 stop_reason
        stop_reason_map = {
            "stop": StopReason.END_TURN,
            "tool_calls": StopReason.TOOL_USE,
            "length": StopReason.MAX_TOKENS,
            "content_filter": StopReason.STOP_SEQUENCE,
        }
        stop_reason = stop_reason_map.get(finish_reason, StopReason.END_TURN)

        # 提取 tool_calls
        tool_calls = []
        for tc in message.get("tool_calls", []):
            tool_calls.append({
                "id": tc["id"],
                "type": tc["type"],
                "function": tc["function"],
            })

        # 提取 usage
        usage = raw.get("usage", {})
        model_name = raw.get("model", self.model)

        return ModelResponse(
            content=message.get("content", "") or "",
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage={
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            },
            model=model_name,
        )

    def _call_sync(
        self,
        api_messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]],
        system: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> ModelResponse:
        """同步 HTTP 调用（在 executor 中运行）"""
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        last_error = None
        for attempt in range(self.max_retries):
            try:
                start = time.time()
                resp = self._session.post(
                    f"{self.base_url}/chat/completions",
                    json=body,
                    timeout=self.timeout,
                )
                elapsed = time.time() - start

                if resp.status_code == 200:
                    data = resp.json()
                    logger.debug(
                        f"OpenAI call: model={self.model} "
                        f"status=200 elapsed={elapsed:.2f}s "
                        f"usage={data.get('usage', {})}"
                    )
                    return self._convert_response(data)

                error_body = resp.text[:500]
                logger.warning(
                    f"OpenAI API error: status={resp.status_code} "
                    f"attempt={attempt+1}/{self.max_retries} "
                    f"body={error_body}"
                )

                if resp.status_code == 429:
                    time.sleep(self.retry_delay * (2 ** attempt))
                    last_error = f"Rate limited (429): {error_body}"
                    continue
                elif resp.status_code in (500, 502, 503):
                    time.sleep(self.retry_delay * (2 ** attempt))
                    last_error = f"Server error ({resp.status_code}): {error_body}"
                    continue
                else:
                    return ModelResponse(
                        content=f"API error: {resp.status_code} - {error_body}",
                        stop_reason=StopReason.ERROR,
                        model=self.model,
                    )

            except requests.Timeout:
                last_error = f"Timeout (attempt {attempt+1})"
                logger.warning(last_error)
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
            except requests.RequestException as e:
                last_error = f"Request error: {e}"
                logger.warning(f"OpenAI request error (attempt {attempt+1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))

        return ModelResponse(
            content=f"Failed after {self.max_retries} retries: {last_error}",
            stop_reason=StopReason.ERROR,
            model=self.model,
        )

    async def call(
        self,
        messages: List[Message],
        tools: Optional[List[Dict]] = None,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> ModelResponse:
        """调用 OpenAI-compatible API"""
        api_messages = await self._convert_messages(messages, system)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._call_sync,
            api_messages,
            tools,
            system,
            max_tokens or self.default_max_tokens,
            temperature if temperature is not None else self.default_temperature,
        )

    def close(self):
        """关闭 HTTP 会话"""
        self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.close()
