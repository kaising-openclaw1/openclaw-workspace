"""
Agent OS — 核心引擎：主控制器
============================
将所有子系统整合为统一的 Agent 操作系统
"""

import asyncio
import logging
import os
import signal
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .event_bus import EventBus, Event, EventPriority, EventCategory
from .state_machine import StateMachine, State
from .plugin_system import PluginRegistry, PluginBase

logger = logging.getLogger("agent-os.core.engine")


@dataclass
class AgentOSConfig:
    """Agent OS 全局配置"""
    node_name: str = ""
    data_dir: str = "~/.agent-os"
    log_dir: str = "~/.agent-os/logs"
    listen_host: str = "0.0.0.0"
    listen_port: int = 8765
    seed_nodes: List[str] = field(default_factory=list)
    enable_mesh: bool = True
    enable_security: bool = True
    enable_observability: bool = True
    plugin_dirs: List[str] = field(default_factory=list)
    max_workers: int = 10
    task_timeout: float = 300.0
    auto_discover_plugins: bool = True
    debug: bool = False


class AgentOSEngine:
    """
    Agent OS 主引擎

    整合所有子系统：
    - 事件总线（通信骨架）
    - 状态机（生命周期）
    - 插件系统（能力扩展）
    - Mesh 网络（多机互联）
    - 安全飞地（源码保护）
    - 智力路由（模型选择）
    - 资源管理（算力抽象）
    - 可观测性（追踪/指标/日志）
    """

    def __init__(self, config: AgentOSConfig):
        self.config = config
        self.node_id = uuid.uuid4().hex[:12]
        self._running = False
        self._started_at: Optional[float] = None

        # 核心子系统
        self.event_bus = EventBus()
        self.state_machine = StateMachine(
            machine_id=f"engine-{self.node_id}",
            initial_state=State.PENDING,
        )
        self.plugin_registry = PluginRegistry(plugin_dirs=config.plugin_dirs)

        # 可选子系统（延迟初始化）
        self._mesh = None
        self._enclave = None
        self._intelligence_router = None
        self._resource_manager = None
        self._tracer = None
        self._metrics = None
        self._structured_logger = None

        # 任务管理
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._task_queues: Dict[int, asyncio.Queue] = {
            p: asyncio.Queue(maxsize=1000) for p in range(10)
        }
        self._workers: List[asyncio.Task] = []

        # 生命周期钩子
        self._startup_hooks: List[Callable] = []
        self._shutdown_hooks: List[Callable] = []

        # 事件订阅 ID 列表
        self._subscriptions: List[str] = []

    # ── 生命周期 ──────────────────────────────────────

    async def start(self):
        """启动 Agent OS"""
        if self._running:
            return

        self._running = True
        self._started_at = time.time()

        logger.info(f"🚀 Agent OS 启动中... (node={self.node_id})")

        # 1. 启动事件总线
        self.event_bus.start()
        self._subscribe_system_events()

        # 2. 初始化可选子系统
        await self._init_subsystems()

        # 3. 发现并加载插件
        if self.config.auto_discover_plugins:
            await self._load_plugins()

        # 4. 启动工作线程
        await self._start_workers()

        # 5. 状态机就绪
        await self.state_machine.run()

        # 6. 执行启动钩子
        for hook in self._startup_hooks:
            try:
                await hook(self)
            except Exception as e:
                logger.error(f"启动钩子失败: {e}")

        # 7. 发送启动事件
        await self.event_bus.emit(
            "system.started",
            payload={
                "node_id": self.node_id,
                "version": "0.1.0",
                "config": {
                    "mesh": self.config.enable_mesh,
                    "security": self.config.enable_security,
                    "observability": self.config.enable_observability,
                },
            },
            category=EventCategory.SYSTEM,
            priority=EventPriority.CRITICAL,
        )

        logger.info(f"✅ Agent OS 已就绪 ({self._get_uptime():.1f}s)")

    async def shutdown(self, reason: str = "user_request"):
        """关闭 Agent OS"""
        logger.info(f"🛑 Agent OS 关闭中... ({reason})")

        await self.state_machine.transition(State.CANCELLED, reason)

        # 执行关闭钩子
        for hook in self._shutdown_hooks:
            try:
                await hook(self)
            except Exception as e:
                logger.error(f"关闭钩子失败: {e}")

        # 关闭子系统
        if self._mesh:
            await self._mesh.stop()
        if self._enclave:
            await self._enclave.shutdown()

        # 停止工作线程
        for w in self._workers:
            w.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

        # 取消订阅
        for sub_id in self._subscriptions:
            self.event_bus.unsubscribe(sub_id)

        # 停止事件总线
        await self.event_bus.stop()

        # 刷新日志
        if self._structured_logger:
            self._structured_logger.flush()

        self._running = False
        logger.info("👋 Agent OS 已关闭")

    # ── 子系统初始化 ──────────────────────────────────

    async def _init_subsystems(self):
        """初始化可选子系统"""
        tasks = []

        # 可观测性
        if self.config.enable_observability:
            from agent_os.observability import Tracer, MetricsCollector, StructuredLogger
            self._tracer = Tracer()
            self._tracer.set_event_bus(self.event_bus)
            self._metrics = MetricsCollector()
            self._metrics.set_event_bus(self.event_bus)
            self._structured_logger = StructuredLogger(
                log_dir=os.path.expanduser(self.config.log_dir)
            )
            self._structured_logger.set_event_bus(self.event_bus)
            logger.info("📊 可观测性已初始化")

        # Mesh 网络
        if self.config.enable_mesh:
            from agent_os.network.mesh import MeshNetwork, MeshConfig, NodeRole
            mesh_config = MeshConfig(
                node_name=self.config.node_name or f"node-{self.node_id[:6]}",
                listen_host=self.config.listen_host,
                listen_port=self.config.listen_port,
                seed_nodes=self.config.seed_nodes,
            )
            self._mesh = MeshNetwork(mesh_config)
            self._mesh.set_event_bus(self.event_bus)
            tasks.append(self._mesh.start())
            logger.info("🔗 Mesh 网络已初始化")

        # 安全飞地
        if self.config.enable_security:
            from agent_os.security.enclave import SecurityEnclave
            self._enclave = SecurityEnclave(
                data_dir=os.path.join(os.path.expanduser(self.config.data_dir), "enclave")
            )
            self._enclave.set_event_bus(self.event_bus)
            logger.info("🔒 安全飞地已初始化")

        # 智力路由
        from agent_os.intelligence.router import IntelligenceRouter
        self._intelligence_router = IntelligenceRouter()
        self._intelligence_router.set_event_bus(self.event_bus)
        logger.info("🧠 智力路由已初始化")

        # 资源管理
        from agent_os.compute.resource_manager import ResourceManager, LocalProvider
        self._resource_manager = ResourceManager()
        self._resource_manager.set_event_bus(self.event_bus)
        await self._resource_manager.register_provider(LocalProvider())
        await self._resource_manager.start_monitoring()
        logger.info("💻 资源管理已初始化")

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    logger.error(f"子系统初始化失败: {r}")

    async def _load_plugins(self):
        """发现并加载插件"""
        plugin_dirs = self.config.plugin_dirs or [
            os.path.join(os.path.expanduser(self.config.data_dir), "plugins"),
        ]
        self.plugin_registry.set_event_bus(self.event_bus)

        discovered = await self.plugin_registry.discover(plugin_dirs)
        for name in discovered:
            await self.plugin_registry.load(name)

        started = await self.plugin_registry.start_all()
        if started:
            logger.info(f"🔌 已加载 {started} 个插件")

    async def _start_workers(self):
        """启动任务工作线程"""
        for i in range(self.config.max_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker)
        logger.info(f"👷 已启动 {self.config.max_workers} 个工作线程")

    async def _worker_loop(self, worker_id: int):
        """工作线程循环"""
        logger.debug(f"Worker-{worker_id} 就绪")
        while self._running:
            processed = False
            for priority in range(10):
                try:
                    task_data = self._task_queues[priority].get_nowait()
                    await self._execute_task(task_data)
                    processed = True
                    break
                except asyncio.QueueEmpty:
                    continue
            if not processed:
                await asyncio.sleep(0.05)

    # ── 系统事件订阅 ──────────────────────────────────

    def _subscribe_system_events(self):
        """订阅系统级事件"""
        subs = []

        async def on_task_created(event: Event):
            task_data = event.payload
            priority = min(task_data.get("priority", 5), 9)
            try:
                await self._task_queues[priority].put(task_data)
            except asyncio.QueueFull:
                logger.warning(f"任务队列满，丢弃: {task_data.get('id', 'unknown')}")

        sub_id = self.event_bus.subscribe("task.*", on_task_created)
        subs.append(sub_id)

        self._subscriptions = subs

    # ── 任务管理 ──────────────────────────────────────

    async def submit_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: int = 5,
        timeout: Optional[float] = None,
    ) -> str:
        """提交任务"""
        task_id = uuid.uuid4().hex[:12]
        task_data = {
            "id": task_id,
            "type": task_type,
            "payload": payload,
            "priority": priority,
            "timeout": timeout or self.config.task_timeout,
            "created_at": time.time(),
            "status": "pending",
        }
        self._tasks[task_id] = task_data

        await self.event_bus.emit(
            "task.created",
            payload=task_data,
            category=EventCategory.TASK,
        )

        if self._metrics:
            self._metrics.increment("tasks.submitted")

        return task_id

    async def _execute_task(self, task_data: Dict[str, Any]):
        """执行任务"""
        task_id = task_data["id"]
        self._tasks[task_id]["status"] = "running"

        # 创建追踪跨度
        span = None
        if self._tracer:
            span = self._tracer.start_span(
                name=f"task:{task_data['type']}",
                category="task",
                tags={"task_id": task_id, "type": task_data["type"]},
            )

        try:
            # 执行任务（带超时）
            result = await asyncio.wait_for(
                self._dispatch_task(task_data),
                timeout=task_data["timeout"],
            )
            self._tasks[task_id]["status"] = "completed"
            self._tasks[task_id]["result"] = result

            if span:
                self._tracer.end_span(span.id)

            await self.event_bus.emit(
                "task.completed",
                payload={"task_id": task_id, "result": result},
                category=EventCategory.TASK,
            )

            if self._metrics:
                self._metrics.increment("tasks.completed")

        except asyncio.TimeoutError:
            self._tasks[task_id]["status"] = "timeout"
            if span:
                self._tracer.end_span(span.id, SpanStatus.TIMEOUT, "timeout")

            await self.event_bus.emit(
                "task.timeout",
                payload={"task_id": task_id},
                category=EventCategory.TASK,
            )

        except Exception as e:
            self._tasks[task_id]["status"] = "failed"
            self._tasks[task_id]["error"] = str(e)
            if span:
                self._tracer.end_span(span.id, SpanStatus.ERROR, str(e))

            await self.event_bus.emit(
                "task.failed",
                payload={"task_id": task_id, "error": str(e)},
                category=EventCategory.TASK,
            )

            if self._metrics:
                self._metrics.increment("tasks.failed")

    async def _dispatch_task(self, task_data: Dict[str, Any]) -> Any:
        """分发任务到对应的处理器"""
        task_type = task_data["type"]

        # 检查插件中是否有对应工具
        tool = self.plugin_registry.get_tool(task_type)
        if tool:
            return await tool.handler(**task_data["payload"])

        # 内置任务类型
        handlers = {
            "ping": lambda p: {"status": "pong", "node": self.node_id},
            "status": lambda p: self.get_status(),
            "execute": self._handle_execute,
            "route": self._handle_route,
        }

        handler = handlers.get(task_type)
        if handler:
            return await handler(task_data["payload"])

        raise ValueError(f"未知任务类型: {task_type}")

    async def _handle_execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """执行命令（安全模式：shell=False）"""
        import shlex
        import subprocess
        command = payload.get("command", "")
        timeout = payload.get("timeout", 30)

        try:
            cmd_list = shlex.split(command)
            result = subprocess.run(
                cmd_list, shell=False, capture_output=True, text=True,
                timeout=timeout,
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"exit_code": -1, "stdout": "", "stderr": "Timeout"}
        except Exception as e:
            return {"exit_code": -1, "stdout": "", "stderr": str(e)}

    async def _handle_route(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """路由到最优模型"""
        if not self._intelligence_router:
            return {"error": "intelligence router not available"}

        from agent_os.intelligence.router import TaskProfile, TaskComplexity
        task = TaskProfile(
            type=payload.get("type", "generic"),
            description=payload.get("description", ""),
            estimated_input_tokens=payload.get("input_tokens", 1000),
            estimated_output_tokens=payload.get("output_tokens", 500),
            requires_tools=payload.get("requires_tools", False),
            requires_vision=payload.get("requires_vision", False),
            priority=payload.get("priority", 5),
        )

        decision = self._intelligence_router.route(task)
        return {
            "model": decision.selected_model,
            "provider": decision.selected_provider,
            "level": decision.intelligence_level.name,
            "cost": decision.estimated_cost,
            "latency_ms": decision.estimated_latency,
            "reason": decision.reason,
            "alternatives": decision.alternatives,
            "confidence": decision.confidence,
        }

    # ── 查询 ──────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            "node_id": self.node_id,
            "running": self._running,
            "uptime": self._get_uptime(),
            "state": self.state_machine.state.name,
            "tasks": {
                "total": len(self._tasks),
                "pending": sum(1 for t in self._tasks.values() if t["status"] == "pending"),
                "running": sum(1 for t in self._tasks.values() if t["status"] == "running"),
                "completed": sum(1 for t in self._tasks.values() if t["status"] == "completed"),
                "failed": sum(1 for t in self._tasks.values() if t["status"] == "failed"),
            },
            "subsystems": {
                "mesh": self._mesh is not None,
                "enclave": self._enclave is not None,
                "router": self._intelligence_router is not None,
                "resource_manager": self._resource_manager is not None,
                "tracer": self._tracer is not None,
                "metrics": self._metrics is not None,
            },
            "plugins": self.plugin_registry.list_plugins(),
            "event_bus": self.event_bus.get_stats(),
        }

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        return tasks

    # ── 辅助 ──────────────────────────────────────────

    def _get_uptime(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    def on_startup(self, hook: Callable):
        """注册启动钩子"""
        self._startup_hooks.append(hook)

    def on_shutdown(self, hook: Callable):
        """注册关闭钩子"""
        self._shutdown_hooks.append(hook)

    @property
    def mesh(self):
        return self._mesh

    @property
    def enclave(self):
        return self._enclave

    @property
    def intelligence_router(self):
        return self._intelligence_router

    @property
    def resource_manager(self):
        return self._resource_manager

    @property
    def tracer(self):
        return self._tracer

    @property
    def metrics(self):
        return self._metrics

    @property
    def structured_logger(self):
        return self._structured_logger
