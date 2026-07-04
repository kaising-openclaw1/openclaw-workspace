"""
Agent OS v7.0 — Anthropic Claude Model Adapter
================================================
支持 Anthropic Claude 系列模型 (claude-sonnet-4, claude-haiku-3.5 等)。

用法：
    adapter = AnthropicAdapter(api_key="sk-ant-...", model="claude-sonnet-4-20250514")
    response = await adapter.call(messages, tools, system="...")
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from ..core_loop import Message, MessageRole, ModelAdapter, ModelResponse, StopReason

logger = logging.getLogger("agent-os.engine.adapters.anthropic")

# Anthropic API 版本
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicAdapter(ModelAdapter):
    """
    Anthropic Claude 模型适配器

    支持：
    - claude-sonnet-4 (20250514)
    - claude-sonnet-4-20250514
    - claude-haiku-3.5
    - claude-opus-4
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        base_url: str = "https://api.anthropic.com/v1",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 120.0,
        default_max_tokens: int = 4096,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.default_max_tokens = default_max_tokens
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def _convert_messages(
        self,
        messages: List[Message],
    ) -> List[Dict[str, Any]]:
        """
        将内部 Message 列表转换为 Anthropic API 格式

        Anthropic 消息格式：
        - system 提示在顶层参数中，不在 messages 数组里
        - tool_result 通过 content 块传递
        """
        result: List[Dict[str, Any]] = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # System 消息在 Anthropic 中通过顶层 system 参数传递
                # 这里跳过，由调用方处理
                continue

            entry: Dict[str, Any] = {"role": self._map_role(msg.role)}

            if msg.role == MessageRole.TOOL:
                # Tool result 使用 content 块格式
                entry["content"] = [
                    {
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id or "",
                        "content": msg.content,
                    }
                ]
            elif msg.tool_calls:
                # Assistant 消息带 tool_calls
                content: List[Dict] = []
                if msg.content:
                    content.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    fn = tc.get("function", {})
                    args = fn.get("arguments", "{}")
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {"raw": args}
                    content.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": fn.get("name", ""),
                        "input": args,
                    })
                entry["content"] = content
            else:
                entry["content"] = msg.content

            result.append(entry)

        return result

    def _map_role(self, role: MessageRole) -> str:
        """映射角色到 Anthropic 格式"""
        mapping = {
            MessageRole.USER: "user",
            MessageRole.ASSISTANT: "assistant",
            MessageRole.TOOL: "user",  # tool_result 包装在 user 消息中
        }
        return mapping.get(role, "user")

    def _convert_tools(self, tools: Optional[List[Dict]]) -> Optional[List[Dict]]:
        """将 OpenAI 格式 tools 转换为 Anthropic 格式"""
        if not tools:
            return None

        anthropic_tools = []
        for tool in tools:
            fn = tool.get("function", tool)
            anthropic_tools.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {}),
            })
        return anthropic_tools

    def _convert_response(self, raw: Dict[str, Any]) -> ModelResponse:
        """将 Anthropic API 响应转换为内部 ModelResponse"""
        content_blocks = raw.get("content", [])
        stop_reason_raw = raw.get("stop_reason", "end_turn")

        # 提取文本内容
        text_parts = []
        tool_calls = []

        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": block.get("name", ""),
                        "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                    },
                })

        # 映射 stop_reason
        stop_reason_map = {
            "end_turn": StopReason.END_TURN,
            "tool_use": StopReason.TOOL_USE,
            "max_tokens": StopReason.MAX_TOKENS,
            "stop_sequence": StopReason.STOP_SEQUENCE,
        }
        stop_reason = stop_reason_map.get(stop_reason_raw, StopReason.END_TURN)

        # 提取 usage
        usage = raw.get("usage", {})
        model_name = raw.get("model", self.model)

        return ModelResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage={
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            },
            model=model_name,
        )

    async def call(
        self,
        messages: List[Message],
        tools: Optional[List[Dict]] = None,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> ModelResponse:
        """调用 Anthropic Claude API"""
        api_messages = await self._convert_messages(messages)
        anthropic_tools = self._convert_tools(tools)

        body: Dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": max_tokens or self.default_max_tokens,
        }

        if system:
            body["system"] = system

        if anthropic_tools:
            body["tools"] = anthropic_tools

        if temperature is not None:
            body["temperature"] = temperature

        last_error = None
        for attempt in range(self.max_retries):
            try:
                start = time.time()
                response = await self.client.post("/messages", json=body)
                elapsed = time.time() - start

                if response.status_code == 200:
                    data = response.json()
                    logger.debug(
                        f"Anthropic call: model={self.model} "
                        f"status=200 elapsed={elapsed:.2f}s "
                        f"usage={data.get('usage', {})}"
                    )
                    return self._convert_response(data)

                # 错误处理
                error_body = response.text[:500]
                logger.warning(
                    f"Anthropic API error: status={response.status_code} "
                    f"attempt={attempt+1}/{self.max_retries} "
                    f"body={error_body}"
                )

                if response.status_code == 429:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    last_error = f"Rate limited (429): {error_body}"
                    continue
                elif response.status_code in (500, 502, 503):
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    last_error = f"Server error ({response.status_code}): {error_body}"
                    continue
                else:
                    return ModelResponse(
                        content=f"API error: {response.status_code} - {error_body}",
                        stop_reason=StopReason.ERROR,
                        model=self.model,
                    )

            except httpx.TimeoutException as e:
                last_error = f"Timeout: {e}"
                logger.warning(f"Anthropic timeout (attempt {attempt+1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
            except httpx.RequestError as e:
                last_error = f"Request error: {e}"
                logger.warning(f"Anthropic request error (attempt {attempt+1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))

        return ModelResponse(
            content=f"Failed after {self.max_retries} retries: {last_error}",
            stop_reason=StopReason.ERROR,
            model=self.model,
        )

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


import asyncio  # noqa: E402
