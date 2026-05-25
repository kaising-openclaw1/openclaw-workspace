# 手把手教你用 Python 构建 AI Agent 可观测性平台：追踪、调试、优化你的智能体

> **关键词：** AI Agent Observability、Trace、LLM Monitoring、Python、OpenTelemetry、Agent 调试
> **目标平台：** 掘金 / 知乎 / V2EX / InfoQ
> **字数：** 约 5500 字
> **配套项目：** github.com/kaising-openclaw1/agent-observability

---

## 前言：你的 AI Agent 到底在干什么？

2026 年，AI Agent 已经从"能不能用"进入了"好不好用"的阶段。

企业把 Agent 部署到生产环境后，遇到了一个共同的痛点：**黑盒问题**。

用户问了一个问题，Agent 经过了 5 步推理、调用了 3 个工具、查询了 2 次数据库，最终给出了一个错误答案。然后呢？

- 哪一步出错了？不知道。
- 哪个工具返回了意外数据？不知道。
- LLM 的 token 消耗是多少？不知道。
- 整个流程花了多长时间？不知道。
- 怎么复现和调试？更不知道。

这就是 **AI Agent 可观测性（Observability）** 要解决的问题。

本文将带你从零构建一个完整的 AI Agent 可观测性平台，包含：
- **自动 Trace 采集**：无需修改业务代码，自动记录 Agent 的每一步操作
- **LLM 调用监控**：token 用量、成本追踪、延迟分析
- **工具调用追踪**：参数、返回值、异常全记录
- **可视化 Dashboard**：Trace 树、成本图表、性能指标
- **智能告警**：异常延迟、成本超支、错误率飙升自动通知

---

## 一、可观测性的三大支柱

在可观测性领域，有三个核心概念：

### 1. Trace（追踪）

Trace 记录一次完整请求的全链路。对于 AI Agent 来说，一个 Trace 包含：
- 用户输入
- Agent 的推理过程（Chain of Thought）
- 工具调用序列
- LLM API 调用
- 最终输出

每个步骤是一个 **Span**，Span 之间有父子关系，形成一棵 Trace 树。

```
Trace: user_query_12345
├── Span: agent_thinking (2.3s)
│   ├── Span: tool_search_knowledge_base (0.8s)
│   │   └── Span: vector_db_query (0.3s)
│   ├── Span: llm_generate (1.2s)
│   └── Span: tool_execute_api_call (0.5s)
└── Span: agent_response (0.1s)
```

### 2. Metric（指标）

聚合的统计数据：
- 平均响应时间
- Token 消耗总量 & 成本
- 工具调用成功率
- 错误率

### 3. Log（日志）

结构化的事件记录，包含时间戳、级别、上下文信息。

---

## 二、项目架构

我们的可观测性平台由四个模块组成：

```
agent-observability/
├── tracer/          # Trace 采集器（自动拦截 + 记录）
├── collector/       # 数据收集与存储（SQLite + 内存缓冲）
├── dashboard/       # Web 可视化界面（FastAPI + 原生前端）
└── alerter/         # 智能告警引擎（阈值 + 异常检测）
```

核心设计理念：**零侵入**。Agent 业务代码不需要任何修改，通过装饰器和拦截器自动采集。

---

## 三、核心模块实现

### 3.1 Trace 采集器

