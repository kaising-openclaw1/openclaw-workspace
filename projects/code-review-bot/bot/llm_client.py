"""LLM client with multi-provider support."""

from typing import Optional
import os
import json


class LLMClient:
    """Unified LLM client supporting multiple providers."""

    PROVIDERS = {
        "qwen": {"endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "env_key": "DASHSCOPE_API_KEY"},
        "openai": {"endpoint": "https://api.openai.com/v1/chat/completions", "env_key": "OPENAI_API_KEY"},
        "deepseek": {"endpoint": "https://api.deepseek.com/v1/chat/completions", "env_key": "DEEPSEEK_API_KEY"},
        "anthropic": {"endpoint": "https://api.anthropic.com/v1/messages", "env_key": "ANTHROPIC_API_KEY"},
    }

    def __init__(self, model: str = "qwen-plus", api_key: Optional[str] = None):
        self.model = model
        self.provider = self._detect_provider(model)
        self.api_key = api_key or os.environ.get(self.PROVIDERS[self.provider]["env_key"], "")
        self.endpoint = self.PROVIDERS[self.provider]["endpoint"]

    def _detect_provider(self, model: str) -> str:
        if model.startswith("gpt") or model.startswith("o"):
            return "openai"
        elif model.startswith("claude"):
            return "anthropic"
        elif model.startswith("deepseek"):
            return "deepseek"
        else:
            return "qwen"

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        """Send a chat request to the LLM."""
        import urllib.request
        import json as _json

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        if self.provider == "anthropic":
            headers["x-api-key"] = self.api_key
            headers["anthropic-version"] = "2023-06-01"
            payload = {
                "model": self.model,
                "max_tokens": 4096,
                "temperature": temperature,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            }
        else:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
            }

        data = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.endpoint, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = _json.loads(resp.read().decode("utf-8"))

            if self.provider == "anthropic":
                return result["content"][0]["text"]
            else:
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {e}")

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Send a chat request expecting JSON response."""
        import json as _json

        prompt = f"{user_prompt}\n\n请只输出 JSON，不要输出其他内容。"
        response = self.chat(system_prompt, prompt, temperature=0.1)
        # Extract JSON from possible markdown code block
        if "```" in response:
            for line in response.split("\n"):
                if line.strip().startswith("{") or line.strip().startswith("["):
                    start = response.index(line)
                    end = response.rfind("```")
                    if end > start:
                        response = response[start:end].strip()
                    break
        return _json.loads(response)
