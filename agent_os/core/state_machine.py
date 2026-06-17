"""
Agent OS — 核心引擎：状态机
===========================
所有任务和 Agent 的生命周期管理，支持 checkpoint/restore、超时、重试
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, TypeVar

logger = logging.getLogger("agent-os.core.state_machine")


class State(Enum):
    """通用状态定义"""
    PENDING = auto()       # 等待中
    INITIALIZING = auto()  # 初始化
    RUNNING = auto()       # 运行中
    PAUSED = auto()        # 暂停
    WAITING = auto()       # 等待外部输入
    COMPLETED = auto()     # 完成
    FAILED = auto()        # 失败
    CANCELLED = auto()     # 取消
    ROLLING_BACK = auto()  # 回滚中
    ROLLED_BACK = auto()   # 已回滚
    TIMEOUT = auto()       # 超时
    UNKNOWN = auto()       # 未知


# 状态转换矩阵：from_state -> set of allowed to_states
STATE_TRANSITIONS: Dict[State, Set[State]] = {
    State.PENDING:        {State.INITIALIZING, State.CANCELLED},
    State.INITIALIZING:   {State.RUNNING, State.FAILED, State.CANCELLED},
    State.RUNNING:        {State.COMPLETED, State.FAILED, State.PAUSED,
                           State.WAITING, State.CANCELLED, State.TIMEOUT},
    State.PAUSED:         {State.RUNNING, State.CANCELLED, State.FAILED},
    State.WAITING:        {State.RUNNING, State.CANCELLED, State.TIMEOUT},
    State.COMPLETED:      set(),
    State.FAILED:         {State.ROLLING_BACK},
    State.CANCELLED:      set(),
    State.ROLLING_BACK:   {State.ROLLED_BACK, State.FAILED},
    State.ROLLED_BACK:    set(),
    State.TIMEOUT:        {State.ROLLING_BACK},
    State.UNKNOWN:        {State.PENDING, State.CANCELLED},
}


class TransitionError(Exception):
    """非法状态转换"""
    pass


@dataclass
class StateMachineSnapshot:
    """状态机快照，用于 checkpoint/restore"""
    machine_id: str
    current_state: str
    context: Dict[str, Any]
    created_at: float
    version: int
    history: List[Dict[str, Any]]


class StateMachine:
    """
    通用状态机引擎

    特性：
    - 严格的状态转换验证
    - 超时自动转换
    - 状态进入/退出钩子
    - Checkpoint/Restore
    - 完整历史追踪
    """

    def __init__(
        self,
        machine_id: str = "",
        initial_state: State = State.PENDING,
        timeout: Optional[float] = None,
        on_timeout: Optional[State] = None,
    ):
        self.machine_id = machine_id or uuid.uuid4().hex[:12]
        self._state = initial_state
        self._initial_state = initial_state
        self._timeout = timeout
        self._on_timeout = on_timeout or State.TIMEOUT
        self._context: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []
        self._version = 0
        self._hooks: Dict[State, List[Callable]] = {
            s: [] for s in State
        }
        self._transition_hooks: List[Callable] = []
        self._lock = asyncio.Lock() if self._has_running_loop() else None
        self._timeout_task: Optional[asyncio.Task] = None
        self._started_at: Optional[float] = None

        self._record_history(initial_state, "init")

    @property
    def state(self) -> State:
        return self._state

    @property
    def elapsed(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    @property
    def context(self) -> Dict[str, Any]:
        return dict(self._context)

    @staticmethod
    def _has_running_loop() -> bool:
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

    async def _ensure_lock(self):
        if self._lock is None:
            self._lock = asyncio.Lock()

    # ── 状态转换 ──────────────────────────────────────

    async def transition(self, to_state: State, reason: str = "") -> bool:
        """尝试状态转换，返回是否成功"""
        await self._ensure_lock()
        async with self._lock:
            if to_state == self._state:
                return True

            if to_state not in STATE_TRANSITIONS.get(self._state, set()):
                raise TransitionError(
                    f"非法转换: {self._state.name} → {to_state.name}"
                )

            from_state = self._state
            self._state = to_state
            self._version += 1
            self._record_history(to_state, reason)

            # 执行进入钩子
            for hook in self._hooks.get(to_state, []):
                try:
                    await hook(self) if asyncio.iscoroutinefunction(hook) else hook(self)
                except Exception as e:
                    logger.error(f"状态钩子失败 [{to_state.name}]: {e}")

            # 执行转换钩子
            for hook in self._transition_hooks:
                try:
                    await hook(self, from_state, to_state, reason)
                except Exception as e:
                    logger.error(f"转换钩子失败 [{from_state.name}→{to_state.name}]: {e}")

            # 超时管理
            if to_state in (State.RUNNING, State.INITIALIZING):
                self._started_at = time.time()
                self._reset_timeout()
            elif to_state in (State.COMPLETED, State.FAILED, State.CANCELLED, State.TIMEOUT):
                self._cancel_timeout()

            logger.info(f"状态转换: {from_state.name} → {to_state.name} [{reason}]")
            return True

    async def run(self) -> bool:
        """快捷：PENDING → INITIALIZING → RUNNING"""
        if self._state == State.PENDING:
            await self.transition(State.INITIALIZING, "start")
            await self.transition(State.RUNNING, "ready")
        return True

    async def complete(self, result: Any = None) -> bool:
        """快捷：→ COMPLETED"""
        if result is not None:
            self._context["result"] = result
        return await self.transition(State.COMPLETED, "completed")

    async def fail(self, error: str = "") -> bool:
        """快捷：→ FAILED"""
        if error:
            self._context["error"] = error
        return await self.transition(State.FAILED, error or "failed")

    async def cancel(self, reason: str = "") -> bool:
        """快捷：→ CANCELLED"""
        return await self.transition(State.CANCELLED, reason or "cancelled")

    # ── 钩子管理 ──────────────────────────────────────

    def on_enter(self, state: State, hook: Callable):
        """注册状态进入钩子"""
        self._hooks.setdefault(state, []).append(hook)

    def on_transition(self, hook: Callable):
        """注册转换钩子"""
        self._transition_hooks.append(hook)

    # ── 超时管理 ──────────────────────────────────────

    def _reset_timeout(self):
        self._cancel_timeout()
        if self._timeout is not None and self._timeout > 0:
            self._timeout_task = asyncio.create_task(self._timeout_watcher())

    def _cancel_timeout(self):
        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()
            self._timeout_task = None

    async def _timeout_watcher(self):
        await asyncio.sleep(self._timeout)
        try:
            await self.transition(self._on_timeout, f"timeout after {self._timeout}s")
        except TransitionError:
            pass

    # ── Checkpoint / Restore ──────────────────────────

    def snapshot(self) -> StateMachineSnapshot:
        """创建快照"""
        return StateMachineSnapshot(
            machine_id=self.machine_id,
            current_state=self._state.name,
            context=dict(self._context),
            created_at=time.time(),
            version=self._version,
            history=list(self._history),
        )

    async def restore(self, snapshot: StateMachineSnapshot) -> bool:
        """从快照恢复"""
        await self._ensure_lock()
        async with self._lock:
            self._state = State[snapshot.current_state]
            self._context = dict(snapshot.context)
            self._version = snapshot.version
            self._history = list(snapshot.history)
            logger.info(f"状态机恢复: {self.machine_id} → {self._state.name} (v{self._version})")
            return True

    # ── 内部 ──────────────────────────────────────────

    def _record_history(self, state: State, reason: str):
        self._history.append({
            "state": state.name,
            "reason": reason,
            "timestamp": time.time(),
            "version": self._version,
        })

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.machine_id,
            "state": self._state.name,
            "version": self._version,
            "elapsed": self.elapsed,
            "history_count": len(self._history),
            "context_keys": list(self._context.keys()),
        }
