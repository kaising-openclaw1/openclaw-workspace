# Agent OS 3.0 — Execution Graph System 最终架构

> 经过 Gemini 评审 + ChatGPT 6 轮深度切磋后的最终架构
> 核心跃迁：从"多 Agent 编排系统" → "可验证执行图计算系统"

---

## 一、架构演进历程

```
v1.0 (当前 5,107行)         v2.0 (初版设计 96,877行)      v3.0 (最终版 11-13.5K行)
────────────────────────    ────────────────────────    ────────────────────────
Agent 编排系统               多Agent团队拓扑               Execution Graph System
单 Agent 执行                6种拓扑 + Raft Lite          Task DAG + Executor Pool
无状态                       分布式状态机                   asyncio Scheduler
无验证                       Supervisor 仲裁               Planner + Validator 分离
无失败记忆                   6层上下文压缩                  Failure Memory + Recovery
```

**关键转折点：**
1. Gemini 指出：Raft Lite 是工具错配（语义问题用语义方式解决）
2. ChatGPT 指出：系统本质是"执行图"不是"Agent编排"
3. ChatGPT 指出：缺 Scheduler、Failure Memory、Execution Loop

---

## 二、最终架构（Execution Graph System）

```
User Request
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  Planner (LLM, temp=0.7)                              │
│  - 解析需求 → 生成初始 Task Graph                     │
│  - 修复不合法 DAG                                     │
│  - 每个 Task 有: input_schema / output_schema         │
│                   constraints / evaluator              │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│  Task Graph (Incremental DAG)                         │
│  - nodes: dict[task_id, Task]                         │
│  - edges: dict[task_id, list[dep_id]]                 │
│  - 3个操作: add_task / update_dependency / mark_done  │
│  - 运行时动态扩展 (Planner + Graph Mutator)            │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│  Scheduler (asyncio event loop)                       │
│  - ready_queue: asyncio.Queue                         │
│  - dependency-based activation                        │
│  - concurrency control: Semaphore(max_concurrency)    │
│  - retry scheduling                                   │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│  Executor Pool                                        │
│  - 每个 Executor = stateless execution wrapper        │
│  - validate_input → call_llm_or_tool → validate_output│
│  - concurrency + retry + timeout                      │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│  Validator + Consensus Gate                           │
│  (LLM, temp=0.1, 同模型不同角色)                       │
│  ├── Schema validation (确定性)                        │
│  ├── Claim overlap (Jaccard/embedding)                │
│  └── Contradiction detection (LLM-as-judge, 限定范围)  │
│  决策: schema_invalid→reject / contradiction→rerun    │
│        agreement→accept / 争议→Supervisor              │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│  Store (Artifact + World State + Failure Memory)      │
│  ├── Artifact Store: id/task_id/type/content          │
│  ├── WorldState: facts/open_tasks/resolved_tasks      │
│  └── Failure Memory: compressed learning signal       │
│      (max 3-5 per task, token budget cap)             │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│  Execution Engine (runtime/engine.py)                  │
│  ⭐ 整个系统的 kernel                                  │
│  Loop: pull ready → execute → validate → commit       │
│        → handle failure → mutate DAG → repeat         │
└──────────────────────────────────────────────────────┘
```

---

## 三、最终代码量预估（ChatGPT 修正版）

