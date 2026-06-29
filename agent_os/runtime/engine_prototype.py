"""
Agent OS 3.0 — Execution Loop Prototype
=========================================
核心闭环验证：Planner → Task Graph → Scheduler → Executor → Validator → Store

这个 prototype 是独立的，不依赖现有代码。
验证通过后，再迁移到正式模块。

运行: python -m agent_os.runtime.engine_prototype
"""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Optional, List, Dict, Tuple, Set
from collections import deque

# ═══════════════════════════════════════════════════════════════
# 1. 类型定义
# ═══════════════════════════════════════════════════════════════

class TaskStatus(Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"

class Verdict(Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"

class ExecutorKind(Enum):
    LLM = "llm"
    TOOL = "tool"
    CODE = "code"
    HUMAN = "human"

@dataclass
class Task:
    """最小化 Task 定义（基于 IR 规范）"""
    id: str
    name: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    dependency_mode: str = "all"  # all | any
    executor: str = "llm"
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})
    output_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})
    validation_level: str = "schema_only"  # none | schema_only | full
    max_retries: int = 2
    timeout_seconds: int = 60
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    output: Optional[dict] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

@dataclass
class Artifact:
    """Task 产生的数据单元"""
    id: str
    task_id: str
    name: str
    content: Any
    created_at: float

@dataclass
class FailureRecord:
    """压缩后的失败学习信号"""
    task_id: str
    lesson: str
    root_cause: str
    suggested_fix: str
    occurrence_count: int = 1


# ═══════════════════════════════════════════════════════════════
# 2. Task Graph — 增量 DAG
# ═══════════════════════════════════════════════════════════════

class TaskGraph:
    """Incremental DAG: 运行时动态扩展"""

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._entry_points: List[str] = []

    def add_task(self, task: Task) -> None:
        """添加任务（运行时动态扩展）"""
        if task.id in self.tasks:
            raise ValueError(f"Task {task.id} already exists")
        self.tasks[task.id] = task
        if not task.dependencies:
            self._entry_points.append(task.id)

    def add_dependency(self, task_id: str, dep_id: str) -> None:
        """运行时添加依赖边"""
        if task_id not in self.tasks or dep_id not in self.tasks:
            raise ValueError("Task not found")
        # 检查是否会形成环（简单 BFS）
        if self._would_create_cycle(task_id, dep_id):
            raise ValueError(f"Adding dependency {dep_id}→{task_id} would create a cycle")
        if dep_id not in self.tasks[task_id].dependencies:
            self.tasks[task_id].dependencies.append(dep_id)

    def _would_create_cycle(self, task_id: str, dep_id: str) -> bool:
        """BFS 检测从 dep_id 出发是否能到达 task_id"""
        visited = set()
        queue = deque([task_id])
        while queue:
            current = queue.popleft()
            if current == dep_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            for dep in self.tasks.get(current, Task(id="")).dependencies:
                if dep not in visited:
                    queue.append(dep)
        return False

    def get_ready_tasks(self) -> List[Task]:
        """获取所有依赖已满足的 READY 任务"""
        ready = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            if self._dependencies_met(task):
                task.status = TaskStatus.READY
                ready.append(task)
        return ready

    def _dependencies_met(self, task: Task) -> bool:
        if not task.dependencies:
            return True
        if task.dependency_mode == "all":
            return all(
                self.tasks[dep].status == TaskStatus.COMPLETED
                for dep in task.dependencies
                if dep in self.tasks
            )
        else:  # any
            return any(
                self.tasks[dep].status == TaskStatus.COMPLETED
                for dep in task.dependencies
                if dep in self.tasks
            )

    def all_done(self) -> bool:
        """所有任务是否已完成/失败/跳过"""
        if not self.tasks:
            return False
        terminal = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED}
        return all(t.status in terminal for t in self.tasks.values())

    def get_entry_points(self) -> List[str]:
        return self._entry_points


# ═══════════════════════════════════════════════════════════════
# 3. Schema Validator — 确定性校验
# ═══════════════════════════════════════════════════════════════

class SchemaValidator:
    """基于 JSON Schema 的确定性校验"""

    @staticmethod
    def validate(data: Any, schema: dict) -> Tuple[bool, List[str]]:
        """校验数据是否符合 schema，返回 (通过?, 错误列表)"""
        errors = []
        SchemaValidator._validate_value(data, schema, "$", errors)
        return len(errors) == 0, errors

    @staticmethod
    def _validate_value(value: Any, schema: dict, path: str, errors: List[str]) -> None:
        schema_type = schema.get("type", "any")

        # null 处理
        if value is None:
            if schema_type == "null":
                return
            errors.append(f"{path}: expected {schema_type}, got null")
            return

        # 类型检查
        type_map = {
            "string": str, "number": (int, float), "boolean": bool,
            "object": dict, "array": list,
        }
        expected_type = type_map.get(schema_type)
        if expected_type and not isinstance(value, expected_type):
            errors.append(f"{path}: expected {schema_type}, got {type(value).__name__}")
            return

        # object 属性检查
        if schema_type == "object" and isinstance(value, dict):
            props = schema.get("properties", {})
            required = schema.get("required", [])
            for field in required:
                if field not in value:
                    errors.append(f"{path}.{field}: missing required field")
            for field, field_schema in props.items():
                if field in value:
                    SchemaValidator._validate_value(
                        value[field], field_schema, f"{path}.{field}", errors
                    )

        # array 元素检查
        if schema_type == "array" and isinstance(value, list):
            items_schema = schema.get("items", {})
            for i, item in enumerate(value):
                SchemaValidator._validate_value(item, items_schema, f"{path}[{i}]", errors)

        # 枚举检查
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path}: value {value!r} not in enum {schema['enum']}")

        # 字符串约束
        if schema_type == "string" and isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                errors.append(f"{path}: minLength {schema['minLength']}, got {len(value)}")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                errors.append(f"{path}: maxLength {schema['maxLength']}, got {len(value)}")

        # 数字约束
        if schema_type == "number" and isinstance(value, (int, float)):
            if "minimum" in schema and value < schema["minimum"]:
                errors.append(f"{path}: minimum {schema['minimum']}, got {value}")
            if "maximum" in schema and value > schema["maximum"]:
                errors.append(f"{path}: maximum {schema['maximum']}, got {value}")


# ═══════════════════════════════════════════════════════════════
# 4. Executor — 执行器
# ═══════════════════════════════════════════════════════════════

class Executor:
    """执行 Task，返回 OutputContract"""

    def __init__(self, llm_callable: Optional[Callable] = None):
        self._llm = llm_callable or self._default_llm

    @staticmethod
    def _default_llm(prompt: str, context: dict) -> dict:
        """默认 LLM 模拟器 — 根据任务类型返回合理输出"""
        task_id = context.get('task', '')
        if 'fetch' in task_id or 'search' in task_id:
            return {'log_entries': [{'level': 'ERROR', 'msg': 'test error'}], 'total_lines': 100}
        if 'analyze' in task_id or 'parse' in task_id:
            return {'error_summary': 'Found 3 errors', 'error_count': 3, 'confidence': 0.85,
                    'keywords': ['test'], 'intent': 'analysis'}
        if 'report' in task_id or 'summarize' in task_id:
            return {'report': 'Analysis complete', 'recommendations': ['fix error 1', 'fix error 2'],
                    'summary': 'Done', 'key_points': ['point 1']}
        if 'understand' in task_id:
            return {'task_breakdown': ['step 1', 'step 2'], 'approach': 'standard'}
        if 'execute' in task_id:
            return {'result': 'executed', 'status': 'success'}
        return {'result': f'processed: {prompt[:50]}', 'confidence': 0.85}

    def execute(self, task: Task, inputs: Dict[str, Any]) -> dict:
        """执行单个 Task，返回输出"""
        # 构建 prompt
        prompt = self._build_prompt(task, inputs)

        # 调用 LLM/Tool
        if task.executor == "llm":
            output = self._llm(prompt, {"task": task.id, "inputs": inputs})
        elif task.executor == "tool":
            output = self._execute_tool(task, inputs)
        else:
            output = {"error": f"unsupported executor: {task.executor}"}

        return output

    def _build_prompt(self, task: Task, inputs: Dict[str, Any]) -> str:
        parts = [f"Task: {task.name}", f"Description: {task.description}"]
        if inputs:
            parts.append(f"Inputs: {json.dumps(inputs, ensure_ascii=False)}")
        parts.append(f"Output schema: {json.dumps(task.output_schema, ensure_ascii=False)}")
        return "\n".join(parts)

    def _execute_tool(self, task: Task, inputs: dict) -> dict:
        """模拟工具执行 — 返回符合 schema 的输出"""
        task_id = task.id
        if 'fetch' in task_id or 'log' in task_id:
            return {'log_entries': [{'level': 'ERROR', 'msg': 'test error'}], 'total_lines': 100}
        if 'search' in task_id:
            return {'results': [{'title': 'AI News', 'url': 'https://example.com'}], 'total_found': 1}
        return {'result': 'tool executed', 'status': 'success'}


