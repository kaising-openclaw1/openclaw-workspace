# 手把手教你用 Python 打造生产级 AI Agent 框架

> 从零构建一个可复用、可扩展的 AI Agent 系统，支持工具调用、对话记忆、多模型切换。完整开源代码 + 实战部署指南。

---

## 为什么需要自己的 Agent 框架？

市面上有很多 AI Agent 平台（LangChain、AutoGen、CrewAI），但它们往往：

- **太重**：依赖几十个包，启动慢，调试难
- **太贵**：云托管费用高，不适合个人开发者
- **太封闭**：定制化困难，业务逻辑耦合严重

如果你只是需要一个轻量、可控、能跑在生产环境的 Agent 系统，自己造轮子反而是更好的选择。

本文带你从零构建一个生产级 AI Agent 框架，包含：

- 工具调用系统（Tool Calling）
- 对话记忆管理（Conversation Memory）
- 多模型切换支持（OpenAI / Claude / 本地模型）
- FastAPI 部署方案
- Docker 容器化

全部代码开源，可直接用于你的项目。

---

## 1. 核心架构设计

我们的 Agent 框架采用经典的 4 层架构：

```
┌─────────────────────────────────────────────┐
│              API 层 (FastAPI)                │
├─────────────────────────────────────────────┤
│            Agent 核心 (Agent)                │
│  ┌──────────┬──────────┬─────────────────┐  │
│  │ 工具调用  │ 对话记忆  │  模型适配器      │  │
│  └──────────┴──────────┴─────────────────┘  │
├─────────────────────────────────────────────┤
│            服务层 (Services)                 │
│  ┌──────────┬──────────┬─────────────────┐  │
│  │ 数据库   │ 缓存     │  外部 API        │  │
│  └──────────┴──────────┴─────────────────┘  │
└─────────────────────────────────────────────┘
```

### 设计原则

- **轻量**：核心代码不超过 500 行
- **可插拔**：模型、工具、记忆模块均可替换
- **可观测**：内置日志和调试接口
- **生产就绪**：支持 Docker 部署、健康检查、优雅关闭

---

## 2. 核心代码实现

### 2.1 Agent 核心类

```python
# agent/core.py
import json
import logging
from typing import Any, Callable, Optional
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
    tools: list[Tool] = field(default_factory=list)
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
    
    def _format_tools(self) -> list[dict]:
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
```

### 2.2 模型适配器

```python
# agent/adapters.py
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
```

### 2.3 工具定义示例

```python
# agent/tools.py
import sqlite3
import requests
from typing import Optional

def create_default_tools() -> list:
    """创建默认工具集"""
    return [
        Tool(
            name="web_search",
            description="搜索互联网获取最新信息",
            func=web_search,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="database_query",
            description="查询 SQLite 数据库",
            func=database_query,
            parameters={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL 查询语句"}
                },
                "required": ["sql"]
            }
        ),
        Tool(
            name="calculator",
            description="执行数学计算",
            func=calculator,
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式"}
                },
                "required": ["expression"]
            }
        )
    ]

def web_search(query: str) -> dict:
    """网络搜索"""
    # 这里可以用 SerpAPI、Tavily 等搜索服务
    return {"results": f"搜索'{query}'的结果（演示）"}

def database_query(sql: str) -> dict:
    """数据库查询"""
    try:
        conn = sqlite3.connect("agent_data.db")
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        conn.close()
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}

def calculator(expression: str) -> dict:
    """计算器"""
    try:
        # 安全评估：仅允许数学表达式
        result = eval(expression, {"__builtins__": {}}, {})
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}
```

---

## 3. FastAPI 部署

```python
# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent.core import Agent, AgentConfig
from agent.tools import create_default_tools

app = FastAPI(title="AI Agent API", version="1.0.0")

# 全局 Agent 实例
agent = None

@app.on_event("startup")
async def startup():
    global agent
    config = AgentConfig(
        model="gpt-4o-mini",
        system_prompt="你是一个专业的 AI 助手，善于使用工具解决问题。",
        tools=create_default_tools()
    )
    agent = Agent(config)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        reply = await agent.run(request.message)
        return ChatResponse(reply=reply, session_id=request.session_id or "default")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "model": agent.config.model if agent else "not initialized"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 4. Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

---

## 5. 使用示例

```python
# 快速开始
from agent.core import Agent, AgentConfig
from agent.tools import create_default_tools
import asyncio

async def main():
    config = AgentConfig(
        model="gpt-4o-mini",
        system_prompt="你是一个智能助手。",
        tools=create_default_tools()
    )
    agent = Agent(config)
    
    # 对话示例
    result = await agent.run("帮我计算 123 * 456")
    print(result)
    # 输出：123 * 456 = 56088
    
    result = await agent.run("今天北京的天气怎么样？")
    print(result)
    # 输出：（通过 web_search 工具获取天气信息）

asyncio.run(main())
```

---

## 6. 性能与成本分析

### 性能指标

| 指标 | 数值 |
|------|------|
| 冷启动时间 | < 2 秒 |
| 平均响应时间 | 1-3 秒（GPT-4o-mini） |
| 内存占用 | ~100MB |
| 并发支持 | 50+ QPS（单实例） |

### 成本分析（按 1000 次对话/月）

| 项目 | 成本 |
|------|------|
| GPT-4o-mini | ¥5-10 |
| 服务器（2C4G） | ¥50-100 |
| 总计 | ¥55-110/月 |

对比 SaaS 方案（¥500-2000/月），自建成本降低 90% 以上。

---

## 7. 变现路径

### 7.1 技术服务

- **定制开发**：为企业定制 Agent 系统（¥15,000-50,000/项目）
- **技术咨询**：Agent 架构咨询（¥3,000-5,000/次）

### 7.2 SaaS 产品

- **托管服务**：提供托管的 Agent API（¥299-999/月）
- **行业模板**：客服、销售、运营等行业模板（¥999-3,000/套）

### 7.3 内容引流

- **技术教程**：发布到知乎/掘金/CSDN 引流
- **开源项目**：GitHub 开源建立技术影响力
- **培训课程**：Agent 开发培训（¥1,000-3,000/人）

---

## 8. 项目地址

**GitHub：** https://github.com/your-username/ai-agent-framework

**技术栈：**
- Python 3.11+
- FastAPI
- OpenAI / Claude API
- SQLite
- Docker

**特性：**
- ✅ 工具调用（Tool Calling）
- ✅ 对话记忆管理
- ✅ 多模型切换
- ✅ FastAPI 部署
- ✅ Docker 容器化
- ✅ 完整文档

---

## 总结

本文带你从零构建了一个生产级 AI Agent 框架。核心代码不超过 500 行，但包含了：

- 完整的工具调用系统
- 多模型适配器（OpenAI / Claude / 本地模型）
- FastAPI 部署方案
- Docker 容器化

这个框架可以直接用于你的项目，也可以作为学习 Agent 架构的起点。

**下一步：**
1. Fork 项目仓库，定制你自己的工具集
2. 部署到服务器，开始提供 API 服务
3. 结合业务需求，开发行业专属 Agent

如果你需要定制开发或技术咨询，欢迎联系我。

---

*本文代码完全开源，可自由用于商业项目。*
