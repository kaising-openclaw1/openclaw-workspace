"""LLM 后端抽象 - 支持多种 LLM 提供商"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    """LLM 配置"""

    provider: str  # "openai", "deepseek", "dashscope", "ollama"
    model: str
    api_key: str = ""
    base_url: str = ""

    @property
    def url(self) -> str:
        if self.base_url:
            return self.base_url
        urls = {
            "openai": "https://api.openai.com/v1/chat/completions",
            "deepseek": "https://api.deepseek.com/v1/chat/completions",
            "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "ollama": "http://localhost:11434/api/chat",
        }
        return urls.get(self.provider, urls["openai"])

    @property
    def auth_header(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}


async def call_llm(
    prompt: str,
    config: Optional[LLMConfig] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """调用 LLM 获取回复"""
    import httpx

    if config is None:
        # 默认使用 DeepSeek（高性价比，中文能力强）
        config = LLMConfig(
            provider="deepseek",
            model="deepseek-chat",
        )

    headers = config.auth_header
    if config.provider == "ollama":
        headers = {"Content-Type": "application/json"}

    payload = {
        "model": config.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(config.url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if config.provider == "ollama":
            return data.get("message", {}).get("content", "")
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
