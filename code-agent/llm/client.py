"""LLM API 客户端 — 火山引擎 DeepSeek"""

import json
import os
import requests
from typing import List, Dict, Optional, Callable, Any

API_BASE = "https://ark.cn-beijing.volces.com/api/plan/v3"
MODEL = "deepseek-v4-flash"


class LLMClient:
    """DeepSeek API 客户端，支持流式输出和工具调用"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENCLAW_API_KEY") or ""
        self.base_url = (base_url or API_BASE).rstrip("/")
        self.model = MODEL

    def chat(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
        temperature: float = 0.3,
        max_tokens: int = 64000,
    ) -> Dict:
        """发送聊天请求"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()

    def chat_stream(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 64000,
    ):
        """流式聊天请求"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools

        with requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=180,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            continue