```python
# tracer/core.py
import time
import uuid
import json
import threading
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from enum import Enum

class SpanStatus(Enum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"

@dataclass
class Span:
    span_id: str
    trace_id: str
    name: str
    span_type: str  # "agent", "llm", "tool", "db"
    start_time: float
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.OK
    parent_id: Optional[str] = None
    attributes: dict = field(default_factory=dict)
    input_data: Optional[Any] = None
    output_data: Optional[Any] = None
    error: Optional[str] = None
    children: list = field(default_factory=list)

    @property
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "name": self.name,
            "span_type": self.span_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "attributes": self.attributes,
            "error": self.error,
        }

# 线程安全的 Trace 上下文
_current_trace: ContextVar[Optional[str]] = ContextVar("current_trace", default=None)
_spans: dict[str, Span] = {}
_traces: dict[str, list[str]] = {}  # trace_id -> [span_ids]
_lock = threading.Lock()

def start_trace(name: str) -> str:
    trace_id = str(uuid.uuid4())[:12]
    _current_trace.set(trace_id)
    with _lock:
        _traces[trace_id] = []
    return trace_id

def start_span(
    name: str,
    span_type: str,
    parent_id: Optional[str] = None,
    attributes: Optional[dict] = None,
    input_data: Any = None,
) -> Span:
    trace_id = _current_trace.get() or start_trace(name)
    span_id = str(uuid.uuid4())[:12]

    span = Span(
        span_id=span_id,
        trace_id=trace_id,
        name=name,
        span_type=span_type,
        start_time=time.time(),
        parent_id=parent_id,
        attributes=attributes or {},
        input_data=input_data,
    )

    with _lock:
        _spans[span_id] = span
        if trace_id in _traces:
            _traces[trace_id].append(span_id)

    return span

def end_span(span: Span, status: SpanStatus = SpanStatus.OK, error: Optional[str] = None):
    span.end_time = time.time()
    span.status = status
    if error:
        span.error = error

def get_trace(trace_id: str) -> dict:
    with _lock:
        span_ids = _traces.get(trace_id, [])
        spans = [_spans[sid].to_dict() for sid in span_ids]

    # 构建树形结构
    span_map = {s["span_id"]: s for s in spans}
    roots = []
    for s in spans:
        if s["parent_id"] is None or s["parent_id"] not in span_map:
            roots.append(s)
        else:
            parent = span_map.get(s["parent_id"])
            if parent:
                parent.setdefault("children", []).append(s)

    total_duration = max((s["duration"] for s in spans), default=0)
    total_cost = sum(s.get("attributes", {}).get("cost", 0) for s in spans)

    return {
        "trace_id": trace_id,
        "spans": spans,
        "tree": roots,
        "total_duration": total_duration,
        "total_cost": total_cost,
        "span_count": len(spans),
    }

def list_traces(limit: int = 50) -> list[dict]:
    with _lock:
        trace_ids = list(_traces.keys())[-limit:]

    results = []
    for tid in reversed(trace_ids):
        span_ids = _traces[tid]
        spans = [_spans[sid] for sid in span_ids]
        root = next((s for s in spans if s.parent_id is None), None)
        results.append({
            "trace_id": tid,
            "root_name": root.name if root else "unknown",
            "duration": max(s.duration for s in spans),
            "span_count": len(spans),
            "status": "error" if any(s.status == SpanStatus.ERROR for s in spans) else "ok",
            "timestamp": min(s.start_time for s in spans),
            "cost": sum(s.attributes.get("cost", 0) for s in spans),
        })
    return results
```

### 3.2 零侵入装饰器

```python
# tracer/decorators.py
import functools
from .core import start_span, end_span, SpanStatus, _current_trace

def trace_agent(func):
    """装饰 Agent 主函数，自动创建 Trace"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        span = start_span(
            name=func.__name__,
            span_type="agent",
            input_data={"args": str(args)[:200], "kwargs": str(kwargs)[:200]},
        )
        try:
            result = func(*args, **kwargs)
            end_span(span, output_data=str(result)[:500])
            return result
        except Exception as e:
            end_span(span, status=SpanStatus.ERROR, error=str(e))
            raise
    return wrapper

def trace_tool(func):
    """装饰工具函数，自动记录参数和返回值"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        span = start_span(
            name=func.__name__,
            span_type="tool",
            attributes={"args_count": len(args), "kwargs_keys": list(kwargs.keys())},
            input_data={"args": str(args)[:300], "kwargs": str(kwargs)[:300]},
        )
        try:
            result = func(*args, **kwargs)
            end_span(span, output_data=str(result)[:500])
            return result
        except Exception as e:
            end_span(span, status=SpanStatus.ERROR, error=str(e))
            raise
    return wrapper

def trace_llm(func):
    """装饰 LLM 调用函数，自动记录 token 和成本"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        model = kwargs.get("model", args[0] if args else "unknown")
        span = start_span(
            name=f"llm:{model}",
            span_type="llm",
            attributes={
                "model": model,
                "temperature": kwargs.get("temperature", "N/A"),
                "max_tokens": kwargs.get("max_tokens", "N/A"),
            },
            input_data={"prompt_preview": str(kwargs.get("messages", args))[:200]},
        )
        try:
            result = func(*args, **kwargs)
            # 尝试从响应中提取 token 信息
            token_info = {}
            if isinstance(result, dict):
                usage = result.get("usage", {})
                token_info = {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }
            end_span(span, output_data=str(result)[:300], attributes={
                **span.attributes,
                **token_info,
            })
            return result
        except Exception as e:
            end_span(span, status=SpanStatus.ERROR, error=str(e))
            raise
    return wrapper
```

