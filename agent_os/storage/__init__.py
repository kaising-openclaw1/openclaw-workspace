"""
Agent OS — 存储层
=================
对象存储、向量数据库、消息队列、文件同步
"""

import asyncio
import json
import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("agent-os.storage")


class ObjectStore:
    """
    轻量级对象存储（基于 SQLite）

    用于存储任务结果、Agent 状态、配置等
    """

    def __init__(self, db_path: str = ""):
        self._db_path = db_path or os.path.expanduser("~/.agent-os/store.db")
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS objects (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                content_type TEXT DEFAULT 'application/json',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                ttl REAL DEFAULT 0
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def put(self, key: str, value: Any, content_type: str = "application/json",
            ttl: float = 0) -> bool:
        """存储对象"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            now = time.time()
            self._conn.execute(
                """INSERT OR REPLACE INTO objects
                   (key, value, content_type, created_at, updated_at, ttl)
                   VALUES (?, ?, ?, COALESCE((SELECT created_at FROM objects WHERE key=?), ?), ?, ?)""",
                (key, value, content_type, key, now, now, ttl),
            )
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"存储失败 [{key}]: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """获取对象"""
        try:
            cursor = self._conn.execute(
                "SELECT value, content_type, ttl, created_at FROM objects WHERE key=?",
                (key,),
            )
            row = cursor.fetchone()
            if not row:
                return default

            value, content_type, ttl, created_at = row

            # TTL 检查
            if ttl > 0 and time.time() > created_at + ttl:
                self.delete(key)
                return default

            if content_type == "application/json":
                return json.loads(value)
            return value
        except Exception as e:
            logger.error(f"读取失败 [{key}]: {e}")
            return default

    def delete(self, key: str) -> bool:
        """删除对象"""
        try:
            self._conn.execute("DELETE FROM objects WHERE key=?", (key,))
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"删除失败 [{key}]: {e}")
            return False

    def list_keys(self, prefix: str = "") -> List[str]:
        """列出键"""
        if prefix:
            cursor = self._conn.execute(
                "SELECT key FROM objects WHERE key LIKE ?", (prefix + "%",)
            )
        else:
            cursor = self._conn.execute("SELECT key FROM objects")
        return [row[0] for row in cursor.fetchall()]

    def cleanup_expired(self) -> int:
        """清理过期对象"""
        cursor = self._conn.execute(
            "DELETE FROM objects WHERE ttl > 0 AND created_at + ttl < ?",
            (time.time(),),
        )
        self._conn.commit()
        return cursor.rowcount

    def close(self):
        if self._conn:
            self._conn.close()


class MessageQueue:
    """
    轻量级内存消息队列

    用于 Agent 间通信和任务分发
    """

    def __init__(self, max_size: int = 10000):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._max_size = max_size

    async def publish(self, topic: str, message: Any):
        """发布消息到主题"""
        if topic not in self._queues:
            self._queues[topic] = asyncio.Queue(maxsize=self._max_size)
        try:
            await self._queues[topic].put(message)
            return True
        except asyncio.QueueFull:
            logger.warning(f"消息队列满 [{topic}]")
            return False

    async def subscribe(self, topic: str, timeout: float = None) -> Optional[Any]:
        """订阅主题（阻塞直到有消息）"""
        if topic not in self._queues:
            self._queues[topic] = asyncio.Queue(maxsize=self._max_size)
        try:
            return await asyncio.wait_for(
                self._queues[topic].get(), timeout=timeout
            )
        except asyncio.TimeoutError:
            return None

    def queue_size(self, topic: str) -> int:
        queue = self._queues.get(topic)
        return queue.qsize() if queue else 0

    def topics(self) -> List[str]:
        return list(self._queues.keys())
