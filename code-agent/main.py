#!/usr/bin/env python3
"""Code Agent — 终端 AI 编程助手（Claude Code 替代品）"""

import sys
import os

# 确保能找到模块
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core.loop import CodeAgent
from core.session import save_session, load_session, list_sessions
from tools.file_ops import read_file
from tools.code_search import analyze_project


def print_banner():
    print("╔══════════════════════════════════════════════╗")
    print("║   🦊 Code Agent v1.0                        ║")
    print("║   终端 AI 编程助手                           ║")
    print("║   输入 /help 查看命令  /quit 退出           ║")
    print("╚══════════════════════════════════════════════╝")
    print()


def print_help():
    print("""
命令:
  /help          显示此帮助
  /quit          退出
  /project       分析当前项目
  /read <path>   读取文件
  /sessions      列出历史会话
  /load <name>   加载历史会话
  /verbose       切换详细模式

使用方式:
  直接输入你的需求，Code Agent 会理解并执行。
  例如:
    "分析这个项目的结构"
    "帮我重构 main.py 中的函数"
    "找到所有使用 requests 的地方并改为 httpx"
    "运行测试并修复失败"
""")


def main():
    print_banner()

    agent = CodeAgent(verbose=False)
    session_name = None

    while True:
        try:
            user_input = input("\n💻 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n再见！👋")
            break

        if not user_input:
            continue

        if user_input == "/quit":
            print("再见！👋")
            break

        elif user_input == "/help":
            print_help()
            continue

        elif user_input == "/verbose":
            agent.verbose = not agent.verbose
            print(f"详细模式: {'✅' if agent.verbose else '❌'}")
            continue

        elif user_input == "/project":
            path = os.getcwd()
            print(analyze_project(path))
            continue

        elif user_input.startswith("/read "):
            path = user_input[6:].strip()
            print(read_file(path))
            continue

        elif user_input == "/sessions":
            sessions = list_sessions()
            if sessions:
                print("历史会话:")
                for s in sessions[:20]:
                    print(f"  {s}")
            else:
                print("没有历史会话")
            continue

        elif user_input.startswith("/load "):
            name = user_input[6:].strip()
            msgs = load_session(name)
            if msgs:
                agent.messages = msgs
                print(f"已加载会话: {name}")
            else:
                print(f"未找到会话: {name}")
            continue

        # 执行任务
        print(f"\n🔄 处理中...")
        try:
            result = agent.run(user_input)
            print(f"\n{result}")

            # 自动保存会话
            session_name = save_session(agent.messages, session_name)
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