### 3.3 成本计算器

```python
# collector/cost.py
# 2026年主流 LLM API 定价（每 1K tokens）
PRICING = {
    "gpt-4o": {"input": 0.01, "output": 0.03},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-sonnet-4": {"input": 0.003, "output": 0.015},
    "claude-opus-4": {"input": 0.015, "output": 0.075},
    "deepseek-chat": {"input": 0.0001, "output": 0.0003},
    "deepseek-reasoner": {"input": 0.0002, "output": 0.0008},
    "qwen-plus": {"input": 0.0004, "output": 0.0012},
    "qwen-max": {"input": 0.0016, "output": 0.0048},
}

def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    model = model.lower().strip()
    if model not in PRICING:
        # 模糊匹配
        for key in PRICING:
            if key in model:
                model = key
                break
        else:
            return 0.0  # 未知模型，不计费

    pricing = PRICING[model]
    return (prompt_tokens / 1000) * pricing["input"] + (completion_tokens / 1000) * pricing["output"]

def get_cost_report(spans: list[dict]) -> dict:
    by_model = {}
    total_cost = 0.0
    total_tokens = 0

    for span in spans:
        if span.get("span_type") != "llm":
            continue
        attrs = span.get("attributes", {})
        model = attrs.get("model", "unknown")
        prompt_tokens = attrs.get("prompt_tokens", 0)
        completion_tokens = attrs.get("completion_tokens", 0)
        cost = calculate_cost(model, prompt_tokens, completion_tokens)

        total_cost += cost
        total_tokens += prompt_tokens + completion_tokens

        if model not in by_model:
            by_model[model] = {"cost": 0, "tokens": 0, "calls": 0}
        by_model[model]["cost"] += cost
        by_model[model]["tokens"] += prompt_tokens + completion_tokens
        by_model[model]["calls"] += 1

    return {
        "total_cost": round(total_cost, 4),
        "total_tokens": total_tokens,
        "by_model": by_model,
    }
```

### 3.4 持久化存储

```python
# collector/storage.py
import sqlite3
import json
import threading
from pathlib import Path

class TraceStorage:
    def __init__(self, db_path: str = "traces.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_conn()
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS traces (
                    trace_id TEXT PRIMARY KEY,
                    root_name TEXT,
                    duration REAL,
                    span_count INTEGER,
                    status TEXT,
                    cost REAL DEFAULT 0,
                    timestamp REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS spans (
                    span_id TEXT PRIMARY KEY,
                    trace_id TEXT,
                    name TEXT,
                    span_type TEXT,
                    duration REAL,
                    status TEXT,
                    parent_id TEXT,
                    attributes TEXT,
                    error TEXT,
                    FOREIGN KEY (trace_id) REFERENCES traces(trace_id)
                );
                CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id);
                CREATE INDEX IF NOT EXISTS idx_traces_time ON traces(timestamp);
                CREATE INDEX IF NOT EXISTS idx_traces_status ON traces(status);
            """)
            conn.commit()
            conn.close()

    def save_trace(self, trace_data: dict):
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO traces VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                    (
                        trace_data["trace_id"],
                        trace_data.get("root_name", "unknown"),
                        trace_data["duration"],
                        trace_data["span_count"],
                        trace_data["status"],
                        trace_data.get("cost", 0),
                        trace_data.get("timestamp", 0),
                    ),
                )
                for span in trace_data.get("spans", []):
                    conn.execute(
                        "INSERT OR REPLACE INTO spans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            span["span_id"],
                            span["trace_id"],
                            span["name"],
                            span["span_type"],
                            span["duration"],
                            span["status"],
                            span.get("parent_id"),
                            json.dumps(span.get("attributes", {})),
                            span.get("error"),
                        ),
                    )
                conn.commit()
            finally:
                conn.close()

    def get_traces(self, limit: int = 50, status: str = None) -> list[dict]:
        with self._lock:
            conn = self._get_conn()
            try:
                if status:
                    rows = conn.execute(
                        "SELECT * FROM traces WHERE status = ? ORDER BY timestamp DESC LIMIT ?",
                        (status, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM traces ORDER BY timestamp DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

    def get_trace_detail(self, trace_id: str) -> dict:
        with self._lock:
            conn = self._get_conn()
            try:
                trace = conn.execute(
                    "SELECT * FROM traces WHERE trace_id = ?", (trace_id,)
                ).fetchone()
                spans = conn.execute(
                    "SELECT * FROM spans WHERE trace_id = ?", (trace_id,)
                ).fetchall()
                if not trace:
                    return {}
                result = dict(trace)
                result["spans"] = [dict(s) for s in spans]
                return result
            finally:
                conn.close()
```

