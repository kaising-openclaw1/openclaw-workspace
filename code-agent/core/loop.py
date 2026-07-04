"""Code Agent 主对话循环 — 核心执行引擎"""

import json
import sys
import os
import time
from typing import List, Dict, Optional, Callable, Any

# 确保能找到模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.client import LLMClient
from llm.prompts import SYSTEM_PROMPT, TOOL_DESCRIPTIONS
from tools.file_ops import read_file, write_file, edit_file, list_files
from tools.code_search import search_code, grep, analyze_project
from tools.exec_cmd import run_command


# 工具注册表
TOOL_REGISTRY = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_files": list_files,
    "search_code": search_code,
    "grep": grep,
    "analyze_project": analyze_project,
    "run_command": run_command,
}


class CodeAgent:
    """Code Agent 主循环"""

    def __init__(self, api_key: Optional[str] = None, verbose: bool = False):
        self.llm = LLMClient(api_key=api_key)
        self.messages: List[Dict] = []
        self.verbose = verbose
        self.max_turns = 50
        self.turn_count = 0

    def run(self, user_input: str) -> str:
        """运行一个完整任务"""
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]

        self.turn_count = 0
        while self.turn_count < self.max_turns:
            self.turn_count += 1

            if self.verbose:
                print(f"\n{'='*60}")
                print(f"🔄 Turn {self.turn_count}")
                print(f"{'='*60}")

            # 调用 LLM
            response = self._call_llm()

            # 检查是否返回了最终回复
            content = response.get("content", "")
            tool_calls = response.get("tool_calls", [])

            if not tool_calls:
                # 没有工具调用 → 最终回复
                return content

            # 执行工具调用
            for tc in tool_calls:
                result = self._execute_tool(tc)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": result,
                })

        return "错误：超过最大对话轮数"

    def _call_llm(self) -> Dict:
        """调用 LLM 并解析响应"""
        tools_list = list(TOOL_DESCRIPTIONS.values())

        raw = self.llm.chat(
            messages=self.messages,
            tools=tools_list,
            temperature=0.3,
        )

        choice = raw["choices"][0]
        msg = choice["message"]

        content = msg.get("content", "")
        tool_calls_raw = msg.get("tool_calls", [])

        if self.verbose:
            if content:
                print(f"\n🤖 LLM: {content[:200]}...")
            if tool_calls_raw:
                for tc in tool_calls_raw:
                    fn = tc.get("function", {})
                    print(f"🔧 Tool call: {fn.get('name')}({fn.get('arguments', '')[:100]}...)")

        # 保存 assistant 消息
        assistant_msg = {"role": "assistant", "content": content}
        if tool_calls_raw:
            assistant_msg["tool_calls"] = tool_calls_raw
        self.messages.append(assistant_msg)

        # 解析工具调用
        tool_calls = []
        for tc in tool_calls_raw:
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({
                "id": tc.get("id", ""),
                "name": fn.get("name", ""),
                "arguments": args,
            })

        return {"content": content, "tool_calls": tool_calls}

    def _execute_tool(self, tc: Dict) -> str:
        """执行单个工具调用"""
        name = tc.get("name", "")
        args = tc.get("arguments", {})

        if name not in TOOL_REGISTRY:
            return f"错误：未知工具 '{name}'"

        if self.verbose:
            print(f"  ▶️  {name}({json.dumps(args, ensure_ascii=False)[:200]})")

        try:
            start = time.time()
            result = TOOL_REGISTRY[name](**args)
            elapsed = time.time() - start
            if self.verbose:
                print(f"  ✅ 完成 ({elapsed:.1f}s)")
            # 截断过长结果
            if len(result) > 10000:
                result = result[:10000] + f"\n... (结果截断，原长 {len(result)} 字符)"
            return result
        except Exception as e:
            error_msg = f"工具执行错误 ({name}): {e}"
            if self.verbose:
                print(f"  ❌ {error_msg}")
            return error_msg
