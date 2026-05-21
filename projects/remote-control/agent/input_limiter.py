"""输入限速器 — 防止鼠标/键盘事件洪水攻击

在远程桌面场景中，用户的鼠标移动可能产生极高的事件频率
（例如 500+ events/sec），直接转发会导致：
1. Agent 端输入队列阻塞
2. 网络带宽浪费
3. 远程操作延迟增大

本模块实现:
- 鼠标移动事件合并（只保留最新位置）
- 事件频率限制（最大 N events/sec）
- 事件队列缓冲
"""
import time
import asyncio
import logging
from collections import deque
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


class InputRateLimiter:
    """输入事件限速器"""

    def __init__(
        self,
        max_events_per_sec: int = 60,
        merge_mouse_move: bool = True,
    ):
        self.max_eps = max_events_per_sec
        self.min_interval = 1.0 / max_events_per_sec
        self.merge_mouse_move = merge_mouse_move

        self._timestamps: deque = deque(maxlen=max_events_per_sec)
        self._last_mouse_move: Optional[dict] = None
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self, send_fn: Callable[[dict], Any]):
        """启动限速器

        Args:
            send_fn: 实际发送事件的异步函数
        """
        self._send_fn = send_fn
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info(f"🚦 输入限速器已启动 (max={self.max_eps}/s)")

    async def stop(self):
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        # 刷新剩余的鼠标移动事件
        if self._last_mouse_move:
            await self._send_fn(self._last_mouse_move)
            self._last_mouse_move = None

    def submit(self, event: dict):
        """提交一个输入事件

        鼠标移动事件会被合并，只保留最新位置。
        其他事件进入队列等待发送。
        """
        action = event.get("action", "")

        if action == "mouse_move" and self.merge_mouse_move:
            # 合并鼠标移动：只保留最新
            self._last_mouse_move = event
        else:
            # 其他事件直接尝试发送
            self._try_send(event)

    def _try_send(self, event: dict):
        """尝试立即发送事件（受速率限制）"""
        now = time.time()

        # 清理过期的时间戳
        while self._timestamps and self._timestamps[0] < now - 1.0:
            self._timestamps.popleft()

        # 检查是否超过速率限制
        if len(self._timestamps) >= self.max_eps:
            # 超过限制，丢弃或排队（这里选择丢弃最旧的事件）
            self._timestamps.popleft()

        self._timestamps.append(now)

    async def _flush_loop(self):
        """定期刷新合并的鼠标移动事件"""
        while self._running:
            if self._last_mouse_move:
                self._try_send(self._last_mouse_move)
                await self._send_fn(self._last_mouse_move)
                self._last_mouse_move = None
            await asyncio.sleep(self.min_interval)

    @property
    def current_rate(self) -> int:
        """当前事件速率 (events/sec)"""
        now = time.time()
        while self._timestamps and self._timestamps[0] < now - 1.0:
            self._timestamps.popleft()
        return len(self._timestamps)
