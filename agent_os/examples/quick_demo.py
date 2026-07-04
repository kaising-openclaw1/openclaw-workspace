#!/usr/bin/env python3
"""
Agent OS v7.0 — Quick Demo
===========================
Demonstrates the core execution loop with mock, OpenAI, or Anthropic backend.

Usage:
    # Mock mode (no API key needed)
    python agent_os/examples/quick_demo.py --mode mock

    # OpenAI mode
    python agent_os/examples/quick_demo.py --mode openai --api-key sk-...

    # Anthropic mode
    python agent_os/examples/quick_demo.py --mode anthropic --api-key sk-ant-...
"""

import argparse
import asyncio
import sys
import os

# Add workspace to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Direct import to avoid httpx dependency when not needed
from agent_os.engine.core_loop import (
    AgentLoop,
    Message,
    MessagePipeline,
    MessageRole,
    ModelAdapter,
    ModelResponse,
    StopReason,
    ToolDef,
    ToolEngine,
    create_default_tools,
)


# ═══════════════════════════════════════════════════════════════
# Mock Adapter — 无需 API 密钥即可演示
# ═══════════════════════════════════════════════════════════════

class MockAdapter(ModelAdapter):
    """模拟模型适配器，用于演示和测试"""

    def __init__(self, name: str = "mock-model"):
        self.name = name
        self._call_count = 0

    async def call(self, messages, tools=None, system=None, max_tokens=4096, temperature=0.0):
        self._call_count += 1

        # 从消息中提取用户最新输入
        user_msgs = [m for m in messages if m.role == MessageRole.USER]
        last_user = user_msgs[-1].content if user_msgs else ""

        # 模拟工具调用或直接回复
        if self._call_count == 1 and tools:
            # 第一次调用：模拟工具调用
            return ModelResponse(
                content="Let me search for that information.",
                tool_calls=[{
                    "id": "call_mock_1",
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "arguments": '{"query": "' + last_user[:50] + '"}',
                    },
                }],
                stop_reason=StopReason.TOOL_USE,
                model=self.name,
            )
        else:
            # 后续调用：模拟最终回复
            return ModelResponse(
                content=f"Based on my analysis of '{last_user[:80]}', here's what I found:\n\n"
                        f"This is a simulated response from Agent OS v7.0 ({self.name}).\n"
                        f"The core loop completed in {self._call_count} iteration(s).\n\n"
                        f"In production, this would use a real LLM backend like OpenAI or Anthropic.",
                stop_reason=StopReason.END_TURN,
                model=self.name,
            )


# ═══════════════════════════════════════════════════════════════
# 自定义工具示例
# ═══════════════════════════════════════════════════════════════

async def calculator(expression: str) -> str:
    """安全计算器 — 仅支持基本运算"""
    allowed = set("0123456789+-*/()., ")
    if not all(c in allowed for c in expression):
        return "Error: Invalid characters in expression"
    try:
        # 安全评估（仅允许字面量表达式）
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"


async def get_time() -> str:
    """返回当前时间"""
    from datetime import datetime
    return f"Current time: {datetime.now().isoformat()}"


def create_demo_tools() -> ToolEngine:
    """创建演示用工具集"""
    engine = create_default_tools()

    engine.register(ToolDef(
        name="calculator",
        description="Perform basic arithmetic calculations",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression (e.g., 2 + 2 * 3)",
                },
            },
            "required": ["expression"],
        },
        handler=calculator,
    ))

    engine.register(ToolDef(
        name="get_time",
        description="Get the current system time",
        parameters={
            "type": "object",
            "properties": {},
        },
        handler=get_time,
    ))

    return engine


# ═══════════════════════════════════════════════════════════════
# 主演示
# ═══════════════════════════════════════════════════════════════

async def run_demo(mode: str, api_key: str = ""):
    """运行 Agent OS 演示"""

    # 1. 创建工具引擎
    tools = create_demo_tools()
    print("🔧 Tools registered:")
    for schema in tools.get_schemas():
        name = schema["function"]["name"]
        desc = schema["function"]["description"]
        print(f"   • {name}: {desc}")

    # 2. 创建模型适配器
    if mode == "mock":
        adapter = MockAdapter()
        print(f"\n🤖 Model: MockAdapter (no API key needed)")
    elif mode == "openai":
        from agent_os.engine.adapters import OpenAIAdapter
        adapter = OpenAIAdapter(
            api_key=api_key or os.getenv("OPENAI_API_KEY", ""),
            model="gpt-4o",
        )
        print(f"\n🤖 Model: OpenAI (gpt-4o)")
    elif mode == "anthropic":
        from agent_os.engine.adapters import AnthropicAdapter
        adapter = AnthropicAdapter(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY", ""),
            model="claude-sonnet-4-20250514",
        )
        print(f"\n🤖 Model: Anthropic (claude-sonnet-4-20250514)")
    else:
        print(f"Unknown mode: {mode}")
        return

    # 3. 创建核心循环
    loop = AgentLoop(
        model=adapter,
        tools=tools,
        system_prompt="You are Agent OS v7.0, a helpful AI assistant with tool-use capabilities.",
        pipeline=MessagePipeline(max_history=50),
    )

    # 4. 运行
    print(f"\n{'='*60}")
    print("🚀 Agent OS v7.0 Core Loop Demo")
    print(f"{'='*60}\n")

    user_input = "What's the current time and calculate 42 * 13?"
    print(f"👤 User: {user_input}\n")

    response, messages = await loop.run(user_input)

    print(f"🤖 Assistant: {response}\n")
    print(f"{'='*60}")
    print(f"📊 Stats:")
    print(f"   Iterations: {loop.iteration_count}")
    print(f"   Elapsed: {loop.elapsed:.2f}s")
    print(f"   Messages in history: {len(messages)}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Agent OS v7.0 Quick Demo")
    parser.add_argument("--mode", choices=["mock", "openai", "anthropic"],
                        default="mock", help="Model backend (default: mock)")
    parser.add_argument("--api-key", default="", help="API key for the model backend")
    args = parser.parse_args()

    asyncio.run(run_demo(args.mode, args.api_key))


if __name__ == "__main__":
    main()