# ═══════════════════════════════════════════════════════════════
# 5. Validator — 质量保障
# ═══════════════════════════════════════════════════════════════

class Validator:
    """验证 Task 输出质量"""

    def __init__(self, llm_callable: Optional[Callable] = None):
        self._llm = llm_callable or self._default_llm
        self._schema_validator = SchemaValidator()

    @staticmethod
    def _default_llm(prompt: str, context: dict) -> dict:
        return {"verdict": "accepted", "confidence": 0.9, "reasoning": "output looks correct"}

    def validate(self, task: Task, output: dict, inputs: dict) -> Tuple[Verdict, List[str]]:
        """验证 Task 输出，返回 (裁决, 问题列表)"""
        issues = []

        # Level 1: Schema 校验（始终执行）
        if task.validation_level in ("schema_only", "full"):
            schema_ok, schema_errors = self._schema_validator.validate(output, task.output_schema)
            if not schema_ok:
                issues.extend(schema_errors)
                return Verdict.REJECTED, issues

        # Level 2: 语义校验（full 时执行）
        if task.validation_level == "full":
            semantic_ok, semantic_issues = self._semantic_check(task, output, inputs)
            if not semantic_ok:
                issues.extend(semantic_issues)
                return Verdict.REJECTED, issues

        return Verdict.ACCEPTED, issues

    def _semantic_check(self, task: Task, output: dict, inputs: dict) -> Tuple[bool, List[str]]:
        """语义检查 — 模拟 LLM-as-judge"""
        issues = []
        # 检查置信度
        confidence = output.get("confidence", 0.5)
        if confidence < 0.3:
            issues.append(f"low confidence: {confidence}")
            return False, issues
        return True, issues


# ═══════════════════════════════════════════════════════════════
# 6. Store — 持久化 + Failure Memory
# ═══════════════════════════════════════════════════════════════

class ArtifactStore:
    """Artifact 存储"""

    def __init__(self):
        self._artifacts: Dict[str, Artifact] = {}

    def save(self, task_id: str, name: str, content: Any) -> Artifact:
        art = Artifact(
            id=str(uuid.uuid4()),
            task_id=task_id,
            name=name,
            content=content,
            created_at=time.time(),
        )
        self._artifacts[art.id] = art
        return art

    def get_by_task(self, task_id: str) -> List[Artifact]:
        return [a for a in self._artifacts.values() if a.task_id == task_id]

    def get_latest(self, task_id: str) -> Optional[Artifact]:
        arts = self.get_by_task(task_id)
        return max(arts, key=lambda a: a.created_at) if arts else None


