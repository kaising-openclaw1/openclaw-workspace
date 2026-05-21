# AI Agent Gateway 🚪

> **智能路由、成本控制与生产级部署** — 统一管理多个 LLM 后端

## 痛点

你的 AI 应用接入了多个 LLM 提供商（OpenAI、Claude、DeepSeek、本地模型），但：
- ❌ 每个 API 调用方式不同，代码臃肿
- ❌ 没有统一的路由策略，浪费成本
- ❌ 无法做请求限流和降级
- ❌ 缺乏统一监控和日志

## 功能

- 🔀 **智能路由** — 按成本/性能/可用性自动选择后端
- 💰 **成本控制** — 预算上限、按优先级降级
- 📊 **统一监控** — 请求量、延迟、成本的实时仪表盘
- 🔄 **自动降级** — 主模型不可用时切换到备用模型
- 📝 **统一接口** — 一套 API 对接所有 LLM 提供商

## 快速开始

```python
from ai_agent_gateway import Gateway, Route

gateway = Gateway()

# 添加路由
gateway.add_route(Route(
    name="primary",
    provider="openai",
    model="gpt-4o",
    priority=1,
    cost_per_1k=0.01,
))
gateway.add_route(Route(
    name="fallback",
    provider="deepseek",
    model="deepseek-chat",
    priority=2,
    cost_per_1k=0.001,
))

# 统一调用
response = gateway.chat(
    messages=[{"role": "user", "content": "Hello"}],
    strategy="cost_optimized",  # 自动选择最优路径
)
```

## 安装

```bash
pip install ai-agent-gateway
```

## License

MIT
