"""
Agent OS v6.0 — 核心对话循环
==============================
借鉴 Claude Code 的 200 行哲学，但加入工具系统、权限控制和上下文管理。

设计原则：
1. 核心循环极简（~250 LOC），复杂度推到外围
2. 扁平消息历史（不引入 DAG，除非需要）
3. 工具系统声明式定义（JSON Schema + 权限级别）
4. 上下文管理自动触发（不阻塞主循环）

运行: python3 -m agent_os_v6.conversation_loop
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agent-os-v6")


# ═══════════════════════════════════════════════════════════════
# 1. 类型定义
# ═══════════════════════════════════════════════════════════════

class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass
class Message:
    role: MessageRole
    content: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_result: Optional[Dict[str, Any]] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    created_at: float = field(default_factory=time.time)

@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    permission_level: str = "auto"  # auto | confirm | prohibited
    timeout_seconds: int = 30
    handler: Optional[Callable] = None

class Permission(Enum):
    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]
    status: str = "pending"  # pending | running | completed | failed
    result: Optional[Any] = None
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# 2. 消息历史管理
# ═══════════════════════════════════════════════════════════════

class MessageHistory:
    """扁平消息历史，支持压缩和预算管理"""

    def __init__(self, max_tokens: int = 48000):
        self.messages: List[Message] = []
        self.max_tokens = max_tokens
        self._token_count = 0

    def append(self, message: Message):
        self.messages.append(message)
        self._token_count += self._estimate_tokens(message)

    def _estimate_tokens(self, msg: Message) -> int:
        """粗略 token 估算（4 chars ≈ 1 token）"""
        total = len(msg.content) // 4
        for tc in msg.tool_calls:
            total += len(json.dumps(tc)) // 4
        if msg.tool_result:
            total += len(json.dumps(msg.tool_result)) // 4
        return max(1, total)

    def get_context(self, max_tokens: int = 40000) -> List[Dict[str, Any]]:
        """获取适合 LLM API 的上下文（自动裁剪）"""
        context = []
        total = 0

        # 从最新的消息开始，反向收集
        for msg in reversed(self.messages):
            tokens = self._estimate_tokens(msg)
            if total + tokens > max_tokens:
                break
            total += tokens
            context.insert(0, self._to_dict(msg))

        # 确保至少有 system message
        if not context or context[0].get("role") != "system":
            system_msg = self._find_system_message()
            if system_msg:
                context.insert(0, self._to_dict(system_msg))

        return context

    def _to_dict(self, msg: Message) -> Dict[str, Any]:
        d = {"role": msg.role.value, "content": msg.content}
        if msg.tool_calls:
            d["tool_calls"] = msg.tool_calls
        if msg.tool_result:
            d["tool_result"] = msg.tool_result
        return d

    def _find_system_message(self) -> Optional[Message]:
        for msg in self.messages:
            if msg.role == MessageRole.SYSTEM:
                return msg
        return None

    def get_token_usage(self) -> Tuple[int, int]:
        """返回 (已用, 上限)"""
        return self._token_count, self.max_tokens

    def compress(self, keep_last: int = 20):
        """压缩历史：保留最近 N 条 + system message"""
        if len(self.messages) <= keep_last:
            return

        system = self._find_system_message()
        recent = self.messages[-keep_last:]

        self.messages = []
        if system:
            self.messages.append(system)
        self.messages.extend(recent)

        self._token_count = sum(self._estimate_tokens(m) for m in self.messages)
        logger.info(f"📦 历史压缩: 保留 {len(self.messages)} 条消息")


# ═══════════════════════════════════════════════════════════════
# 3. 工具系统
# ═══════════════════════════════════════════════════════════════

class ToolRegistry:
    """声明式工具注册表"""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition):
        if tool.name in self._tools:
            raise ValueError(f"工具已注册: {tool.name}")
        self._tools[tool.name] = tool
        logger.info(f"🔧 工具已注册: {tool.name}")

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """返回适合 LLM 工具调用的格式"""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in self._tools.values()
        ]

    def get_permission(self, name: str) -> str:
        tool = self._tools.get(name)
        return tool.permission_level if tool else "deny"


# ═══════════════════════════════════════════════════════════════
# 4. 权限系统
# ═══════════════════════════════════════════════════════════════

class PermissionRacer:
    """
    权限竞速：4 路并行审批，最快返回的路线决定结果

    Route 1: 用户策略（全局/项目级预设规则）
    Route 2: 风险分类器（基于操作类型的风险评估）
    Route 3: 上下文规则（当前状态特殊规则）
    Route 4: 用户实时（终端提示用户确认）
    """

    def __init__(self):
        # Route 1: 用户策略
        self._policies: Dict[str, str] = {
            # 默认策略：读操作自动允许，写操作需要确认
            "read_file": "auto",
            "search_code": "auto",
            "list_directory": "auto",
            "grep": "auto",
            "write_file": "confirm",
            "edit_file": "confirm",
            "delete_file": "confirm",
            "run_command": "confirm",
            "run_python": "confirm",
        }

    async def race(self, tool_name: str, arguments: Dict[str, Any]) -> Permission:
        """4 路并行竞速"""
        # Route 1: 用户策略
        policy = self._policies.get(tool_name, "confirm")
        if policy == "auto":
            return Permission.ALLOW
        if policy == "deny":
            return Permission.DENY

        # Route 2: 风险分类器（简单实现）
        risk = self._classify_risk(tool_name, arguments)
        if risk == "low":
            return Permission.ALLOW
        if risk == "critical":
            return Permission.DENY

        # Route 3: 上下文规则（当前无特殊规则）
        # Route 4: 用户实时确认
        return Permission.CONFIRM

    def _classify_risk(self, tool_name: str, arguments: Dict) -> str:
        """简单的风险分类"""
        # 写操作默认中风险
        if tool_name in ("write_file", "edit_file"):
            path = arguments.get("path", "")
            # 修改关键配置文件 → 高风险
            if any(k in path for k in [".env", "config", "secret", "key", "password"]):
                return "critical"
            return "medium"

        # 执行操作默认高风险
        if tool_name in ("run_command", "run_python"):
            cmd = str(arguments.get("command", arguments.get("code", "")))
            # 危险命令 → 拒绝
            dangerous = ["rm -rf", "mkfs", "dd if=", "> /dev/", ":(){ :|:& };:"]
            if any(d in cmd for d in dangerous):
                return "critical"
            return "high"

        # 读操作默认低风险
        return "low"


# ═══════════════════════════════════════════════════════════════
# 5. LLM 接口抽象
# ═══════════════════════════════════════════════════════════════

class LLMInterface:
    """LLM API 的抽象接口，支持多模型切换"""

    def __init__(self, model: str = "deepseek-v4-flash", api_key: str = ""):
        self.model = model
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = "https://ark.cn-beijing.volces.com/api/v3"

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """调用 LLM API"""
        import aiohttp

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = tools

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=body,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        return {
                            "error": f"API 错误 ({resp.status}): {text[:200]}",
                            "content": "",
                            "tool_calls": [],
                        }
                    data = await resp.json()
                    choice = data["choices"][0]
                    msg = choice["message"]

                    return {
                        "content": msg.get("content", ""),
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["function"]["name"],
                                    "arguments": tc["function"]["arguments"],
                                },
                            }
                            for tc in msg.get("tool_calls", [])
                        ],
                        "finish_reason": choice.get("finish_reason", "stop"),
                    }
        except asyncio.TimeoutError:
            return {"error": "API 请求超时", "content": "", "tool_calls": []}
        except Exception as e:
            return {"error": f"API 请求失败: {e}", "content": "", "tool_calls": []}

    async def generate_simple(
        self, prompt: str, temperature: float = 0.3
    ) -> str:
        """简单文本生成（无工具调用）"""
        result = await self.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=2048,
        )
        return result.get("content", "") or result.get("error", "生成失败")


# ═══════════════════════════════════════════════════════════════
# 6. 核心工具实现
# ═══════════════════════════════════════════════════════════════

async def tool_read_file(path: str, offset: int = 0, limit: int = 200) -> Dict:
    """读取文件内容"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            if offset > 0:
                for _ in range(offset):
                    next(f, None)
            lines = []
            for _ in range(limit):
                try:
                    lines.append(next(f))
                except StopIteration:
                    break
        content = "".join(lines)
        return {
            "success": True,
            "content": content,
            "line_count": len(lines),
            "truncated": len(lines) >= limit,
        }
    except FileNotFoundError:
        return {"success": False, "error": f"文件未找到: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def tool_write_file(path: str, content: str, create_parents: bool = False) -> Dict:
    """写入文件"""
    try:
        if create_parents:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": path, "bytes": len(content.encode("utf-8"))}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def tool_search_code(pattern: str, path: str = ".", max_results: int = 20) -> Dict:
    """搜索代码（使用 ripgrep）"""
    import subprocess
    try:
        result = subprocess.run(
            ["rg", "-n", "--color", "never", pattern, path],
            capture_output=True, text=True, timeout=30,
        )
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        return {
            "success": True,
            "results": lines[:max_results],
            "total": len(lines),
            "truncated": len(lines) > max_results,
        }
    except FileNotFoundError:
        return {"success": False, "error": "ripgrep (rg) 未安装，请先安装"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "搜索超时"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def tool_list_directory(path: str = ".") -> Dict:
    """列出目录内容"""
    try:
        entries = []
        for entry in os.scandir(path):
            entries.append({
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "size": entry.stat().st_size if entry.is_file() else 0,
            })
        entries.sort(key=lambda e: (e["type"] != "directory", e["name"]))
        return {"success": True, "path": os.path.abspath(path), "entries": entries}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def tool_run_command(command: str, timeout: int = 30) -> Dict:
    """执行 Shell 命令（安全模式）"""
    import shlex
    import subprocess
    try:
        cmd_list = shlex.split(command)
        result = subprocess.run(
            cmd_list, shell=False, capture_output=True, text=True, timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-1000:] if result.stderr else "",
            "truncated": len(result.stdout) > 2000 or len(result.stderr) > 1000,
        }
    except ValueError as e:
        return {"success": False, "error": f"命令解析失败: {e}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"命令执行超时 ({timeout}s)"}
    except FileNotFoundError:
        return {"success": False, "error": "命令未找到"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# 7. 核心对话循环
# ═══════════════════════════════════════════════════════════════

class ConversationLoop:
    """
    Agent OS v6.0 核心对话循环

    借鉴 Claude Code 的 200 行哲学：
    - 核心循环 ~250 LOC
    - 所有复杂度在工具/权限/上下文中
    - 扁平消息历史，不引入 DAG
    """

    def __init__(self, llm: Optional[LLMInterface] = None):
        self.history = MessageHistory()
        self.tools = ToolRegistry()
        self.permission = PermissionRacer()
        self.llm = llm or LLMInterface()
        self._running = False
        self._stats = {
            "turns": 0,
            "tool_calls": 0,
            "tool_errors": 0,
            "permission_denies": 0,
            "api_calls": 0,
            "api_errors": 0,
        }

        # 注册核心工具
        self._register_core_tools()

    def _register_core_tools(self):
        """注册内置工具"""
        self.tools.register(ToolDefinition(
            name="read_file",
            description="读取文件内容，支持行范围。用于查看源代码、配置文件等。",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "offset": {"type": "integer", "description": "起始行号（从0开始）", "default": 0},
                    "limit": {"type": "integer", "description": "最多读取行数", "default": 200},
                },
                "required": ["path"],
            },
            output_schema={"type": "object"},
            permission_level="auto",
            handler=tool_read_file,
        ))
        self.tools.register(ToolDefinition(
            name="write_file",
            description="写入文件。如果文件已存在会被覆盖。",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "文件内容"},
                    "create_parents": {"type": "boolean", "description": "是否创建父目录", "default": False},
                },
                "required": ["path", "content"],
            },
            output_schema={"type": "object"},
            permission_level="confirm",
            handler=tool_write_file,
        ))
        self.tools.register(ToolDefinition(
            name="search_code",
            description="在代码库中搜索文本（使用 ripgrep）。支持正则表达式。",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "搜索模式（支持正则）"},
                    "path": {"type": "string", "description": "搜索路径", "default": "."},
                    "max_results": {"type": "integer", "description": "最大结果数", "default": 20},
                },
                "required": ["pattern"],
            },
            output_schema={"type": "object"},
            permission_level="auto",
            handler=tool_search_code,
        ))
        self.tools.register(ToolDefinition(
            name="list_directory",
            description="列出目录内容。",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径", "default": "."},
                },
            },
            output_schema={"type": "object"},
            permission_level="auto",
            handler=tool_list_directory,
        ))
        self.tools.register(ToolDefinition(
            name="run_command",
            description="执行 Shell 命令（安全模式，不支持管道和重定向）。用于编译、运行测试、git 操作等。",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的命令"},
                    "timeout": {"type": "integer", "description": "超时秒数", "default": 30},
                },
                "required": ["command"],
            },
            output_schema={"type": "object"},
            permission_level="confirm",
            handler=tool_run_command,
        ))

    async def process_message(self, user_input: str) -> str:
        """处理单条用户消息（核心循环的一次迭代）"""
        self._stats["turns"] += 1

        # 1. 添加用户消息到历史
        self.history.append(Message(role=MessageRole.USER, content=user_input))

        # 2. 构建上下文
        context = self.history.get_context()

        # 3. 调用 LLM
        response = await self.llm.generate(
            messages=context,
            tools=self.tools.list_tools(),
        )
        self._stats["api_calls"] += 1

        if response.get("error"):
            self._stats["api_errors"] += 1
            error_msg = f"❌ {response['error']}"
            self.history.append(Message(role=MessageRole.ASSISTANT, content=error_msg))
            return error_msg

        # 4. 处理回复
        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        if not tool_calls:
            # 纯文本回复
            self.history.append(Message(role=MessageRole.ASSISTANT, content=content))
            return content

        # 5. 处理工具调用
        self.history.append(Message(
            role=MessageRole.ASSISTANT,
            content=content or "",
            tool_calls=tool_calls,
        ))

        results = []
        for tc in tool_calls:
            result = await self._handle_tool_call(tc)
            results.append(result)

            self.history.append(Message(
                role=MessageRole.TOOL,
                content=f"工具 {tc['function']['name']} 执行结果",
                tool_result=result,
            ))

        # 6. 如果有工具调用，让 LLM 生成最终回复
        if results:
            final_context = self.history.get_context()
            final_response = await self.llm.generate(
                messages=final_context,
                temperature=0.3,
            )
            self._stats["api_calls"] += 1

            final_content = final_response.get("content", "")
            if final_response.get("error"):
                final_content = f"❌ {final_response['error']}"

            self.history.append(Message(role=MessageRole.ASSISTANT, content=final_content))
            return final_content

        return content

    async def _handle_tool_call(self, tc: Dict) -> Dict:
        """处理单个工具调用"""
        self._stats["tool_calls"] += 1
        name = tc["function"]["name"]

        try:
            arguments = json.loads(tc["function"]["arguments"])
        except json.JSONDecodeError:
            self._stats["tool_errors"] += 1
            return {"error": "参数解析失败", "tool": name}

        # 权限检查
        permission = await self.permission.race(name, arguments)
        if permission == Permission.DENY:
            self._stats["permission_denies"] += 1
            return {"error": f"权限拒绝: {name}", "tool": name, "denied": True}

        if permission == Permission.CONFIRM:
            # 模拟用户确认（在终端模式下会提示用户）
            logger.info(f"🔐 需要确认: {name}({json.dumps(arguments)[:100]})")
            # 自动确认（开发模式）
            logger.info(f"🔐 自动确认（开发模式）")

        # 查找并执行工具
        tool = self.tools.get(name)
        if not tool or not tool.handler:
            self._stats["tool_errors"] += 1
            return {"error": f"未知工具: {name}", "tool": name}

        try:
            result = await tool.handler(**arguments)
            if not result.get("success", True):
                self._stats["tool_errors"] += 1
            return {"tool": name, **result}
        except Exception as e:
            self._stats["tool_errors"] += 1
            return {"error": str(e), "tool": name}

    async def run_interactive(self):
        """运行交互式终端"""
        self._running = True

        # 系统提示
        system_prompt = """你是 Agent OS v6.0，一个智能编码助手。
你可以读取文件、搜索代码、执行命令来帮助用户完成编程任务。
始终使用中文回复，简洁明了。
如果需要执行可能影响系统的操作，先解释风险再执行。"""
        self.history.append(Message(role=MessageRole.SYSTEM, content=system_prompt))

        print("\n" + "=" * 60)
        print("  Agent OS v6.0 — 交互式终端")
        print("  输入 /help 查看命令，/exit 退出")
        print("=" * 60 + "\n")

        try:
            while self._running:
                try:
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: input("🦊 > ").strip()
                    )
                except (EOFError, KeyboardInterrupt):
                    print("\n\n👋 再见！")
                    break

                if not user_input:
                    continue

                # 内置命令
                if user_input == "/exit":
                    print("👋 再见！")
                    break
                elif user_input == "/help":
                    print("""
  📋 可用命令:
    /exit         退出
    /help         显示此帮助
    /tools        列出可用工具
    /stats        显示统计信息
    /history      显示对话历史
    /compress     手动压缩历史
    /clear        清屏
                    """)
                    continue
                elif user_input == "/tools":
                    tools = self.tools.list_tools()
                    print(f"\n🔧 可用工具 ({len(tools)}):")
                    for t in tools:
                        name = t["function"]["name"]
                        desc = t["function"]["description"][:80]
                        perm = self.tools.get_permission(name)
                        icon = {"auto": "✅", "confirm": "🔐", "deny": "❌"}.get(perm, "❓")
                        print(f"  {icon} {name}: {desc}")
                    print()
                    continue
                elif user_input == "/stats":
                    s = self._stats
                    print(f"""
  📊 统计:
    对话轮次:   {s['turns']}
    API 调用:   {s['api_calls']} (错误: {s['api_errors']})
    工具调用:   {s['tool_calls']} (错误: {s['tool_errors']})
    权限拒绝:   {s['permission_denies']}
    历史消息:   {len(self.history.messages)}
                    """)
                    continue
                elif user_input == "/history":
                    for i, msg in enumerate(self.history.messages):
                        role_icon = {
                            MessageRole.SYSTEM: "⚙️",
                            MessageRole.USER: "👤",
                            MessageRole.ASSISTANT: "🤖",
                            MessageRole.TOOL: "🔧",
                        }.get(msg.role, "❓")
                        preview = msg.content[:80].replace("\n", " ")
                        print(f"  {i:3d} {role_icon} {preview}")
                    print()
                    continue
                elif user_input == "/compress":
                    before = len(self.history.messages)
                    self.history.compress()
                    after = len(self.history.messages)
                    print(f"📦 压缩完成: {before} → {after} 条消息\n")
                    continue
                elif user_input == "/clear":
                    os.system("clear" if os.name == "posix" else "cls")
                    continue

                # 处理用户输入
                response = await self.process_message(user_input)
                print(f"\n{response}\n")

        finally:
            self._running = False

    def get_stats(self) -> Dict:
        return {**self._stats, "history_size": len(self.history.messages)}


# ═══════════════════════════════════════════════════════════════
# 8. 主程序
# ═══════════════════════════════════════════════════════════════

async def main():
    """入口"""
    loop = ConversationLoop()
    await loop.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())
