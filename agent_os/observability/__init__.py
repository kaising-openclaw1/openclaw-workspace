"""
Agent OS — 可观测性层
=====================
分布式追踪 + 结构化日志 + 实时指标
"""

import asyncio
import json
import logging
import os
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("agent-os.observability")


# ── 追踪 ──────────────────────────────────────────────

class SpanStatus(Enum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class Span:
    """追踪跨度"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    trace_id: str = ""
    parent_id: str = ""
    name: str = ""
    category: str = ""
    status: SpanStatus = SpanStatus.OK
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    duration_ms: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    error: str = ""

    def finish(self, status: SpanStatus = SpanStatus.OK, error: str = ""):
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error = error

    def add_event(self, name: str, attributes: Dict[str, Any] = None):
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "category": self.category,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "events": self.events,
            "error": self.error,
        }


class Tracer:
    """
    分布式追踪器

    支持：
    - 嵌套跨度（父-子）
    - 跨节点追踪（trace_id 传播）
    - 自动采样
    """

    def __init__(self, sample_rate: float = 1.0):
        self._spans: Dict[str, Span] = {}
        self._traces: Dict[str, List[Span]] = defaultdict(list)
        self._active_spans: Dict[str, str] = {}  # task_id -> current_span_id
        self._sample_rate = sample_rate
        self._event_bus = None

    def start_span(
        self,
        name: str,
        category: str = "",
        trace_id: str = "",
        parent_id: str = "",
        tags: Dict[str, str] = None,
    ) -> Span:
        """开始一个新的跨度"""
        if not trace_id:
            trace_id = uuid.uuid4().hex[:16]

        span = Span(
            name=name,
            category=category,
            trace_id=trace_id,
            parent_id=parent_id,
            tags=tags or {},
        )
        self._spans[span.id] = span
        self._traces[trace_id].append(span)
        return span

    def end_span(self, span_id: str, status: SpanStatus = SpanStatus.OK, error: str = ""):
        """结束跨度"""
        span = self._spans.get(span_id)
        if span:
            span.finish(status, error)
            if self._event_bus:
                asyncio.ensure_future(
                    self._event_bus.emit(
                        "observability.span_ended",
                        payload=span.to_dict(),
                    )
                )

    def get_trace(self, trace_id: str) -> List[Span]:
        return list(self._traces.get(trace_id, []))

    def get_span(self, span_id: str) -> Optional[Span]:
        return self._spans.get(span_id)

    def get_active_span(self, task_id: str) -> Optional[Span]:
        span_id = self._active_spans.get(task_id)
        if span_id:
            return self._spans.get(span_id)
        return None

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_spans": len(self._spans),
            "total_traces": len(self._traces),
            "active_spans": sum(1 for s in self._spans.values() if s.end_time == 0),
        }


# ── 指标 ──────────────────────────────────────────────

@dataclass
class MetricPoint:
    """指标数据点"""
    name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    type: str = "gauge"  # gauge, counter, histogram


class MetricsCollector:
    """
    指标收集器

    支持：
    - Counter（计数）
    - Gauge（瞬时值）
    - Histogram（分布）
    - 标签聚合
    """

    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._max_histogram_buckets = 1000
        self._points: List[MetricPoint] = []
        self._max_points = 10000
        self._event_bus = None

    def increment(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """计数器自增"""
        key = self._key(name, tags)
        self._counters[key] += value
        self._record(MetricPoint(name, self._counters[key], tags or {}, type="counter"))

    def gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """设置仪表值"""
        key = self._key(name, tags)
        self._gauges[key] = value
        self._record(MetricPoint(name, value, tags or {}, type="gauge"))

    def histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录直方图值"""
        key = self._key(name, tags)
        self._histograms[key].append(value)
        # 限制桶大小
        if len(self._histograms[key]) > self._max_histogram_buckets:
            self._histograms[key] = self._histograms[key][-self._max_histogram_buckets:]
        self._record(MetricPoint(name, value, tags or {}, type="histogram"))

    def _record(self, point: MetricPoint):
        self._points.append(point)
        if len(self._points) > self._max_points:
            self._points = self._points[-self._max_points:]
        if self._event_bus:
            asyncio.ensure_future(
                self._event_bus.emit(
                    "observability.metric",
                    payload={
                        "name": point.name,
                        "value": point.value,
                        "type": point.type,
                        "tags": point.tags,
                    },
                )
            )

    @staticmethod
    def _key(name: str, tags: Dict[str, str] = None) -> str:
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            return f"{name}#{tag_str}"
        return name

    def get_counter(self, name: str, tags: Dict[str, str] = None) -> float:
        return self._counters.get(self._key(name, tags), 0.0)

    def get_gauge(self, name: str, tags: Dict[str, str] = None) -> Optional[float]:
        return self._gauges.get(self._key(name, tags))

    def get_histogram_stats(self, name: str, tags: Dict[str, str] = None) -> Dict[str, float]:
        values = self._histograms.get(self._key(name, tags), [])
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        sorted_v = sorted(values)
        n = len(sorted_v)
        return {
            "count": n,
            "min": sorted_v[0],
            "max": sorted_v[-1],
            "avg": sum(sorted_v) / n,
            "p50": sorted_v[int(n * 0.5)],
            "p95": sorted_v[int(n * 0.95)],
            "p99": sorted_v[int(n * 0.99)],
        }

    def snapshot(self) -> Dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: self.get_histogram_stats(k)
                for k in self._histograms
            },
        }

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus


# ── 结构化日志 ────────────────────────────────────────

class LogLevel(Enum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class StructuredLog:
    """结构化日志条目"""
    level: LogLevel
    message: str
    module: str = ""
    trace_id: str = ""
    span_id: str = ""
    task_id: str = ""
    tags: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.name,
            "message": self.message,
            "module": self.module,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "task_id": self.task_id,
            "tags": self.tags,
            "timestamp": self.timestamp,
        }


class StructuredLogger:
    """
    结构化日志记录器

    输出格式：JSON Lines，可被任何日志收集系统消费
    """

    def __init__(self, log_dir: str = ""):
        self._log_dir = log_dir or os.path.expanduser("~/.agent-os/logs")
        os.makedirs(self._log_dir, exist_ok=True)
        self._log_file = os.path.join(
            self._log_dir,
            f"agent-os-{time.strftime('%Y-%m-%d')}.jsonl"
        )
        self._buffer: List[StructuredLog] = []
        self._max_buffer = 50
        self._event_bus = None

    def log(
        self,
        level: LogLevel,
        message: str,
        module: str = "",
        trace_id: str = "",
        span_id: str = "",
        task_id: str = "",
        tags: Dict[str, Any] = None,
    ):
        """记录结构化日志"""
        entry = StructuredLog(
            level=level,
            message=message,
            module=module,
            trace_id=trace_id,
            span_id=span_id,
            task_id=task_id,
            tags=tags or {},
        )
        self._buffer.append(entry)

        if len(self._buffer) >= self._max_buffer:
            self._flush()

        if self._event_bus and level.value >= LogLevel.WARNING.value:
            asyncio.ensure_future(
                self._event_bus.emit(
                    "observability.log",
                    payload=entry.to_dict(),
                )
            )

    def debug(self, msg: str, **tags):
        self.log(LogLevel.DEBUG, msg, **tags)

    def info(self, msg: str, **tags):
        self.log(LogLevel.INFO, msg, **tags)

    def warning(self, msg: str, **tags):
        self.log(LogLevel.WARNING, msg, **tags)

    def error(self, msg: str, **tags):
        self.log(LogLevel.ERROR, msg, **tags)

    def critical(self, msg: str, **tags):
        self.log(LogLevel.CRITICAL, msg, **tags)

    def _flush(self):
        if not self._buffer:
            return
        try:
            with open(self._log_file, "a") as f:
                for entry in self._buffer:
                    f.write(json.dumps(entry.to_dict()) + "\n")
            self._buffer.clear()
        except Exception as e:
            logger.error(f"日志写入失败: {e}")

    def flush(self):
        self._flush()

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus
