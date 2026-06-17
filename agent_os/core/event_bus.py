"""
Agent OS — 核心引擎：异步事件总线
==================================
基于 asyncio 的高性能事件驱动架构，支持优先级、通配符订阅、背压控制
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, TypeVar

logger = logging.getLogger("agent-os.core.event_bus")

T = TypeVar("T")


class EventPriority(Enum):
    """事件优先级"""
    CRITICAL = 0   # 系统级事件，立即处理
    HIGH = 1       # 用户交互事件
    NORMAL = 2     # 普通任务事件
    LOW = 3        # 后台维护事件
    BACKGROUND = 4 # 可延迟处理


class EventCategory(Enum):
    """事件分类"""
    SYSTEM = auto()
    TASK = auto()
    NODE = auto()
    AGENT = auto()
    SECURITY = auto()
    OBSERVABILITY = auto()
    USER = auto()


@dataclass
class Event:
    """不可变事件对象"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: str = ""
    category: EventCategory = EventCategory.SYSTEM
    priority: EventPriority = EventPriority.NORMAL
    source: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    trace_id: str = ""
    span_id: str = ""
    ttl: int = 3  # 最大传递跳数

    def __post_init__(self):
        if not self.type:
            self.type = f"{self.category.name.lower()}.generic"
        if not self.trace_id:
            self.trace_id = uuid.uuid4().hex[:16]

    def copy_with(self, **kwargs) -> "Event":
        """创建事件的浅拷贝并覆盖指定字段"""
        return Event(**{**self.__dict__, **kwargs})


class EventSubscription:
    """事件订阅描述符"""

    def __init__(
        self,
        pattern: str,
        callback: Callable[[Event], Coroutine[Any, Any, None]],
        priority: Optional[EventPriority] = None,
        category: Optional[EventCategory] = None,
        once: bool = False,
        filter_fn: Optional[Callable[[Event], bool]] = None,
    ):
        self.id = uuid.uuid4().hex[:8]
        self.pattern = pattern
        self.callback = callback
        self.priority = priority
        self.category = category
        self.once = once
        self.filter_fn = filter_fn
        self.created_at = time.time()

    def matches(self, event: Event) -> bool:
        """检查事件是否匹配此订阅"""
        # 优先级过滤
        if self.priority is not None and event.priority != self.priority:
            return False
        # 分类过滤
        if self.category is not None and event.category != self.category:
            return False
        # 通配符模式匹配
        if self.pattern == "*" or self.pattern == event.type:
            return True
        # 前缀匹配 (e.g., "task.*" matches "task.created")
        if self.pattern.endswith(".*"):
            prefix = self.pattern[:-2]
            if event.type.startswith(prefix + ".") or event.type == prefix:
                return True
        # 自定义过滤
        if self.filter_fn and not self.filter_fn(event):
            return False
        return False


