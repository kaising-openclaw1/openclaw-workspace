# Agent Native Starter 🤖

> **从传统 API 到 AI 原生架构的脚手架** — 为你的应用集成 AI Agent 能力

## 概述

这个脚手架帮助你快速将传统 Web 应用改造为 **Agent-Native 架构**，即应用的核心逻辑由 AI Agent 驱动而非硬编码规则。

## 特性

- 🧠 Agent 驱动的核心业务逻辑
- 🔌 工具调用（Tool Calling）集成
- 📝 结构化输出（JSON Schema）
- 🔄 多步工作流编排
- 💬 对话式交互接口
- 🧪 内置测试框架（兼容 agent-test-framework）

## 快速开始

```python
from agent_native_starter import AgentApp, Tool

app = AgentApp()

@app.tool("weather")
def get_weather(city: str) -> str:
    return f"{city} 今天晴，25°C"

@app.route("ask")
async def handle_query(query: str):
    return await app.agent.run(query, tools=["weather"])
```

## 架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   用户请求   │ ──→ │ Agent Router │ ──→ │  Tool Calls  │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                      │
                           ▼                      ▼
                    ┌──────────────┐     ┌─────────────┐
                    │  LLM Backend  │ ←── │  结果整合   │
                    └──────────────┘     └─────────────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │  用户响应    │
                                         └─────────────┘
```

## 配置

```yaml
# config.yaml
agent:
  model: "gpt-4o"
  temperature: 0.1
  max_turns: 5

tools:
  - name: weather
    endpoint: "https://api.weather.com/v1"
  - name: search
    endpoint: "internal://search"
```

## 安装

```bash
pip install agent-native-starter
```

## License

MIT
