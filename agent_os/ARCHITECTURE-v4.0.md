# Agent OS v4.0 — Execution Graph Architecture

> 综合 ChatGPT（6 轮深度评审）+ Gemini（1 轮架构评审）的交叉验证
> 目标：追上 → 对标 → 超越 Claude Code
> 基于 Claude Code 512K 行 TypeScript 源码逆向分析

---

## 一、核心定位

**Agent OS 是一个可验证执行图计算系统（Execution Graph System），不是 Agent 编排系统。**

```
❌ 原定位：多 Agent 编排系统（Supervisor + Worker）
✔️ 新定位：结构化任务执行 + 验证系统（Task DAG + Executors）
```

### 核心范式转变

| 维度 | 旧系统（v1.0/v2.0） | 新系统（v4.0） |
|------|-------------------|---------------|
| 单位 | Agent | Task |
| 状态 | 隐式（Agent 内部状态） | 显式（Task Graph + Artifact Store） |
| 协作 | Message Passing | Dependency Graph |
| 正确性 | 模糊（LLM 判断） | 可验证（Schema + Consensus） |
| 扩展 | 复杂度爆炸 | 结构化扩展 |

---

## 二、最终架构（MVP）

```
agent_os/
├── core/                          # 核心运行时
│   ├── scheduler.py     (900-1100 LOC)  # asyncio event loop + DAG activation
│   ├── task_graph.py    (800 LOC)       # Incremental DAG (nodes/edges/mutation)
│   ├── state.py         (400 LOC)       # Task lifecycle state machine
│   └── recovery.py      (300-500 LOC)   # Recovery policy registry
│
├── planner/
│   └── planner.py       (800-1000 LOC)  # LLM: 解析需求 → 生成/修复 DAG
│
├── executor/
│   ├── executor.py      (700-900 LOC)   # Stateless execution wrapper + pool
│   └── contract.py      (400 LOC)       # Pydantic schema + ExecutionContract
│
├── validator/
│   ├── schema_validator.py (400 LOC)    # Schema validation (确定性)
│   ├── consensus.py       (600 LOC)     # Claim overlap + contradiction detection
│   └── graph_validator.py (300 LOC)     # DAG 合法性校验 (cycle/orphan/dep)
│
├── store/
│   ├── artifact_store.py  (400 LOC)     # Artifact CRUD
│   ├── failure_memory.py  (400 LOC)     # Compressed failure records
│   └── world_state.py     (300 LOC)     # Global state + schema registry
│
├── tools/
│   ├── registry.py      (300 LOC)       # Tool registration
│   └── runtime.py       (500 LOC)       # Tool execution runtime
│
├── runtime/
│   ├── engine.py         (900-1200 LOC) # ⭐ Execution Loop (orchestrate all)
│   └── trace.py          (300-500 LOC)  # ⭐ Observability / Tracing
│
└── tests/                (3000-4500 LOC) # 多 Agent 系统测试
```

**总计：11,200 – 13,500 LOC（MVP 可运行版本）**

---

## 三、核心设计原则

### 原则 1：Execution Loop 是系统的心脏

```
User Request
    │
    ▼
┌──────────────┐
│   Planner    │  ← LLM (temp=0.7) 生成初始 DAG
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Task Graph  │  ← Incremental DAG, 运行时动态扩展
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Scheduler   │  ← asyncio event loop + dependency activation
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Executor Pool│  ← 并发执行 Task，schema 验证输入输出
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Validator   │  ← Schema + Consensus + Contradiction
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    Store     │  ← Artifact + Failure Memory + World State
└──────────────┘
```

### 原则 2：Scheduler = asyncio + DAG activation

- **不是操作系统 scheduler，不是分布式调度器**
- 只是一个 asyncio event loop 的轻量封装
- 核心职责：Task readiness management + concurrency control + retry routing
- 并发控制：`asyncio.Semaphore(max_concurrency)`
- 依赖激活：`on_task_completed → check children → enqueue ready`

### 原则 3：Planner/Validator 必须拆成两个 LLM 角色

- **Planner**：生成模型，temp=0.7，负责生成/修复 DAG
- **Validator**：判别模型，temp=0.1，负责检查输出一致性
- 同一个 base model，不同 prompt role + temperature
- 不能合并：否则 Planner 会自我合理化，Validator 会被污染

### 原则 4：只做"结构+约束一致性"，不做语义一致性判断

- Schema validation（确定性）→ Pydantic model_validate
- Claim overlap（弱语义）→ Jaccard / embedding cosine similarity
- Contradiction detection（限定范围）→ LLM-as-judge，只判断"是否矛盾"
- Consensus Gate 决策：schema_invalid → reject / contradiction → rerun / agreement → accept / else → escalate