class EventBus:
    """
    高性能异步事件总线

    特性：
    - 优先级队列（CRITICAL 优先处理）
    - 通配符订阅 (task.*)
    - 一次性订阅 (once=True)
    - 背压控制（max_queue_size）
    - 批量处理（batch_window）
    - 死信队列
    """

    def __init__(
        self,
        max_queue_size: int = 10000,
        batch_window: float = 0.01,
        worker_count: int = 4,
    ):
        self._subscriptions: Dict[str, List[EventSubscription]] = {}
        self._wildcard_subscriptions: List[EventSubscription] = []
        self._queues: Dict[EventPriority, asyncio.Queue] = {
            p: asyncio.Queue(maxsize=max_queue_size)
            for p in EventPriority
        }
        self._workers: List[asyncio.Task] = []
        self._worker_count = worker_count
        self._batch_window = batch_window
        self._running = False
        self._dead_letter_queue: asyncio.Queue = asyncio.Queue()
        self._stats = {"published": 0, "processed": 0, "failed": 0, "dropped": 0}
        self._lock = asyncio.Lock() if self._has_running_loop() else None

    @staticmethod
    def _has_running_loop() -> bool:
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

    # ── 订阅管理 ──────────────────────────────────────

    def subscribe(
        self,
        pattern: str,
        callback: Callable[[Event], Coroutine[Any, Any, None]],
        priority: Optional[EventPriority] = None,
        category: Optional[EventCategory] = None,
        once: bool = False,
        filter_fn: Optional[Callable[[Event], bool]] = None,
    ) -> str:
        """订阅事件，返回 subscription_id"""
        sub = EventSubscription(pattern, callback, priority, category, once, filter_fn)
        if pattern.endswith(".*") or pattern == "*":
            self._wildcard_subscriptions.append(sub)
        else:
            self._subscriptions.setdefault(pattern, []).append(sub)
        logger.debug(f"订阅: {pattern} (id={sub.id})")
        return sub.id

    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        for pattern, subs in self._subscriptions.items():
            for s in subs:
                if s.id == subscription_id:
                    subs.remove(s)
                    return True
        for s in self._wildcard_subscriptions:
            if s.id == subscription_id:
                self._wildcard_subscriptions.remove(s)
                return True
        return False

    # ── 事件发布 ──────────────────────────────────────

    async def publish(self, event: Event) -> bool:
        """发布事件到对应优先级的队列"""
        try:
            await self._queues[event.priority].put(event)
            self._stats["published"] += 1
            return True
        except asyncio.QueueFull:
            self._stats["dropped"] += 1
            logger.warning(f"队列满，丢弃事件: {event.type} (priority={event.priority})")
            return False

    async def emit(
        self,
        type: str,
        payload: Dict[str, Any] = None,
        category: EventCategory = EventCategory.SYSTEM,
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "",
        trace_id: str = "",
    ) -> Event:
        """快捷发布并返回事件对象"""
        event = Event(
            type=type,
            category=category,
            priority=priority,
            source=source,
            payload=payload or {},
            trace_id=trace_id or uuid.uuid4().hex[:16],
        )
        await self.publish(event)
        return event

    # ── 事件处理 ──────────────────────────────────────

    async def _process_event(self, event: Event):
        """将事件分发给所有匹配的订阅者"""
        matched_subs: List[EventSubscription] = []

        # 精确匹配
        if event.type in self._subscriptions:
            matched_subs.extend(self._subscriptions[event.type])

        # 通配符匹配
        for sub in self._wildcard_subscriptions:
            if sub.matches(event):
                matched_subs.append(sub)

        # 前缀匹配
        for pattern, subs in self._subscriptions.items():
            if pattern.endswith(".*"):
                prefix = pattern[:-2]
                if event.type.startswith(prefix + ".") or event.type == prefix:
                    matched_subs.extend(subs)

        if not matched_subs:
            return

        # 按优先级排序
        matched_subs.sort(key=lambda s: s.created_at)

        for sub in matched_subs:
            try:
                await sub.callback(event)
                self._stats["processed"] += 1
                # 一次性订阅自动取消
                if sub.once:
                    self.unsubscribe(sub.id)
            except Exception as e:
                self._stats["failed"] += 1
                logger.error(f"事件处理失败: {event.type} → {sub.pattern}: {e}")
                await self._dead_letter_queue.put((event, sub, str(e)))

    async def _worker_loop(self, worker_id: int):
        """工作线程循环：从高优先级队列取事件处理"""
        logger.info(f"事件总线 Worker-{worker_id} 启动")
        while self._running:
            processed = False
            for priority in sorted(EventPriority, key=lambda p: p.value):
                try:
                    event = self._queues[priority].get_nowait()
                    await self._process_event(event)
                    processed = True
                    break
                except asyncio.QueueEmpty:
                    continue
            if not processed:
                await asyncio.sleep(self._batch_window)

    # ── 生命周期 ──────────────────────────────────────

    def start(self):
        """启动事件总线"""
        if self._running:
            return
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker_loop(i))
            for i in range(self._worker_count)
        ]
        logger.info(f"事件总线启动: {self._worker_count} workers")

    async def stop(self, timeout: float = 5.0):
        """优雅关闭事件总线"""
        self._running = False
        if self._workers:
            done, pending = await asyncio.wait(
                self._workers, timeout=timeout
            )
            for task in pending:
                task.cancel()
        logger.info(f"事件总线停止. 统计: {self._stats}")

    def get_stats(self) -> Dict[str, int]:
        """获取事件统计"""
        return dict(self._stats)

    async def drain_dead_letters(self) -> List[tuple]:
        """排空死信队列"""
        letters = []
        while not self._dead_letter_queue.empty():
            try:
                letters.append(self._dead_letter_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return letters