| 模块 | 文件 | 预估行数 |
|------|------|---------|
| **core/** | | |
| | core/scheduler.py | 900–1,100 |
| | core/task_graph.py | 800 |
| | core/state.py | 400 |
| | core/recovery.py | 400–600 |
| **planner/** | | |
| | planner/planner.py | 800–1,000 |
| **executor/** | | |
| | executor/executor.py | 700–900 |
| | executor/contract.py | 400 |
| **validator/** | | |
| | validator/schema_validator.py | 400 |
| | validator/consensus.py | 600 |
| | validator/graph_validator.py | 300 |
| **store/** | | |
| | store/artifact_store.py | 400 |
| | store/failure_memory.py | 400 |
| | store/world_state.py | 300 |
| **tools/** | | |
| | tools/registry.py | 300 |
| | tools/runtime.py | 500 |
| **runtime/** | | |
| | runtime/engine.py | 900–1,200 |
| | runtime/trace.py | 300–500 |
| **tests/** | | 3,000–4,500 |
| **合计** | **~18 文件** | **11,200–13,500** |

### 现有 5,107 行代码的复用策略

| 旧模块 | 复用方式 | 新模块 |
|--------|---------|--------|
| 事件总线 (309行) | ✅ 70-90% 复用 | core/scheduler.py backbone |
| 状态机 (271行) | ✅ 70-90% 复用 | core/state.py (Task lifecycle) |
| 插件系统 (290行) | ✅ 完全复用 | tools/runtime.py |
| 智力路由 (398行) | ⚠️ 30-50% 复用 | planner/planner.py |
| 加密引擎 (298行) | ✅ 保留 | security/ (后期) |
| 安全飞地 (392行) | ✅ 保留 | security/ (后期) |
| 可观测性 (380行) | ⚠️ 30-50% 复用 | runtime/trace.py |
| 存储层 (169行) | ⚠️ 部分复用 | store/ |
| Agent编排逻辑 | ❌ 重写 | 全部替换为 Task Graph |
| Mesh网络 (466行) | ❌ MVP阶段删除 | 后期分布式扩展时恢复 |
| 上下文管理 | ❌ 重写 | store/artifact_store.py |

---

## 四、成功率提升路径（修正版）

### 不是线性提升，而是"先降后升"

```
成功率
  │
90%│                    ┌────
  │               ┌─────┘
75%│         ┌────┘
  │    ┌─────┘
60%│────┘
  │
  │    Phase 1    Phase 2    Phase 3
  │    冷启动      收敛期      稳定期
  │    (20-40%     (75-85%)   (90%+)
  │    workload)
  └─────────────────────────────────── 时间
```

**Phase 1（冷启动，20-40% workload）：40-55%**
- DAG 约束过强，Planner 不适应
- Validator reject rate 高
- Scheduler 冷启动，ready queue 断流
- Failure memory 还没形成经验

**Phase 2（收敛期）：75-85%**
- Planner 学会生成合法 DAG
- Validator 阈值调优
- Failure memory 开始起作用
- Scheduler 达到稳态

**Phase 3（稳定期）：90%+**
- 所有组件协同工作
- 经验数据库积累足够
- 系统达到设计上限

### 缩短阵痛期的方法
1. **Warm-start 策略**：预置 10-20 个 golden task 的 DAG 模板
2. **渐进式约束**：先放宽 Validator 阈值，再逐步收紧
3. **Human-in-the-loop**：初期人工纠正 Planner 的 DAG 错误

---

## 五、多机扩展路径

```
MVP (单机)               Phase 2 (中心化+分布式)      Phase 3 (全分布式)
──────────               ──────────────────────      ─────────────────
Execution Engine         Engine (中心节点)            Mesh of Engines
Executor Pool (本地)     Executor Pool (远程节点)     每个节点独立 Engine
Artifact Store (本地)    Artifact Store (共享存储)    分布式 Artifact Store
                        通过 gRPC 通信               Raft Lite (数据层面)
                        复用现有 Mesh 网络           全对等网络
```

**MVP 阶段不做多机**，先用单机验证架构正确性。

---

## 六、与 Claude Code 的最终对比

| 维度 | Claude Code (512K TS) | Agent OS 3.0 (11-13.5K Python) |
|------|----------------------|-------------------------------|
| 核心范式 | 单 Agent + 工具调用 | 多 Task 执行图 + 验证 |
| 上下文管理 | 5 层压缩 | Artifact Store + Failure Memory |
| 成功率保障 | 隐式（依赖模型能力） | 显式（Validator + Consensus） |
| 多机支持 | ❌ | ✅ (Phase 2+) |
| 源码安全 | ❌ | ✅ (加密飞地) |
| 开源 | ❌ | ✅ MIT |
| 等效行数 | 512K TS | ~35-43K TS 等效 |

---

## 七、下一步行动

1. **写 Execution Loop prototype（200-400 行）** — 验证核心闭环
2. **实现 Scheduler + Task Graph** — 核心基础设施
3. **实现 Executor + Contract** — 执行层
4. **实现 Validator + Consensus** — 质量保障
5. **实现 Store (Artifact/Failure/State)** — 持久化
6. **集成测试** — 验证成功率提升