### 原则 5：Failure Memory = 压缩学习信号，不是日志系统

- 三层存储策略：
  1. Hard limit per task：max 3-5 failures
  2. Token budget cap：超过触发压缩
  3. Retention policy：只保留 last failure + best failure + contradiction case
- 存储格式：`FailureRecord(task_id, failure_type, minimal_reason, fix_hint)`
- ❌ 不存：full LLM output / full chain-of-thought / redundant retries

### 原则 6：DAG = runtime mutable state，不是静态结构

- 不是 `DAG (fixed)`，而是 `DAG(t) = evolving graph`
- 3 个核心操作：`add_task`, `update_dependency`, `mark_complete`
- DAG 合法性校验：cycle detection + orphan node check + dependency existence
- ❌ 不做：optimal scheduling / semantic dependency correctness / graph optimization

---

## 四、Execution Loop 伪代码（核心 200 行级）

```python
class ExecutionEngine:
    def __init__(self, planner, scheduler, executor_pool, validator, store, max_steps=1000):
        self.planner = planner
        self.scheduler = scheduler
        self.executor_pool = executor_pool
        self.validator = validator
        self.store = store
        self.max_steps = max_steps
        self.step_counter = 0
        self.active = True

    async def run(self, user_request):
        # STEP 1: Plan initial DAG
        task_graph = await self.planner.generate(user_request)
        self.scheduler.load(task_graph)
        self.store.world_state.init_session(user_request)

        # STEP 2: Main loop
        while self.active and self.step_counter < self.max_steps:
            self.step_counter += 1

            # 2.1 Get ready tasks
            ready_tasks = self.scheduler.get_ready_tasks()
            if not ready_tasks and self.scheduler.is_idle():
                break

            # 2.2 Execute tasks concurrently
            running_futures = []
            for task in ready_tasks:
                future = self.executor_pool.submit(task)
                running_futures.append((task, future))
            results = await gather_all(running_futures)

            # 2.3 Validate outputs
            for task, output in results:
                if not self.validator.schema_validate(task, output):
                    self.handle_failure(task, output, "schema_error")
                    continue
                consensus = self.validator.consensus_check(task, output)
                if consensus == "reject":
                    self.handle_failure(task, output, "consensus_failure")
                    continue

                # 2.4 Commit artifact
                artifact = self.store.artifact_store.save(
                    task_id=task.id, content=output, type="result"
                )
                self.store.world_state.mark_completed(task.id)
                self.scheduler.mark_done(task.id)

            # 2.5 DAG mutation
            mutations = self.store.world_state.get_pending_mutations()
            for mutation in mutations:
                self.scheduler.graph.apply(mutation)

    def handle_failure(self, task, output, reason):
        self.store.failure_memory.record(task_id=task.id, output=output, reason=reason)
        strategy = self.validator.recovery_policy(task, reason)
        if strategy == "retry":
            self.scheduler.retry(task)
        elif strategy == "decompose":
            new_tasks = self.planner.refine(task, output)
            self.scheduler.add_tasks(new_tasks)
        elif strategy == "escalate":
            self.scheduler.escalate_to_parent(task)
```

---

## 五、成功率曲线预期

```
成功率
 90%+  ┤───────────────────────────────────●─── 稳定期
 85%   ┤                              ●────
 75%   ┤                    ●─────────         收敛期
 55%   ┤           ●───────
 40%   ┤    ●──────                       冷启动期
       └──────────────────────────────────────────
          0    20%    40%    60%    80%   100%
                      workload 完成度
```

- **冷启动期（0-20% workload）**：成功率 40-55%，DAG 约束过强、Validator reject rate 高
- **收敛期（20-60% workload）**：成功率 75-85%，Failure Memory 形成经验
- **稳定期（60%+ workload）**：成功率 90%+，系统收敛

**缩短阵痛期的 3 个方法：**
1. Warm-start DAG templates（FAQ / coding / reasoning / retrieval 模板）
2. Bootstrap failure memory（预置常见失败模式）
3. Relaxed validation mode（前 100 tasks 降低阈值）

---

## 六、多机扩展路径

```
MVP (Phase 1)           Phase 2                  Phase 3
┌──────────────┐   ┌──────────────┐        ┌──────────────┐
│  Engine (1)  │   │  Engine (1)  │        │  Engine A    │── Mesh ── Engine B
│  Single node │   │  Centralized │        │  Peer-to-peer│
│  asyncio     │   │  Scheduler   │        │  Full DAG    │
└──────────────┘   └──────┬───────┘        │  replication │
                          │                └──────────────┘
                 ┌────────┼────────┐
                 ▼        ▼        ▼
           Worker 1  Worker 2  Worker 3
           (gRPC)    (gRPC)    (gRPC)
```