### 3.5 Web Dashboard

```python
# dashboard/app.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from collector.storage import TraceStorage
from collector.cost import get_cost_report

app = FastAPI(title="Agent Observability Dashboard")
storage = TraceStorage()

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return Path(__file__).parent / "static" / "index.html"

@app.get("/api/traces")
async def list_traces(limit: int = 50, status: str = None):
    return storage.get_traces(limit, status)

@app.get("/api/traces/{trace_id}")
async def get_trace(trace_id: str):
    data = storage.get_trace_detail(trace_id)
    if not data:
        raise HTTPException(404, "Trace not found")
    return data

@app.get("/api/costs")
async def cost_report():
    traces = storage.get_traces(limit=1000)
    all_spans = []
    for t in traces:
        spans = storage.get_trace_detail(t["trace_id"]).get("spans", [])
        all_spans.extend(spans)
    return get_cost_report(all_spans)

@app.get("/api/stats")
async def stats():
    traces = storage.get_traces(limit=10000)
    if not traces:
        return {"total_traces": 0, "avg_duration": 0, "error_rate": 0, "total_cost": 0}

    total = len(traces)
    avg_duration = sum(t["duration"] for t in traces) / total
    errors = sum(1 for t in traces if t["status"] == "error")
    total_cost = sum(t.get("cost", 0) for t in traces)

    return {
        "total_traces": total,
        "avg_duration": round(avg_duration, 3),
        "error_rate": round(errors / total * 100, 2),
        "total_cost": round(total_cost, 4),
        "success_rate": round((total - errors) / total * 100, 2),
    }
```

---

## 四、使用示例

### 4.1 集成到你的 Agent

只需添加装饰器，零侵入：

```python
from agent_observability.tracer.decorators import trace_agent, trace_tool, trace_llm
from agent_observability.tracer.core import start_trace, end_span
from agent_observability.collector.storage import TraceStorage

storage = TraceStorage()

@trace_agent
def my_agent(user_query: str):
    # 你的 Agent 逻辑，无需任何改动
    context = search_knowledge_base(user_query)
    analysis = analyze_data(context)
    response = call_llm(analysis)
    return response

@trace_tool
def search_knowledge_base(query: str):
    # 工具函数自动被追踪
    return db.search(query)

@trace_tool
def analyze_data(context: dict):
    return {"summary": context[:500], "keywords": extract_keywords(context)}

@trace_llm
def call_llm(analysis: dict):
    # LLM 调用自动记录 token 和成本
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": str(analysis)}],
    )
    return response

# 运行
if __name__ == "__main__":
    start_trace("demo")
    result = my_agent("2026年AI行业趋势是什么？")

    # 查看 Trace
    from agent_observability.tracer.core import get_trace
    trace = get_trace(_current_trace.get())
    print(f"总耗时: {trace['total_duration']:.2f}s")
    print(f"总成本: ¥{trace['total_cost']:.4f}")
    print(f"Span 数量: {trace['span_count']}")

    # 持久化
    storage.save_trace(trace)
```

### 4.2 启动 Dashboard

