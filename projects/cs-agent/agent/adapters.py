"""模型适配器"""
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class ModelResponse:
    content: str
    tool_calls: Optional[list] = None


class BaseAdapter:
    """模型适配器基类"""
    def __init__(self, model: str):
        self.model = model
    
    async def generate(self, messages: list, **kwargs) -> ModelResponse:
        raise NotImplementedError


class OpenAIAdapter(BaseAdapter):
    """OpenAI 模型适配器"""
    def __init__(self, model: str):
        super().__init__(model)
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def generate(self, messages: list, tools=None, **kwargs) -> ModelResponse:
        params = {
            "model": self.model,
            "messages": messages,
            **kwargs
        }
        if tools:
            params["tools"] = tools
        
        response = await self.client.chat.completions.create(**params)
        choice = response.choices[0].message
        
        return ModelResponse(
            content=choice.content or "",
            tool_calls=choice.tool_calls
        )


class ClaudeAdapter(BaseAdapter):
    """Claude 模型适配器"""
    def __init__(self, model: str):
        super().__init__(model)
        import anthropic
        self.client = anthropic.AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    
    async def generate(self, messages: list, tools=None, **kwargs) -> ModelResponse:
        # 转换消息格式为 Claude 格式
        system_msg = ""
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                claude_messages.append(msg)
        
        params = {
            "model": self.model,
            "system": system_msg,
            "messages": claude_messages,
            **kwargs
        }
        
        response = await self.client.messages.create(**params)
        
        return ModelResponse(content=response.content[0].text)


class LocalModelAdapter(BaseAdapter):
    """本地模型适配器（支持 Ollama、vLLM 等）"""
    def __init__(self, model: str):
        super().__init__(model)
        self.base_url = os.getenv("LOCAL_MODEL_URL", "http://localhost:11434")
    
    async def generate(self, messages: list, **kwargs) -> ModelResponse:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    **kwargs
                }
            ) as response:
                data = await response.json()
                content = data["choices"][0]["message"]["content"]
                return ModelResponse(content=content)