- **MVP**：单机 asyncio，所有组件同进程
- **Phase 2**：中心化 Engine + 分布式 Executor Pool（gRPC workers）
- **Phase 3**：全对等 Mesh of Engines（需要分布式 DAG consensus）
- ❌ MVP 不做：fully distributed engine、Mesh network

---

## 七、与 Claude Code 的差距与差异化

### 差距分析

| 维度 | Claude Code | Agent OS v4.0 | 差距 |
|------|------------|---------------|------|
| 核心 Loop | 200 行 while 循环 | 900-1200 行 Execution Engine | ⚠️ 略复杂 |
| 上下文压缩 | 5 层（生产验证） | 0 层（MVP 不做） | ❌ 最大差距 |
| 工具系统 | 40+ 工具（80,000 行） | 2 文件（800 行） | ❌ |
| 权限系统 | 4 路竞速（15,000 行） | 0 行 | ❌ |
| 子 Agent | 隔离上下文（20,000 行） | 0 行 | ❌ |
| 终端 UI | Ink React（60,000 行） | CLI（420 行） | ❌ |
| MCP 协议 | 完整实现（30,000 行） | 0 行 | ❌ |
| **可验证执行图** | ❌ 无 | ✅ 核心差异化 | 🏆 优势 |
| **Failure Memory** | ❌ 无 | ✅ 核心差异化 | 🏆 优势 |
| **多机扩展** | ❌ 单机 | ✅ 规划中 | 🏆 优势 |

### 差异化方向

```
Claude Code 有的（我们追）：
  └─ 上下文压缩（Phase 2）
  └─ 工具系统（Phase 2）
  └─ 权限系统（Phase 3）

Claude Code 没有的（我们超越）：
  └─ 可验证执行图 ✅ 核心差异化
  └─ Failure Memory ✅ 核心差异化
  └─ 多机 Mesh（Phase 3）
```

---

## 八、旧代码复用策略（5,107 LOC → v4.0）

| 旧模块 | 复用策略 | 新模块 |
|--------|---------|--------|
| Event Bus | 70-90% 复用 | core/scheduler.py backbone |
| State Machine | 70-90% 复用 | core/state.py (Task lifecycle) |
| Plugin System | 完全复用 | tools/runtime.py |
| Agent orchestration | 30-50% 复用（拆 decision logic） | core/task_graph.py + planner/planner.py |
| Mesh network | MVP 阶段砍掉 | — |
| Agent hierarchy | 完全重写 | — |
| Context system | 完全重写 | store/artifact_store.py + failure_memory.py + world_state.py |

### 重构步骤（严格顺序）

1. **Phase 0**：冻结旧系统
2. **Phase 1**：写 Execution Engine prototype（200-400 LOC）
3. **Phase 2**：双系统并行（旧系统 + 新 Engine 对比）
4. **Phase 3**：替换 scheduler layer
5. **Phase 4**：替换 executor layer
6. **Phase 5**：逐步删除 agent logic

---

## 九、最大工程风险与缓解

| 风险 | 描述 | 缓解策略 |
|------|------|---------|
| DAG 状态爆炸 | 动态扩展导致无限膨胀 | Hard limit per task + Token budget cap |
| 环路死锁 | Planner 插入节点形成隐式依赖环 | Cycle detection + fallback to Planner repair |
| Validator 延迟崩塌 | 串行 LLM 验证抹平异步优势 | 只做结构+约束一致性，不做语义判断 |
| Token 成本爆炸 | Consensus Gate 多次 LLM 调用 | 同模型不同 temperature，复用 cache |
| 冷启动成功率低 | 40-55% 初期成功率 | Warm-start templates + bootstrap failure memory |

---

## 十、下一步行动

1. **Phase 1**：写 Execution Loop prototype（200-400 LOC）→ 验证核心闭环
2. **Phase 2**：实现 Scheduler + Task Graph → 替换旧 Event Bus
3. **Phase 3**：实现 Executor Pool + Contract → 替换旧 Plugin System
4. **Phase 4**：实现 Validator + Consensus Gate → 增加验证层
5. **Phase 5**：实现 Store（Artifact + Failure Memory + World State）
6. **Phase 6**：集成测试 + 调优

> 核心哲学：把精力从"让 LLM 变聪明"转移到"假设 LLM 随时掉链子、网络随时断开、内存随时 OOM 时的系统级容错"。
