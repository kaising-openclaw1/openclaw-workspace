"""Agent 核心模块"""
import json
import logging
from typing import Any, Callable, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    func: Callable
    parameters: dict  # JSON Schema 格式


@dataclass
class AgentConfig:
    """Agent 配置"""
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2000
    system_prompt: str = "You are a helpful assistant."
    tools: List[Tool] = field(default_factory=list)
    memory_enabled: bool = True


class Agent:
    """AI Agent 核心类"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.tools = {t.name: t for t in config.tools}
        self.messages = [{"role": "system", "content": config.system_prompt}]
        self.model_adapter = self._get_model_adapter(config.model)
        
    def _get_model_adapter(self, model: str):
        """获取模型适配器"""
        if model.startswith("gpt") or model.startswith("o"):
            from .adapters import OpenAIAdapter
            return OpenAIAdapter(model)
        elif model.startswith("claude"):
            from .adapters import ClaudeAdapter
            return ClaudeAdapter(model)
        else:
            from .adapters import LocalModelAdapter
            return LocalModelAdapter(model)
    
    async def run(self, user_input: str, context: dict = None) -> str:
        """运行 Agent，处理用户输入"""
        # 1. 添加用户消息到对话历史
        self.messages.append({"role": "user", "content": user_input})
        
        # 2. 调用模型
        response = await self.model_adapter.generate(
            messages=self.messages,
            tools=self._format_tools(),
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        
        # 3. 处理工具调用
        if response.tool_calls:
            for tool_call in response.tool_calls:
                result = await self._execute_tool(tool_call)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
            
            # 4. 基于工具结果再次生成
            response = await self.model_adapter.generate(
                messages=self.messages,
                temperature=self.config.temperature
            )
        
        # 5. 保存助手回复
        self.messages.append({"role": "assistant", "content": response.content})
        
        # 6. 清理过长的对话历史
        self._trim_history()
        
        return response.content
    
    async def _execute_tool(self, tool_call) -> Any:
        """执行工具调用"""
        tool_name = tool_call.function.name
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool = self.tools[tool_name]
        try:
            args = json.loads(tool_call.function.arguments)
            result = tool.func(**args)
            logger.info(f"Tool {tool_name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"error": str(e)}
    
    def _format_tools(self) -> list:
        """格式化工具定义为 OpenAI API 格式"""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters
                }
            }
            for t in self.config.tools
        ]
    
    def _trim_history(self):
        """清理过长的对话历史，保留最近 10 轮"""
        if len(self.messages) > 21:  # system + 20 messages (10 rounds)
            self.messages = [self.messages[0]] + self.messages[-20:]
    
    def reset(self):
        """重置对话"""
        self.messages = [{"role": "system", "content": self.config.system_prompt}]
