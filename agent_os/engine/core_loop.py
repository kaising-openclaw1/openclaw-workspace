"""
Agent OS v7.0 — 核心执行循环
=============================
"核心循环只有 200 行，但这是最重要的 200 行" — Claude Code 架构教训 #1

设计原则：
1. 极简核心：while True 循环，所有复杂度推到外围
2. 模型无关：支持 OpenAI/Anthropic/Google/本地模型
3. 消息管道：采集→压缩→注入→预算
4. 工具循环：调用→权限→执行→反馈
5. 生产就绪：重试、超时、回退、审计

用法：
    loop = AgentLoop(model="claude-sonnet-4")
    await loop.run("帮我重构这个模块")
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("agent-os.engine.core_loop")


# ═══════════════════════════════════════════════════════════════
# 1. 类型定义 (~30 LOC)
# ═══════════════════════════════════════════════════════════════

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass
class Message:
    role: MessageRole
    content: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d

@dataclass
class ToolDef:
    """声明式工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    handler: Callable
    permission_level: str = "user"  # user | admin | system
    timeout: float = 30.0

@dataclass
class ModelResponse:
    content: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    stop_reason: str = "end_turn"
    usage: Dict[str, int] = field(default_factory=dict)
    model: str = ""

class StopReason(str, Enum):
    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    ERROR = "error"


# ═══════════════════════════════════════════════════════════════
# 2. 模型适配器接口 (~20 LOC)
# ═══════════════════════════════════════════════════════════════

class ModelAdapter:
    """模型适配器基类 — 支持任意 LLM 后端"""

    async def call(
        self,
        messages: List[Message],
        tools: Optional[List[Dict]] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> ModelResponse:
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════
# 3. 消息管道 (~40 LOC)
# ═══════════════════════════════════════════════════════════════

class MessagePipeline:
    """
    消息管道：采集 → 压缩 → 注入 → 预算
    负责消息的预处理和后处理
    """

    def __init__(self, max_history: int = 100, max_tokens: int = 128000):
        self.max_history = max_history
        self.max_tokens = max_tokens
        self._token_estimator = lambda s: len(s) // 2  # 粗略估计

    async def process_input(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Message], Optional[str]]:
        """采集 → 压缩 → 注入 → 预算"""
        msgs = list(messages)

        # 压缩：截断历史
        if len(msgs) > self.max_history:
            # 保留系统消息 + 最近 N 条
            system_msgs = [m for m in msgs if m.role == MessageRole.SYSTEM]
            recent = msgs[-self.max_history:]
            msgs = system_msgs + [m for m in recent if m.role != MessageRole.SYSTEM]

        # 注入：添加上下文
        if context:
            ctx_str = json.dumps(context, ensure_ascii=False)
            msgs.append(Message(role=MessageRole.SYSTEM, content=f"[Context]: {ctx_str}"))

        # 预算：检查 token 预算
        total_tokens = sum(self._token_estimator(m.content) for m in msgs)
        if total_tokens > self.max_tokens * 0.8:
            logger.warning(f"Token budget warning: ~{total_tokens} tokens (limit: {self.max_tokens})")

        return msgs, system_prompt

    async def process_output(self, response: ModelResponse) -> ModelResponse:
        """后处理模型输出"""
        return response


# ═══════════════════════════════════════════════════════════════
# 4. 工具执行引擎 (~50 LOC)
# ═══════════════════════════════════════════════════════════════

