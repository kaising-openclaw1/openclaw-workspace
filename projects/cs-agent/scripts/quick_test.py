#!/usr/bin/env python3
"""快速测试脚本"""
import asyncio
import sys
from agent.core import Agent, AgentConfig
from agent.tools import create_default_tools


async def main():
    print("🚀 CS-Agent 快速测试")
    print("=" * 50)
    
    config = AgentConfig(
        model="gpt-4o-mini",
        system_prompt="你是一个专业的 AI 客服助手。",
        tools=create_default_tools()
    )
    agent = Agent(config)
    
    # 测试计算器
    print("\n📝 测试 1: 数学计算")
    result = await agent.run("帮我计算 123 * 456")
    print(f"Agent: {result}")
    
    # 测试订单查询
    print("\n📝 测试 2: 订单查询")
    result = await agent.run("我的订单 ORD001 状态如何？")
    print(f"Agent: {result}")
    
    # 测试知识库
    print("\n📝 测试 3: 知识库检索")
    result = await agent.run("你们的退货政策是什么？")
    print(f"Agent: {result}")
    
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