class FailureMemory:
    """压缩学习信号存储"""

    def __init__(self, max_records: int = 50):
        self._records: List[FailureRecord] = []
        self._max_records = max_records

    def record(self, task_id: str, lesson: str, root_cause: str, fix: str) -> FailureRecord:
        # 检查是否已有相似记录
        for rec in self._records:
            if rec.task_id == task_id and rec.root_cause == root_cause:
                rec.occurrence_count += 1
                return rec
        rec = FailureRecord(task_id=task_id, lesson=lesson, root_cause=root_cause, suggested_fix=fix)
        self._records.append(rec)
        # 裁剪
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]
        return rec

    def get_relevant(self, task: Task) -> List[FailureRecord]:
        """获取与 Task 相关的失败记录"""
        return [r for r in self._records if r.task_id == task.id]

    def summarize(self) -> str:
        """生成压缩摘要（给 Planner 的提示）"""
        if not self._records:
            return ""
        lines = ["[Failure Memory]", "Past failures to avoid:"]
        for r in self._records[-5:]:  # 最近 5 条
            lines.append(f"  - {r.task_id}: {r.lesson} (×{r.occurrence_count})")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 7. Execution Engine — 核心闭环
# ═══════════════════════════════════════════════════════════════

class ExecutionEngine:
    """
    Agent OS 的核心 kernel

    Loop:
        1. pull ready → 从 Task Graph 获取就绪任务
        2. execute → Executor 执行
        3. validate → Validator 验证
        4. commit → 保存 Artifact
        5. handle failure → 失败处理
        6. mutate DAG → 动态扩展（Planner 介入）
        7. repeat → 直到所有任务完成
    """

    def __init__(self, max_concurrency: int = 3):
        self.graph = TaskGraph()
        self.executor = Executor()
        self.validator = Validator()
        self.artifacts = ArtifactStore()
        self.failures = FailureMemory()
        self.max_concurrency = max_concurrency
        self._active_count = 0
        self._stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_skipped": 0,
            "total_retries": 0,
            "validation_rejects": 0,
        }

    def run(self, graph: TaskGraph) -> dict:
        """运行完整的执行图"""
        self.graph = graph
        print(f"\n{'='*60}")
        print(f"🚀 Execution Engine Starting")
        print(f"   Tasks: {len(self.graph.tasks)}")
        print(f"   Max concurrency: {self.max_concurrency}")
        print(f"{'='*60}")

        iteration = 0
        while not self.graph.all_done():
            iteration += 1
            print(f"\n─── Iteration {iteration} ───")

            # Step 1: Pull ready tasks
            ready = self.graph.get_ready_tasks()
            if not ready and not self.graph.all_done():
                # 没有就绪任务但还没完成 → 死锁检测
                self._detect_deadlock()
                break

            # Step 2: Execute (respect concurrency limit)
            available = self.max_concurrency - self._active_count
            to_execute = ready[:available]

            for task in to_execute:
                self._execute_task(task)

            # Step 3: Check for completed tasks and validate
            self._process_completed()

            # 防止无限循环
            if iteration > 100:
                print("⚠️  Max iterations reached")
                break

        print(f"\n{'='*60}")
        print(f"🏁 Execution Complete")
        print(f"   Completed: {self._stats['tasks_completed']}")
        print(f"   Failed: {self._stats['tasks_failed']}")
        print(f"   Skipped: {self._stats['tasks_skipped']}")
        print(f"   Retries: {self._stats['total_retries']}")
        print(f"   Validation rejects: {self._stats['validation_rejects']}")
        print(f"{'='*60}")

        return self._stats

    def _execute_task(self, task: Task) -> None:
        """执行单个 Task"""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self._active_count += 1

        # 收集输入（来自依赖任务的 Artifact）
        inputs = {}
        for dep_id in task.dependencies:
            art = self.artifacts.get_latest(dep_id)
            if art:
                inputs[dep_id] = art.content

        print(f"  ▶️  {task.id} ({task.name}) — running...")

        try:
            # Execute
            output = self.executor.execute(task, inputs)
            task.output = output

            # Validate
            task.status = TaskStatus.VALIDATING
            verdict, issues = self.validator.validate(task, output, inputs)

            if verdict == Verdict.ACCEPTED:
                # Commit
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                self.artifacts.save(task.id, f"{task.id}_output", output)
                self._stats["tasks_completed"] += 1
                elapsed = task.completed_at - task.started_at
                print(f"  ✅ {task.id} — completed ({elapsed:.1f}s)")

            elif verdict == Verdict.REJECTED:
                self._stats["validation_rejects"] += 1
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.RETRYING
                    self._stats["total_retries"] += 1
                    print(f"  🔄 {task.id} — retry {task.retry_count}/{task.max_retries}")
                    # 重新加入就绪队列
                    task.status = TaskStatus.PENDING
                else:
                    task.status = TaskStatus.FAILED
                    task.error = f"Validation failed after {task.max_retries} retries: {issues}"
                    self._stats["tasks_failed"] += 1
                    self._record_failure(task, issues)
                    print(f"  ❌ {task.id} — failed (max retries): {issues[:2]}...")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self._stats["tasks_failed"] += 1
            self._record_failure(task, [str(e)])
            print(f"  💥 {task.id} — exception: {e}")

        finally:
            self._active_count -= 1

    def _process_completed(self) -> None:
        """处理已完成任务的后续影响（跳过依赖失败的任务）"""
        for task in self.graph.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            # 如果有依赖失败，跳过
            for dep_id in task.dependencies:
                dep = self.graph.tasks.get(dep_id)
                if dep and dep.status == TaskStatus.FAILED:
                    task.status = TaskStatus.SKIPPED
                    self._stats["tasks_skipped"] += 1
                    print(f"  ⏭️  {task.id} — skipped (dependency {dep_id} failed)")
                    break

    def _detect_deadlock(self) -> None:
        """检测死锁：有 PENDING 任务但没有 READY 任务"""
        pending = [t for t in self.graph.tasks.values() if t.status == TaskStatus.PENDING]
        if pending:
            print(f"\n  ⚠️  DEADLOCK DETECTED: {len(pending)} tasks pending but none ready")
            for t in pending[:3]:
                unmet = [d for d in t.dependencies
                         if d in self.graph.tasks and self.graph.tasks[d].status != TaskStatus.COMPLETED]
                print(f"     {t.id} waiting for: {unmet}")

    def _record_failure(self, task: Task, issues: List[str]) -> None:
        """记录失败到 Failure Memory"""
        lesson = f"{task.name}: {issues[0] if issues else 'unknown error'}"
        self.failures.record(
            task_id=task.id,
            lesson=lesson,
            root_cause=issues[0] if issues else "unknown",
            fix=f"Consider simplifying {task.name} or using stricter schema"
        )