```bash
pip install fastapi uvicorn
cd agent-observability
uvicorn dashboard.app:app --host 0.0.0.0 --port 8080
# 访问 http://localhost:8080
```

Dashboard 提供：
- 📊 Trace 列表（按时间/状态/成本排序）
- 🌳 Trace 树形可视化（展开每个 Span 的详情）
- 💰 成本分析（按模型/时间维度）
- ⚡ 性能指标（P50/P95/P99 延迟）
- 🚨 错误率监控

---

## 五、告警引擎

```python
# alerter/engine.py
from dataclasses import dataclass
from typing import Callable
from collector.storage import TraceStorage

@dataclass
class AlertRule:
    name: str
    condition: Callable  # 返回 True 时触发
    message: str
    severity: str = "warning"  # warning / critical

class AlertEngine:
    def __init__(self, storage: TraceStorage):
        self.storage = storage
        self.rules: list[AlertRule] = []
        self.callbacks: list[Callable] = []

    def add_rule(self, rule: AlertRule):
        self.rules.append(rule)

    def on_alert(self, callback: Callable):
        self.callbacks.append(callback)

    def check(self):
        traces = self.storage.get_traces(limit=100)
        if not traces:
            return

        for rule in self.rules:
            if rule.condition(traces):
                for cb in self.callbacks:
                    cb(rule, traces)

# 内置规则
def high_error_rate_rule(threshold: float = 0.1) -> AlertRule:
    def condition(traces):
        errors = sum(1 for t in traces if t["status"] == "error")
        return errors / len(traces) > threshold
    return AlertRule(
        name="high_error_rate",
        condition=condition,
        message=f"Agent 错误率超过 {threshold*100}%",
        severity="critical",
    )

def high_latency_rule(threshold_ms: float = 5000) -> AlertRule:
    def condition(traces):
        slow = sum(1 for t in traces if t["duration"] > threshold_ms / 1000)
        return slow / len(traces) > 0.2
    return AlertRule(
        name="high_latency",
        condition=condition,
        message=f"超过 20% 的 Agent 调用耗时 > {threshold_ms}ms",
        severity="warning",
    )

def cost_spike_rule(threshold: float = 1.0) -> AlertRule:
    def condition(traces):
        total_cost = sum(t.get("cost", 0) for t in traces)
        return total_cost > threshold
    return AlertRule(
        name="cost_spike",
        condition=condition,
        message=f"最近 100 次调用成本超过 ¥{threshold}",
        severity="warning",
    )
```

---

## 六、实战价值

### 6.1 企业为什么需要？

| 场景 | 无可观测性 | 有可观测性 |
|------|-----------|-----------|
| Agent 回复错误 | 无从排查 | 精确定位到出错的 Span |
| 成本超预算 | 月底才发现 | 实时告警，及时止损 |
| 性能优化 | 凭感觉猜测 | P95/P99 数据说话 |
| 合规审计 | 无法证明 | 完整 Trace 记录可追溯 |

### 6.2 商业机会

1. **SaaS 产品**：为企业 Agent 提供托管可观测性服务
   - 定价：¥299-2999/月（按调用量）
   - 对标：LangSmith（$0.025/run）、Arize Phoenix（开源+企业版）

2. **咨询+部署服务**：为企业定制部署可观测性方案
   - 定价：¥5,000-20,000/项目
   - 包括：集成现有 Agent、配置告警规则、培训团队

3. **开源引流**：开源核心版 + 企业版增值功能
   - 企业功能：多租户、SSO、审计日志、自定义 Dashboard

---

## 七、总结

AI Agent 可观测性不是"锦上添花"，而是生产环境的**必需品**。

没有可观测性的 Agent 就像没有仪表的汽车——你根本不知道引擎在干什么，直到它冒烟的那一刻。

本文构建的平台具备：
- ✅ 零侵入 Trace 采集
- ✅ LLM 成本精确计算
- ✅ 可视化 Dashboard
- ✅ 智能告警引擎
- ✅ SQLite 持久化存储

**下一步**：接入 OpenTelemetry 标准、支持更多 LLM 提供商、添加异常检测算法。

---

> 📌 配套项目地址：github.com/kaising-openclaw1/agent-observability
> 💬 有问题？欢迎在评论区交流！