class ToolEngine:
    """
    工具执行引擎：调用 → 权限 → 执行 → 反馈
    声明式工具注册 + 权限检查 + 超时控制
    """

    def __init__(self):
        self._tools: Dict[str, ToolDef] = {}
        self._tool_schemas: List[Dict] = []

    def register(self, tool: ToolDef):
        """注册工具"""
        self._tools[tool.name] = tool
        self._tool_schemas.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        })

    def get_schemas(self) -> List[Dict]:
        """获取所有工具的 OpenAI 格式 schema"""
        return self._tool_schemas

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        permission_context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """执行单个工具调用"""
        tool = self._tools.get(tool_name)
        if not tool:
            return {"error": f"Unknown tool: {tool_name}"}

        # 权限检查（占位）
        if tool.permission_level == "admin" and not permission_context:
            return {"error": f"Permission denied: {tool_name} requires admin level"}

        # 执行（带超时）
        try:
            result = await asyncio.wait_for(
                tool.handler(**arguments),
                timeout=tool.timeout,
            )
            return {"result": result}
        except asyncio.TimeoutError:
            logger.warning(f"Tool {tool_name} timed out after {tool.timeout}s")
            return {"error": f"Tool {tool_name} timed out"}
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"error": str(e)}

    async def execute_all(
        self,
        tool_calls: List[Dict[str, Any]],
        permission_context: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """并行执行多个工具调用"""
        tasks = []
        for tc in tool_calls:
            fn_name = tc.get("function", {}).get("name", "")
            fn_args_str = tc.get("function", {}).get("arguments", "{}")
            try:
                fn_args = json.loads(fn_args_str) if isinstance(fn_args_str, str) else fn_args_str
            except json.JSONDecodeError:
                fn_args = {}
            tasks.append(self.execute(fn_name, fn_args, permission_context))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        tool_results = []
        for tc, result in zip(tool_calls, results):
            if isinstance(result, Exception):
                result = {"error": str(result)}
            tool_results.append({
                "tool_call_id": tc.get("id", ""),
                "name": tc.get("function", {}).get("name", ""),
                "result": result,
            })
        return tool_results


# ═══════════════════════════════════════════════════════════════
# 5. 核心循环 (~60 LOC) — 最重要的 60 行
# ═══════════════════════════════════════════════════════════════

class AgentLoop:
    """
    Agent OS 核心执行循环

    最简形式：
        while True:
            response = await model.call(messages, tools)
            if response.stop_reason == "end_turn": break
            results = await tool_engine.execute_all(response.tool_calls)
            messages += results
    """

    def __init__(
        self,
        model: ModelAdapter,
        tools: Optional[ToolEngine] = None,
        system_prompt: Optional[str] = None,
        pipeline: Optional[MessagePipeline] = None,
        max_iterations: int = 50,
    ):
        self.model = model
        self.tools = tools or ToolEngine()
        self.system_prompt = system_prompt
        self.pipeline = pipeline or MessagePipeline()
        self.max_iterations = max_iterations
        self._messages: List[Message] = []
        self._iteration = 0
        self._started_at: Optional[float] = None

    async def run(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[Message]]:
        """
        运行 Agent 循环

        返回: (最终回复, 完整消息历史)
        """
        self._iteration = 0
        self._started_at = time.time()

        # 添加用户消息
        self._messages.append(Message(role=MessageRole.USER, content=user_input))

        # 主循环
        while self._iteration < self.max_iterations:
            self._iteration += 1
            logger.debug(f"Agent loop iteration {self._iteration}")

            # 消息管道：预处理
            processed_msgs, sys_prompt = await self.pipeline.process_input(
                self._messages, self.system_prompt, context
            )

            # 调用模型
            try:
                response = await self.model.call(
                    messages=processed_msgs,
                    tools=self.tools.get_schemas() if self.tools else None,
                    system=sys_prompt,
                )
            except Exception as e:
                logger.error(f"Model call failed: {e}")
                error_msg = Message(
                    role=MessageRole.ASSISTANT,
                    content=f"I encountered an error: {str(e)}",
                )
                self._messages.append(error_msg)
                return error_msg.content, self._messages

            # 添加助手回复
            assistant_msg = Message(
                role=MessageRole.ASSISTANT,
                content=response.content,
                tool_calls=response.tool_calls,
            )
            self._messages.append(assistant_msg)

            # 判断停止原因
            if response.stop_reason == StopReason.END_TURN:
                logger.info(f"Agent loop completed after {self._iteration} iterations")
                return response.content, self._messages

            if response.stop_reason == StopReason.MAX_TOKENS:
                logger.warning("Hit max tokens limit")
                return response.content + "\n\n[Response truncated due to token limit]", self._messages

            # 执行工具调用
            if response.tool_calls and self.tools:
                tool_results = await self.tools.execute_all(response.tool_calls)

                # 将工具结果添加为消息
                for tr in tool_results:
                    self._messages.append(Message(
                        role=MessageRole.TOOL,
                        content=json.dumps(tr["result"], ensure_ascii=False),
                        tool_call_id=tr["tool_call_id"],
                        name=tr["name"],
                    ))

                # 消息管道：后处理
                response = await self.pipeline.process_output(response)
                continue

            # 没有工具调用且没有 end_turn — 安全退出
            break

        logger.warning(f"Agent loop hit max iterations ({self.max_iterations})")
        return response.content, self._messages

    @property
    def messages(self) -> List[Message]:
        return list(self._messages)

    @property
    def iteration_count(self) -> int:
        return self._iteration

    @property
    def elapsed(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at


# ═══════════════════════════════════════════════════════════════
# 6. 内置工具示例 (~20 LOC)
# ═══════════════════════════════════════════════════════════════

def create_default_tools() -> ToolEngine:
    """创建默认工具集"""
    engine = ToolEngine()

    async def web_search(query: str) -> str:
        """搜索网络（占位）"""
        return f"[Web search results for: {query}]"

    async def read_file(path: str) -> str:
        """读取文件（占位）"""
        return f"[File contents of: {path}]"

    async def run_command(command: str) -> str:
        """运行命令（占位，安全模式）"""
        return f"[Command output for: {command}]"

    engine.register(ToolDef(
        name="web_search",
        description="Search the web for current information",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
        handler=web_search,
    ))

    engine.register(ToolDef(
        name="read_file",
        description="Read a file from the filesystem",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
            },
            "required": ["path"],
        },
        handler=read_file,
        permission_level="user",
    ))

    engine.register(ToolDef(
        name="run_command",
        description="Execute a shell command (sandboxed)",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command"},
            },
            "required": ["command"],
        },
        handler=run_command,
        permission_level="admin",
    ))

    return engine