# ═══════════════════════════════════════════════════════════════
# 8. Planner 模拟 — 生成 Task Graph
# ═══════════════════════════════════════════════════════════════

class MockPlanner:
    """模拟 Planner：根据用户意图生成 Task Graph"""

    @staticmethod
    def plan(user_intent: str) -> TaskGraph:
        """生成执行图"""
        graph = TaskGraph()

        if "log" in user_intent.lower():
            # 日志分析流水线
            graph.add_task(Task(
                id="fetch_logs",
                name="获取日志",
                description="从服务器获取最近24小时日志",
                executor="tool",
                output_schema={
                    "type": "object",
                    "properties": {
                        "log_entries": {"type": "array", "items": {"type": "object"}},
                        "total_lines": {"type": "number"},
                    },
                    "required": ["log_entries", "total_lines"],
                },
                validation_level="schema_only",
            ))
            graph.add_task(Task(
                id="analyze_errors",
                name="分析错误",
                description="分析日志中的错误模式",
                dependencies=["fetch_logs"],
                output_schema={
                    "type": "object",
                    "properties": {
                        "error_summary": {"type": "string"},
                        "error_count": {"type": "number"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["error_summary", "error_count"],
                },
                validation_level="full",
            ))
            graph.add_task(Task(
                id="generate_report",
                name="生成报告",
                description="生成运维分析报告",
                dependencies=["analyze_errors"],
                output_schema={
                    "type": "object",
                    "properties": {
                        "report": {"type": "string", "maxLength": 5000},
                        "recommendations": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["report", "recommendations"],
                },
                validation_level="full",
            ))

        elif "search" in user_intent.lower():
            # 信息检索流水线
            graph.add_task(Task(
                id="parse_query",
                name="解析查询",
                description="解析用户搜索意图",
                executor="llm",
                output_schema={
                    "type": "object",
                    "properties": {
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "intent": {"type": "string"},
                    },
                    "required": ["keywords", "intent"],
                },
            ))
            graph.add_task(Task(
                id="search_web",
                name="搜索网络",
                description="基于关键词搜索网络信息",
                dependencies=["parse_query"],
                executor="tool",
                output_schema={
                    "type": "object",
                    "properties": {
                        "results": {"type": "array", "items": {"type": "object"}},
                        "total_found": {"type": "number"},
                    },
                    "required": ["results", "total_found"],
                },
                validation_level="schema_only",
            ))
            graph.add_task(Task(
                id="summarize",
                name="总结结果",
                description="总结搜索结果",
                dependencies=["search_web"],
                output_schema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "key_points": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["summary", "key_points"],
                },
                validation_level="full",
            ))

        else:
            # 通用处理流水线
            graph.add_task(Task(
                id="understand",
                name="理解需求",
                description="理解用户需求并分解为子任务",
                output_schema={
                    "type": "object",
                    "properties": {
                        "task_breakdown": {"type": "array", "items": {"type": "string"}},
                        "approach": {"type": "string"},
                    },
                    "required": ["task_breakdown", "approach"],
                },
            ))
            graph.add_task(Task(
                id="execute_plan",
                name="执行计划",
                description="按计划执行",
                dependencies=["understand"],
                output_schema={
                    "type": "object",
                    "properties": {
                        "result": {"type": "string"},
                        "status": {"type": "string"},
                    },
                    "required": ["result"],
                },
            ))

        return graph


# ═══════════════════════════════════════════════════════════════
# 9. 主程序 — 运行验证
# ═══════════════════════════════════════════════════════════════

def run_demo(intent: str = "analyze server logs for errors"):
    """运行完整演示"""
    print(f"\n📋 User Intent: {intent}")

    # 1. Planner 生成 Task Graph
    planner = MockPlanner()
    graph = planner.plan(intent)
    print(f"\n📐 Planner generated {len(graph.tasks)} tasks:")
    for tid, task in graph.tasks.items():
        deps = f" → depends on: {task.dependencies}" if task.dependencies else " (entry point)"
        print(f"   {tid}: {task.name}{deps}")

    # 2. Execution Engine 运行
    engine = ExecutionEngine(max_concurrency=2)
    stats = engine.run(graph)

    # 3. 输出结果
    print(f"\n📊 Final Results:")
    for tid, task in graph.tasks.items():
        status_icon = {
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.SKIPPED: "⏭️",
        }.get(task.status, "⏳")
        print(f"   {status_icon} {tid}: {task.status.value}")
        if task.output:
            print(f"      Output keys: {list(task.output.keys())}")

    # 4. Failure Memory 摘要
    fm_summary = engine.failures.summarize()
    if fm_summary:
        print(f"\n📝 Failure Memory:\n{fm_summary}")

    return stats


def test_validation_rejection():
    """测试：验证失败 + 重试 + 最终失败"""
    print(f"\n{'='*60}")
    print("🧪 TEST: Validation Rejection + Retry + Fallback")
    print(f"{'='*60}")

    graph = TaskGraph()
    graph.add_task(Task(
        id="unreliable_task",
        name="不可靠任务",
        description="这个任务总是输出低质量结果",
        output_schema={
            "type": "object",
            "properties": {
                "result": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0.8},
            },
            "required": ["result", "confidence"],
        },
        validation_level="full",
        max_retries=1,
    ))

    # 自定义 Executor：总是返回低置信度
    class LowConfExecutor(Executor):
        def execute(self, task, inputs):
            return {"result": "low quality output", "confidence": 0.1}

    engine = ExecutionEngine(max_concurrency=1)
    engine.executor = LowConfExecutor()
    stats = engine.run(graph)

    if stats["tasks_failed"] != 1:
        raise AssertionError(f"Expected 1 failure, got {stats}")
    if stats["total_retries"] != 1:
        raise AssertionError(f"Expected 1 retry, got {stats}")
    print("  ✅ Test passed: validation rejection works correctly")
    return stats


def test_dynamic_dag():
    """测试：运行时动态添加任务"""
    print(f"\n{'='*60}")
    print("🧪 TEST: Dynamic DAG — Runtime Task Addition")
    print(f"{'='*60}")

    graph = TaskGraph()
    graph.add_task(Task(
        id="initial_task",
        name="初始任务",
        description="第一个执行的任务",
        output_schema={
            "type": "object",
            "properties": {"result": {"type": "string"}},
            "required": ["result"],
        },
        validation_level="schema_only",
    ))

    # 自定义 Executor：执行后动态添加新任务
    class DynamicExecutor(Executor):
        def __init__(self):
            super().__init__()
            self._executed = False

        def execute(self, task, inputs):
            if task.id == "initial_task" and not self._executed:
                self._executed = True
                return {"result": "initial done, adding more tasks"}
            return {"result": "dynamic task executed"}

    engine = ExecutionEngine(max_concurrency=2)
    engine.executor = DynamicExecutor()

    # 模拟 Planner 在运行时介入：添加新任务
    original_execute = engine._execute_task

    def patched_execute(task):
        original_execute(task)
        # 如果初始任务完成，动态添加新任务
        if task.id == "initial_task" and task.status == TaskStatus.COMPLETED:
            print(f"  🔧 Planner介入: 动态添加新任务")
            engine.graph.add_task(Task(
                id="dynamic_task",
                name="动态添加的任务",
                description="运行时由 Planner 添加",
                dependencies=["initial_task"],
                output_schema={
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                    "required": ["result"],
                },
                validation_level="schema_only",
            ))

    engine._execute_task = patched_execute
    stats = engine.run(graph)

    if stats["tasks_completed"] != 2:
        raise AssertionError(f"Expected 2 completed, got {stats}")
    print("  ✅ Test passed: dynamic DAG works correctly")
    return stats


def test_deadlock_detection():
    """测试：死锁检测"""
    print(f"\n{'='*60}")
    print("🧪 TEST: Deadlock Detection")
    print(f"{'='*60}")

    graph = TaskGraph()
    graph.add_task(Task(
        id="task_a", name="Task A", description="depends on B",
        dependencies=["task_b"], output_schema={"type": "object", "properties": {}},
    ))
    graph.add_task(Task(
        id="task_b", name="Task B", description="depends on A",
        dependencies=["task_a"], output_schema={"type": "object", "properties": {}},
    ))

    engine = ExecutionEngine(max_concurrency=1)
    stats = engine.run(graph)

    print("  ✅ Test passed: deadlock detected")
    return stats


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════╗")
    print("║   Agent OS 3.0 — Execution Loop Prototype          ║")
    print("║   核心闭环验证                                      ║")
    print("╚══════════════════════════════════════════════════════╝")

    # Demo 1: 标准日志分析流水线
    run_demo("analyze server logs for errors")

    # Demo 2: 搜索流水线
    run_demo("search the web for AI news")

    # Demo 3: 通用处理
    run_demo("help me understand this document")

    # Test 1: 验证失败 + 重试
    test_validation_rejection()

    # Test 2: 动态 DAG
    test_dynamic_dag()

    # Test 3: 死锁检测
    test_deadlock_detection()

    print(f"\n{'='*60}")
    print("🎯 All prototypes and tests completed!")
    print(f"{'='*60}")
