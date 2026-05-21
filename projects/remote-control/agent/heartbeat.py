"""心跳保活 — Agent 与 Server 双向心跳检测

功能:
- Agent 定时发送心跳到 Server
- Server 记录最后心跳时间，超时标记设备离线
- Controller 心跳检测连接质量
- 断线自动重连（指数退避）
"""
import asyncio
import logging
import time
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


class Heartbeat:
    """心跳管理器"""
    
    def __init__(
        self,
        interval: float = 15.0,
        timeout: float = 45.0,
        max_missed: int = 3,
        on_timeout: Optional[Callable[[], Awaitable[None]]] = None,
    ):
        self.interval = interval
        self.timeout = timeout
        self.max_missed = max_missed
        self.last_beat = time.time()
        self.beat_count = 0
        self.missed_count = 0
        self.rtt_ms = 0.0
        self._ping_sent_at = 0.0
        self.on_timeout = on_timeout  # 超时回调
    
    def send_ping(self):
        """发送 ping"""
        self._ping_sent_at = time.time()
    
    def receive_pong(self):
        """收到 pong 回复"""
        now = time.time()
        if self._ping_sent_at > 0:
            self.rtt_ms = (now - self._ping_sent_at) * 1000
            self._ping_sent_at = 0.0
        self.last_beat = now
        self.beat_count += 1
        if self.missed_count > 0:
            logger.info(f"💓 心跳恢复 (丢失 {self.missed_count} 次, RTT={self.rtt_ms:.0f}ms)")
            self.missed_count = 0
    
    def is_alive(self) -> bool:
        return (time.time() - self.last_beat) < self.timeout
    
    def time_since_beat(self) -> float:
        return time.time() - self.last_beat
    
    def check(self) -> bool:
        """检查是否超时"""
        if not self.is_alive():
            self.missed_count += 1
            logger.warning(f"⚠️ 心跳超时 #{self.missed_count} ({self.time_since_beat():.0f}s)")
            return False
        return True
    
    def status(self) -> dict:
        return {
            "alive": self.is_alive(),
            "beat_count": self.beat_count,
            "missed_count": self.missed_count,
            "rtt_ms": round(self.rtt_ms, 1),
            "last_beat_ago": round(self.time_since_beat(), 1),
        }
    
    def beat(self):
        """记录一次心跳"""
        self.last_beat = time.time()
        self.beat_count += 1
