# Agent OS v6.0 — 自我进化的 Agent 运行时架构

> 基于 2026-06-26 全面技术史研究 + Claude Code 512K 行源码逆向 + 行业框架对比
> 核心差异化：**可验证执行图 + 自我进化 + 原生多模态 Agent**
> 不做 Claude Code 的平替，做 Claude Code 做不到的事

---

## 零、AI Coding Agent 技术发展全史（2013-2026）

### 0.1 奠基期（2013-2020）：从 Embedding 到 In-Context Learning

```
2013  word2vec          ── 代码/Token 的语义可计算化
2014  Seq2Seq + Attention ── 编码器-解码器 + 长程对齐
2016  DeepCoder          ── 搜索+学习的程序合成，Agentic Tool Loop 的雏形
2017  Transformer        ── 并行上下文缩放，一切的基础
2019  GPT-2              ── 零样本迁移，代码生成的可能性
2020  GPT-3              ── In-Context Learning，"提示即编程"
```

**关键洞察**：这个阶段的工具（TabNine, Kite）只是"更聪明的自动补全"，没有 Agent 概念。模型能力是瓶颈，不是架构。

### 0.2 爆发期（2021-2023）：Copilot → ChatGPT → AutoGPT

```
2021.06  GitHub Copilot (Codex)  ── 第一个商用 AI 编程工具，自动补全→整行/整函数
2022.10  ReAct                    ── 推理+工具使用的第一类循环范式
2023.03  GPT-4                    ── 多文件推理能力，Agent 的经济学拐点
2023.03  Claude 1 (100K ctx)     ── 首个大上下文窗口，整库理解成为可能
2023.05  AutoGPT                  ── 递归自主 Agent 的普及（和失败模式暴露）
2023.11  GPTs + Code Interpreter  ── 工具调用+可执行反馈成为标准
```

**关键洞察**：GPT-4 和 Claude 100K 是真正的拐点。AutoGPT 证明了"自主 Agent"的可行性，也暴露了"没有验证循环的自主=灾难"。

### 0.3 分化期（2024-2025）：AI-Native IDE → 自主 Agent

```
2024.03  Claude 3 Opus          ── 最强编码模型，Sonnet 性价比拐点
2024.06  Claude 3.5 Sonnet      ── 里程碑：Opus 级能力，Sonnet 价格
2024.10  Cursor ($100M ARR)     ── AI-Native IDE 验证：开发者愿意换工具
2024.11  Bolt.new / Lovable     ── 自然语言→全栈应用，非开发者也能编程
2025.02  Claude Code (Research Preview) ── 终端原生 Agent，CLI-first
2025.05  Claude 4 Opus          ── Anthropic 4.5x 收入增长
2025.06  Devin                  ── "第一个 AI 软件工程师"，沙箱隔离
2025.12  OpenAI Codex CLI       ── 云端优先的 Agent 方案
```

**关键洞察**：Cursor 证明了"AI-Native 体验"的价值。Claude Code 证明了"终端 Agent"的可行性。Devin 证明了"沙箱隔离"的必要性。但所有这些系统都有一个共同盲点：**它们不会从失败中学习**。

### 0.4 成熟期（2026）：Agent 框架大战 + Claude Code 源码泄露

```
2026.01  LangGraph 1.0          ── 图状态机成为生产级 Agent 标准
2026.02  Claude Opus 4.8        ── 当前最强编码模型
2026.03  Claude Code 源码泄露   ── 512K 行 TypeScript，1,900 文件
2026.03  KAIROS / ULTRAPLAN     ── 泄露揭示的 44 个未发布功能
2026.04  claw-code (Rust 重写)  ── 社区 20K 行 Rust 逆向工程
2026.05  MCP + A2A 协议         ── Agent 互操作性标准形成
2026.06  Cursor + Claude Code 双雄 ── 市场格局基本确定
```

**关键洞察**：Claude Code 源码泄露是行业转折点——它揭示了"Agent 的护城河不在模型，在工程系统"。1,900 个文件、512K 行代码中，模型调用只有几十行。剩下的全是：上下文管道、工具系统、权限模型、多 Agent 编排、记忆系统、安全沙箱。

### 0.5 历史给我们的 7 条铁律

```
1. 模型能力是商品，工程系统是护城河
   └─ Claude Code 512K 行中模型调用 < 0.1%

2. 核心循环必须极简（~200 行），复杂度推到外围
   └─ Claude Code 的 while True 只有 200 行

3. 上下文管理是 #1 工程挑战
   └─ 14 个缓存失效向量、5 层压缩、4 阶段管道

4. 安全不是围墙，是竞速
   └─ 4 路并行审批（User → Hook → Classifier → Bridge）

5. 子 Agent 隔离是架构决策，不是功能
   └─ 独立上下文窗口、独立工具集、独立模型选择

6. 验证缺失是自主 Agent 的头号杀手
   └─ AutoGPT 的教训：没有验证的自主 = 灾难

7. 自我进化是最后一个未攻克的堡垒
   └─ Claude Code 做不到（512K LOC 不敢改），Cursor 做不到（商业产品），
       LangGraph 做不到（框架无自省），只有我们能做（从零设计）
```

---

## 一、战略定位：Agent OS 的独特性

### 1.1 竞争格局定位

```
                   生产级
                    │
                    │
    Claude Code ◄───┼───► Cursor
    (终端 Agent)    │    (IDE Agent)
                    │
                    │
    传统框架 ◄──────┼───────► Agent OS ←── 我们在这里
    (LangGraph/     │           │
     CrewAI)        │           │
                    │           ▼
                实验级        自我进化
```

### 1.2 我们 vs 所有竞品

| 维度 | Claude Code | Cursor | LangGraph | Agent OS v6.0 |
|------|------------|--------|-----------|---------------|
| 代码量 | 512K LOC | ~200K LOC | ~100K LOC | **~15K LOC** |
| 核心语言 | TypeScript | TypeScript | Python/JS | **Python** |
| 执行模型 | 扁平消息 | 扁平消息 | 图状态机 | **扁平+DAG 双模** |
| 上下文压缩 | 5 层（生产验证） | 3 层 | 无 | **5 层（对标）** |
| 工具系统 | 40+ 工具（80K LOC） | 插件系统 | 工具注册 | **20 工具 MVP** |
| 权限模型 | 4 路竞速 | 简单确认 | 无 | **3 层分级** |
| 子 Agent | 隔离上下文 | 无 | 通过图实现 | **原生隔离** |
| **验证机制** | ❌ 无 | ❌ 无 | ❌ 无 | **✅ L0+L1+L2** |
| **失败学习** | ❌ 无 | ❌ 无 | ❌ 无 | **✅ Failure Memory** |
| **自我进化** | ❌ 不可能 | ❌ 不可能 | ❌ 不可能 | **✅ Meta-Layer** |
| 多机 | ❌ 单机 | ❌ 单机 | ❌ 单机 | **✅ Mesh（Phase 2）** |
| MCP 协议 | ✅ 原生 | ✅ 插件 | ✅ LangChain | **✅ 原生** |
| A2A 协议 | ❌ 无 | ❌ 无 | ❌ 无 | **✅ 原生** |

### 1.3 核心差异化（三句话）

1. **Claude Code 能做的，我们都能做**（文件读写、代码搜索、命令执行、Git 集成）
2. **Claude Code 做不到的，我们能做**（可验证执行、失败学习、自我进化）
3. **Claude Code 不敢做的，我们敢做**（系统自我修改、架构自动优化）

---

## 二、核心架构：三层 + 双环

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   █████  ██████  ███████ ███    █ ████████  █████  ██████           │
│  ██      ██   ██ ██      ████   █    ██    ██   ██ ██   ██          │
│  ███████ ██████  █████   ██ ██  █    ██    ███████ ██████           │
│       ██ ██   ██ ██      ██  ██ █    ██    ██   ██ ██              │
│  ██████  ██   ██ ███████ ██   ████    ██    ██   ██ ██              │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  LAYER 1: BOOTSTRAP（信任根, ~500 LOC）                      │   │
│  │  永远手写，永远不改。启动加载 + 健康监控 + 回滚保护          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                               │                                     │
│                               ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  LAYER 2: EXECUTION ENGINE（执行引擎, ~10K LOC）             │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  外环：对话循环（Conversation Loop, ~300 LOC）        │   │   │
│  │  │  while True:                                          │   │   │
│  │  │    user_input = await read_stdin()                    │   │   │
│  │  │    context = compress(history)                        │   │   │
│  │  │    action = await model.generate(context)             │   │   │
│  │  │    permission = await race_permission(action)         │   │   │
│  │  │    if approved: result = await execute(action)        │   │   │
│  │  │    history.append(result)                             │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                               │                               │   │
│  │                               ▼                               │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  内环：执行图循环（Execution Graph Loop, ~2K LOC）    │   │   │
│  │  │  当任务需要多步验证时，从外环切换到内环：              │   │   │
│  │  │  Planner → Task Graph → Scheduler → Executor →       │   │   │
│  │  │  Validator → Store → Failure Memory                   │   │   │
│  │  │  内环是可选升级路径，不是强制抽象                      │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │   │
│  │  │ 上下文    │ │ 工具系统  │ │ 权限模型  │ │ 子 Agent     │   │   │
│  │  │ 管道(5层) │ │ (20工具) │ │ (3层分级) │ │ (隔离上下文) │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                               │                                     │
│                               ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  LAYER 3: META-LAYER（进化层, ~4K LOC）                      │   │
│  │                                                              │   │
│  │  Monitor → Analyzer → Evolution Manager → Verifier → Deploy │   │
│  │                                                              │   │
│  │  进化范围安全分级：                                           │   │
│  │  L0 参数调优 → 自动                                         │   │
│  │  L1 提示词优化 → 自动+沙箱                                  │   │
│  │  L2 工具注册表 → 人类审批                                   │   │
│  │  L3 核心循环 → 人类审批+冷却期                              │   │
│  │  ❌ Bootstrap → 永远不允许                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.1 双环设计详解

这是 v6.0 最核心的架构决策。借鉴 Claude Code 的"扁平消息"和 v4.0 的"执行图"，我们选择**双模运行**：

```
外环（对话循环）：
  适用场景：日常编码（文件编辑、代码搜索、简单问答）
  复杂度：~300 LOC
  延迟：低（无 DAG 开销）
  验证：无（信任模型输出）

内环（执行图循环）：
  适用场景：复杂任务（多步重构、测试生成、安全敏感操作）
  复杂度：~2,000 LOC
  延迟：中（DAG 调度开销）
  验证：L0 Schema + L1 语义 + L2 共识

切换条件：
  1. 用户显式请求（/plan, /verify）
  2. 任务复杂度超过阈值（>3 步）
  3. 安全敏感操作自动触发
  4. 历史同类任务失败率 > 30%
```

**为什么不是纯 DAG？**
Claude Code 用扁平消息取得了巨大成功。纯 DAG 在简单场景下是过度抽象。双环设计让我们在简单场景保持 Claude Code 级的低延迟，在复杂场景获得可验证执行。

**为什么不是纯扁平？**
纯扁平没有验证。对于自主 Agent，没有验证意味着同样的错误会重复发生。内环的 Failure Memory 让系统从错误中学习——这是 Claude Code 做不到的。

### 2.2 上下文管道（5 层压缩）

直接从 Claude Code 源码逆向的核心竞争力：

```
Stage 1: 原始采集
  ├─ 文件系统（AST 解析，只读函数签名+相关代码块）
  ├─ Git 历史（最近变更、分支信息）
  ├─ 终端输出（最后 N 行）
  └─ 用户输入

Stage 2: 智能压缩（触发条件：上下文窗口 > 80%）
  ├─ MicroCompact：本地裁剪旧工具输出，零 API 调用
  ├─ AutoCompact：预留 13K token 缓冲，生成 20K token 结构化摘要
  └─ Full Compact：压缩全部对话，重注入最近文件（≤5K token/文件）

Stage 3: 缓存优化
  ├─ 追踪 14 个缓存失效向量
  ├─ Sticky Latch：检测到缓存断裂后锁定当前模式
  └─ 目标：prompt cache hit rate > 70%

Stage 4: 注入检测
  ├─ 可信/不可信来源标记系统
  ├─ 外部内容（文件、网页、MCP 返回）→ 注入扫描
  └─ 危险模式拦截

Stage 5: 预算管理
  ├─ Token 预算分配（系统提示 20% / 对话历史 50% / 工具输出 30%）
  ├─ 超预算时自动触发压缩
  └─ 压缩失败断路器（连续 3 次失败后停止重试）
```

### 2.3 工具系统（20 个核心工具）

借鉴 Claude Code 的 40+ 工具设计，但精简到 20 个核心：

```
读操作（Auto-Allow）:
  ├─ read_file        ── 读取文件（支持行范围）
  ├─ search_code      ── 语义/正则搜索
  ├─ grep             ── 快速文本搜索
  ├─ list_directory   ── 目录列表
  ├─ file_info        ── 文件元信息
  ├─ git_log          ── Git 历史
  └─ git_diff         ── 变更对比

写操作（Requires Confirmation）:
  ├─ write_file       ── 写入文件
  ├─ edit_file        ── 精确编辑
  ├─ rename_file      ── 重命名
  ├─ delete_file      ── 删除文件
  ├─ create_directory ── 创建目录
  └─ git_commit       ── Git 提交

执行操作（Requires Confirmation + 沙箱）:
  ├─ run_command      ── 执行 Shell 命令
  ├─ run_python       ── 执行 Python 代码
  └─ run_test         ── 运行测试

Agent 操作（Requires Confirmation）:
  ├─ spawn_sub_agent  ── 生成子 Agent（隔离上下文）
  ├─ plan             ── 生成执行计划（切换到内环）
  └─ verify           ── 验证当前结果

MCP 操作（Auto-Allow 读 / Confirmation 写）:
  ├─ mcp_call         ── 调用 MCP 工具
  └─ a2a_call         ── 调用 A2A Agent
```

每个工具的定义结构（借鉴 Claude Code 的声明式设计）：

```python
@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict          # JSON Schema
    output_schema: dict         # JSON Schema
    permission_level: str       # "auto" | "confirm" | "prohibited"
    timeout_seconds: int
    risk_level: str             # "read" | "write" | "exec" | "agent"
    mcp_compatible: bool        # 是否暴露为 MCP 工具
```

### 2.4 权限模型（3 层分级 + 4 路竞速）

借鉴 Claude Code 的 4 路权限竞速，但简化到实用级别：

```
┌─────────────────────────────────────────────────────┐
│  用户输入                                            │
│     │                                                │
│     ▼                                                │
│  ┌─────────────────────────────────────────────┐    │
│  │  权限竞速（并行）                              │    │
│  │                                                │    │
│  │  Route 1: 用户策略 → 全局/项目级预设规则       │    │
│  │  Route 2: 风险分类器 → ML 模型评估操作风险     │    │
│  │  Route 3: 上下文规则 → 当前状态特殊规则        │    │
│  │  Route 4: 用户实时 → 终端提示用户确认          │    │
│  │                                                │    │
│  │  最快返回的路线决定权限结果                      │    │
│  └─────────────────────────────────────────────┘    │
│     │                                                │
│     ▼                                                │
│  ┌─────────────────────────────────────────────┐    │
│  │  权限结果                                      │    │
│  │  ├─ ALLOW（任何路线批准）                      │    │
│  │  ├─ DENY（任何路线拒绝）                       │    │
│  │  └─ CONFIRM（需要用户确认）                    │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

### 2.5 子 Agent 系统（隔离上下文模式）

直接采用 Claude Code 的 AgentTool 模式：

```
主 Agent 上下文（~50K tokens）
  ├─ 系统提示
  ├─ 对话历史
  └─ 当前任务状态
       │
       ├─ spawn_sub_agent("search_codebase", model="haiku")
       │    └─ 子 Agent 上下文（完全隔离，~20K tokens）
       │         ├─ 独立系统提示
       │         ├─ 独立对话历史
       │         └─ 独立工具集（只读）
       │              └─ 返回：5 行结论
       │
       └─ spawn_sub_agent("refactor_module", model="opus")
            └─ 子 Agent 上下文（完全隔离，~80K tokens）
                 ├─ 独立系统提示
                 ├─ 独立对话历史
                 └─ 独立工具集（读写）
                      └─ 返回：重构后的文件列表

关键设计：
  - 子 Agent 可以指定不同模型（省钱：Haiku 搜索，Opus 重构）
  - 子 Agent 的上下文不污染主 Agent（搜索 100 个文件 ≠ 主 Agent 读 100 个文件）
  - 子 Agent 可以有自己的工具集（搜索 Agent 只有读工具）
```

---

## 三、自我进化机制（Meta-Layer）

### 3.1 为什么这是我们的核武器

```
Claude Code 做不到自我进化的原因：
  1. 512K LOC → 修改风险极高，没有人敢改
  2. 没有验证层 → 改了也不知道对不对
  3. 商业产品 → 不允许"自我修改"
  4. 没有 Failure Memory → 每次失败都是孤立事件

Agent OS 能做到的原因：
  1. 15K LOC → 修改风险可控
  2. 有 Validator → 改了可以验证
  3. 从零设计 → "自我进化"是核心能力，不是事后补丁
  4. 有 Failure Memory → 失败经验可以指导进化方向
```

### 3.2 进化流程

```
┌─────────────────────────────────────────────────────────────┐
│  1. Monitor（持续采集）                                      │
│     ├─ 任务成功率（按类型：文件编辑、代码搜索、命令执行等）   │
│     ├─ 工具调用失败率（哪个工具最容易失败？）                 │
│     ├─ 用户反馈（隐式：是否接受结果？显式：/feedback）       │
│     ├─ 性能指标（延迟 P50/P95/P99、Token 消耗）              │
│     └─ 验证通过率（内环的 L0/L1/L2 通过率）                  │
│                                                              │
│  2. Analyzer（定期分析）                                      │
│     ├─ 识别失败模式（聚类：哪些任务经常失败？）               │
│     ├─ 定位低效环节（哪个阶段 Token 消耗最高？）              │
│     └─ 生成改进建议（LLM 分析 + 统计显著性检验）             │
│                                                              │
│  3. Evolution Manager（生成补丁）                             │
│     ├─ 基于 Failure Memory 生成修复                          │
│     ├─ 在沙箱中运行验证（完整测试套件）                       │
│     ├─ 通过 Verifier 检查（回归检测）                        │
│     └─ 根据安全级别选择部署策略                              │
│                                                              │
│  4. Deploy（安全部署）                                        │
│     ├─ L0: 自动部署（参数调优）                              │
│     ├─ L1: 自动 + 沙箱通过（提示词优化）                     │
│     ├─ L2: 人类审批（工具注册表修改）                        │
│     └─ L3: 人类审批 + 冷却期（核心循环修改）                 │
│                                                              │
│  5. Rollback（失败回滚）                                      │
│     ├─ 每次修改前备份                                        │
│     ├─ 部署后监控 100 Task 或 1h                             │
│     └─ 成功率下降 > 10% → 自动回滚                          │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 进化范围详细定义

```
L0 — 参数调优（自动，无风险）
  ├─ temperature（0.1-0.9）
  ├─ max_tokens（512-8192）
  ├─ retry_count（1-5）
  ├─ timeout_seconds（30-300）
  ├─ max_concurrency（1-10）
  └─ compression_threshold（70-95%）

L1 — 提示词优化（自动+沙箱，低风险）
  ├─ system_prompt（核心角色定义）
  ├─ tool_descriptions（工具描述文本）
  ├─ validation_criteria（验证标准）
  ├─ error_message_templates（错误提示模板）
  └─ sub_agent_prompts（子 Agent 提示词）

L2 — 工具注册表（人类审批，中风险）
  ├─ 新增工具
  ├─ 修改工具参数/返回值 schema
  ├─ 修改工具权限级别
  ├─ 修改 MCP 暴露配置
  └─ 新增/修改安全规则

L3 — 核心循环（人类审批+冷却期，高风险）
  ├─ Execution Loop 逻辑修改
  ├─ 上下文压缩策略修改
  ├─ 权限竞速逻辑修改
  ├─ 子 Agent 调度策略修改
  └─ 验证流程修改

❌ — Bootstrap（永远不允许修改）
  ├─ loader.py
  ├─ guardian.py（回滚保护）
  ├─ verifier.py（验证器本身）
  └─ evolution_memory.py（进化记录）
```

---

## 四、执行引擎详细设计

### 4.1 外环：对话循环（~300 LOC）

```python
# Agent OS v6.0 — 核心对话循环
# 借鉴 Claude Code 的 200 行哲学，但加入双环切换

class ConversationLoop:
    """外环：日常编码对话"""

    def __init__(self):
        self.history = MessageHistory()
        self.context = ContextPipeline()    # 5 层压缩
        self.tools = ToolRegistry()         # 20 个核心工具
        self.permission = PermissionRacer() # 4 路竞速
        self.agent_tool = AgentTool()       # 子 Agent 工厂
        self.engine = ExecutionEngine()     # 内环引擎

    async def run(self):
        while True:
            # 1. 读取用户输入
            user_input = await self.read_input()

            # 2. 检查是否切换到内环
            if self.should_use_execution_graph(user_input):
                result = await self.engine.run_task(user_input)
                self.history.append(result)
                continue

            # 3. 构建上下文（5 层管道）
            context = await self.context.build(self.history)

            # 4. LLM 生成下一步
            response = await self.llm.generate(context)

            # 5. 处理工具调用
            if response.has_tool_calls:
                for tool_call in response.tool_calls:
                    # 权限竞速
                    decision = await self.permission.race(tool_call)
                    if decision == DENY:
                        self.history.append(f"❌ 权限拒绝: {tool_call.name}")
                        continue
                    if decision == CONFIRM:
                        if not await self.user_confirm(tool_call):
                            self.history.append(f"⏭️ 用户取消: {tool_call.name}")
                            continue

                    # 执行工具
                    result = await self.tools.execute(tool_call)
                    self.history.append(result)
            else:
                # 纯文本回复
                self.history.append(response.text)

            # 6. 自动上下文管理
            if self.context.usage_ratio > 0.8:
                await self.context.compress(self.history)
```

### 4.2 内环：执行图循环（~2,000 LOC）

基于 v4.0/v5.0 的已验证原型（engine_prototype.py, 917 LOC），核心流程：

```
1. Planner（LLM, temp=0.7）
   └─ 用户需求 → Task Graph（DAG）
   └─ 参考 Failure Memory 避免历史错误

2. Task Graph（增量 DAG）
   └─ 运行时动态扩展
   └─ 死锁检测（BFS）
   └─ 依赖满足检查

3. Scheduler（asyncio event loop）
   └─ 就绪任务队列
   └─ 并发控制（Semaphore）
   └─ 依赖激活（on_task_completed → check children → enqueue）

4. Executor（LLM + Tool）
   └─ LLM 执行器（调用模型 API）
   └─ Tool 执行器（调用工具系统）
   └─ Code 执行器（沙箱运行代码）

5. Validator（3 层验证）
   ├─ L0: Schema 校验（JSON Schema 匹配）
   ├─ L1: 语义校验（LLM-as-Judge, temp=0.1）
   └─ L2: 共识校验（多模型交叉验证，可选）

6. Artifact Store
   └─ Task 输出持久化
   └─ 依赖任务输入收集

7. Failure Memory
   └─ 失败记录（task_id, lesson, root_cause, fix）
   └─ Planner 参考（避免重复错误）
   └─ 进化信号（Meta-Layer 使用）
```

### 4.3 外环→内环切换条件

```python
def should_use_execution_graph(self, user_input: str) -> bool:
    """判断是否需要切换到内环（执行图模式）"""

    # 1. 用户显式请求
    if user_input.startswith("/plan") or user_input.startswith("/verify"):
        return True

    # 2. 任务复杂度估计
    complexity = self.estimate_complexity(user_input)
    if complexity > COMPLEXITY_THRESHOLD:  # >3 步
        return True

    # 3. 安全敏感操作
    if self.is_safety_sensitive(user_input):
        return True

    # 4. 历史失败模式
    similar_failures = self.failure_memory.get_similar(user_input)
    if similar_failures and similar_failures[0].occurrence_count > 3:
        return True

    # 5. 用户设置（总是/从不使用内环）
    return self.user_prefs.force_execution_graph
```

---

## 五、与 Claude Code 的深度对标

### 5.1 功能对标矩阵

| Claude Code 功能 | Agent OS v6.0 | 实现策略 |
|-----------------|---------------|---------|
| 文件读写 | ✅ Phase 0 | 直接实现 |
| 代码搜索 | ✅ Phase 0 | ripgrep + AST 解析 |
| 命令执行 | ✅ Phase 0 | 沙箱执行 |
| Git 集成 | ✅ Phase 1 | gitpython |
| 终端 UI | ✅ Phase 1 | Rich + Prompt Toolkit |
| 会话管理 | ✅ Phase 1 | SQLite 持久化 |
| 项目上下文 | ✅ Phase 1 | .clinerules 等效 |
| 5 层上下文压缩 | ✅ Phase 1 | 逆向实现 |
| 40+ 工具系统 | ✅ Phase 2 | 20 核心 + 插件扩展 |
| 4 路权限竞速 | ✅ Phase 2 | 3 层简化版 |
| 子 Agent 隔离 | ✅ Phase 2 | AgentTool 模式 |
| MCP 协议 | ✅ Phase 1 | 原生支持 |
| 多模型支持 | ✅ Phase 0 | 火山引擎 + 备用 |
| /plan 命令 | ✅ Phase 1 | 切换到内环 |
| /compact 命令 | ✅ Phase 1 | 手动触发压缩 |
| 技能系统 | ✅ Phase 2 | 可插拔技能包 |
| **可验证执行** | ✅ **独有** | 内环 Validator |
| **失败学习** | ✅ **独有** | Failure Memory |
| **自我进化** | ✅ **独有** | Meta-Layer |
| **A2A 协议** | ✅ **独有** | 原生 Agent 通信 |
| **多机 Mesh** | ✅ Phase 2 | 分布式执行 |

### 5.2 代码量预算

```
Layer 1: Bootstrap (~500 LOC)
  ├─ loader.py             200 LOC  # 启动加载
  └─ guardian.py           300 LOC  # 回滚保护 + 健康监控

Layer 2: Execution Engine (~10,000 LOC)
  ├─ 外环：对话循环
  │   ├─ conversation_loop.py   300 LOC  # 核心 while True
  │   ├─ message_history.py     400 LOC  # 消息历史管理
  │   └─ input_reader.py        200 LOC  # 输入读取（stdin/IDE/MCP）
  │
  ├─ 内环：执行图
  │   ├─ planner.py             500 LOC  # LLM DAG 生成
  │   ├─ task_graph.py          600 LOC  # 增量 DAG
  │   ├─ scheduler.py           400 LOC  # asyncio 调度
  │   ├─ executor.py            500 LOC  # LLM + Tool 执行
  │   ├─ validator.py           600 LOC  # L0+L1+L2 验证
  │   ├─ artifact_store.py      300 LOC  # 产物存储
  │   └─ failure_memory.py      400 LOC  # 失败记忆
  │
  ├─ 上下文管道
  │   ├─ context_pipeline.py    800 LOC  # 5 层管道编排
  │   ├─ compressor.py          600 LOC  # Micro/Auto/Full Compact
  │   ├─ cache_manager.py       400 LOC  # 14 向量缓存追踪
  │   └─ injection_detector.py  300 LOC  # 注入检测
  │
  ├─ 工具系统
  │   ├─ tool_registry.py       300 LOC  # 工具注册
  │   ├─ core_tools.py         1200 LOC  # 20 个核心工具
  │   └─ mcp_bridge.py          400 LOC  # MCP 协议桥接
  │
  ├─ 权限系统
  │   ├─ permission_racer.py    400 LOC  # 4 路竞速
  │   └─ risk_classifier.py     300 LOC  # 风险分类
  │
  ├─ 子 Agent
  │   ├─ agent_tool.py          400 LOC  # AgentTool 实现
  │   └─ sub_agent_manager.py   300 LOC  # 子 Agent 生命周期
  │
  └─ 终端 UI
      ├─ terminal_ui.py         600 LOC  # Rich + Prompt Toolkit
      └─ session_manager.py     300 LOC  # 会话持久化

Layer 3: Meta-Layer (~4,000 LOC)
  ├─ monitor.py                 800 LOC  # 数据采集
  ├─ analyzer.py                800 LOC  # 瓶颈分析
  ├─ evolution_manager.py      1000 LOC  # 补丁生成 + 沙箱
  ├─ verifier.py                600 LOC  # 补丁验证
  ├─ deployer.py                400 LOC  # 安全部署
  └─ rollback.py                400 LOC  # 回滚机制

测试 (~3,000 LOC)
  ├─ test_conversation_loop.py  400 LOC
  ├─ test_execution_graph.py    600 LOC
  ├─ test_context_pipeline.py   400 LOC
  ├─ test_tools.py              500 LOC
  ├─ test_permissions.py        300 LOC
  ├─ test_sub_agent.py          300 LOC
  └─ test_evolution.py          500 LOC

总计: ~17,500 LOC（含测试）
等效 TypeScript: ~56,000 LOC（Python:TS ≈ 1:3.2）
Claude Code: 512,000 LOC
覆盖率: 56K / 512K ≈ 11% → 但核心差异化 100%
```

---

## 六、分阶段实施路线图

### Phase 0：MVP 核心（2 周，~3,000 LOC）

**目标**：跑通"外环对话循环"，实现 Claude Code 日常编码功能

```
Week 1:
  ├─ conversation_loop.py     ✅ 300 LOC 核心循环
  ├─ message_history.py       ✅ 400 LOC 消息管理
  ├─ tool_registry.py         ✅ 300 LOC 工具注册
  ├─ core_tools.py (read/write/search/run) ✅ 600 LOC 4 个核心工具
  └─ terminal_ui.py           ✅ 400 LOC 基础终端

Week 2:
  ├─ context_pipeline.py      ✅ 400 LOC 基础上下文（Stage 1+2）
  ├─ permission_racer.py      ✅ 300 LOC 简单权限
  ├─ mcp_bridge.py            ✅ 300 LOC MCP 协议
  └─ test_core.py             ✅ 500 LOC 核心测试

里程碑：可以日常编码使用（文件编辑、代码搜索、命令执行）
```

### Phase 1：内环 + 上下文（2 周，~5,000 LOC）

**目标**：跑通"内环执行图"，实现可验证执行

```
Week 3:
  ├─ planner.py               ✅ 500 LOC DAG 生成
  ├─ task_graph.py            ✅ 600 LOC 增量 DAG
  ├─ scheduler.py             ✅ 400 LOC 调度器
  ├─ executor.py              ✅ 500 LOC 执行器
  └─ validator.py             ✅ 600 LOC L0+L1 验证

Week 4:
  ├─ artifact_store.py        ✅ 300 LOC 产物存储
  ├─ failure_memory.py        ✅ 400 LOC 失败记忆
  ├─ compressor.py            ✅ 600 LOC 5 层压缩
  ├─ cache_manager.py         ✅ 400 LOC 缓存优化
  ├─ injection_detector.py    ✅ 300 LOC 注入检测
  └─ agent_tool.py            ✅ 400 LOC 子 Agent

里程碑：可验证执行图跑通，复杂任务成功率 > 80%
```

### Phase 2：自我进化（2 周，~4,000 LOC）

**目标**：跑通 Meta-Layer，实现 L0/L1 自动进化

```
Week 5:
  ├─ monitor.py               ✅ 800 LOC 数据采集
  ├─ analyzer.py              ✅ 800 LOC 瓶颈分析
  └─ evolution_manager.py     ✅ 1000 LOC 补丁生成

Week 6:
  ├─ verifier.py              ✅ 600 LOC 补丁验证
  ├─ deployer.py              ✅ 400 LOC 安全部署
  ├─ rollback.py              ✅ 400 LOC 回滚机制
  └─ test_evolution.py        ✅ 500 LOC 进化测试

里程碑：系统可以自动优化参数和提示词，人类只需审批 L2+
```

### Phase 3：生产化（2 周，~5,500 LOC）

**目标**：补全剩余工具、完善 UI、生产部署

```
Week 7:
  ├─ core_tools.py (complete) ✅ +600 LOC 20 个工具完整
  ├─ git_integration.py       ✅ 400 LOC Git 操作
  ├─ project_context.py       ✅ 400 LOC 项目理解
  └─ session_manager.py       ✅ 300 LOC 会话持久化

Week 8:
  ├─ terminal_ui.py (pro)     ✅ +400 LOC 完整终端 UI
  ├─ ide_bridge.py            ✅ 300 LOC VS Code 桥接
  ├─ web_interface.py         ✅ 400 LOC Web 界面
  ├─ a2a_protocol.py          ✅ 400 LOC Agent 通信
  └─ mesh_network.py          ✅ 500 LOC 多机 Mesh（基础）

里程碑：生产可用，功能对标 Claude Code 80%，差异化 100%
```

### 代码量增长曲线

```
Phase 0:  3,000 LOC  ── 可以日常编码
Phase 1:  8,000 LOC  ── 可验证执行 ✅（Claude Code 做不到）
Phase 2: 12,000 LOC  ── 自我进化 ✅（Claude Code 做不到）
Phase 3: 17,500 LOC  ── 生产可用 + 多机 Mesh
                    ── Claude Code: 512,000 LOC
                    ── 我们是 Claude Code 的 3.4%，但做到了它做不到的事
```

---

## 七、关键风险与缓解

### 7.1 技术风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| LLM 能力天花板 | 中 | 高 | 多模型支持，模型无关设计 |
| 自我进化失控 | 低 | 致命 | Bootstrap 不可修改 + 沙箱 + 回滚 |
| 上下文压缩质量 | 中 | 高 | 5 层设计，失败断路器 |
| 工具系统安全性 | 中 | 高 | 3 层权限 + 注入检测 |
| 性能（Python vs TS） | 低 | 中 | 核心用 asyncio，瓶颈用 C 扩展 |

### 7.2 产品风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 用户不信任自我进化 | 高 | 高 | 默认关闭，显式启用，完整审计 |
| Claude Code 先发优势 | 高 | 中 | 差异化功能（验证+进化） |
| 社区生态不足 | 中 | 中 | MCP 兼容，复用现有生态 |
| 商业化困难 | 中 | 高 | 开源核心 + 企业版（Mesh+安全） |

### 7.3 与 Claude Code 的竞争策略

```
短期（Phase 0-1）：功能对标，差异化验证
  └─ 用户："Agent OS 能做的 Claude Code 也能做"
  └─ 但我们有验证 + 失败学习

中期（Phase 2）：差异化凸显
  └─ 用户："Agent OS 能自动优化自己"
  └─ Claude Code 做不到

长期（Phase 3）：生态锁定
  └─ 用户："我的 Agent OS 已经跑了 10000 个任务，
       它知道我的代码风格、常见错误、最佳实践"
  └─ Claude Code 每次都是从头开始
```

---

## 八、技术栈决策

| 组件 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.12+ | AI/ML 生态、现有代码复用、快速迭代 |
| 异步 | asyncio | 原生协程支持，足够性能 |
| 终端 UI | Rich + Prompt Toolkit | 功能丰富，纯 Python |
| 序列化 | Pydantic v2 | 类型安全、JSON Schema 生成 |
| 存储 | SQLite + aiosqlite | 零依赖，足够性能 |
| 搜索 | ripgrep (rg) | 最快的代码搜索工具 |
| MCP | 自实现 | 协议简单，避免依赖 |
| 沙箱 | subprocess + cgroups | 轻量隔离 |
| 测试 | pytest | 标准选择 |
| 打包 | pip install | 简单分发 |

---

## 九、总结：Agent OS 的终极愿景

```
2026 年的 AI Coding Agent 市场：

  Claude Code（Anthropic）—— 终端 Agent 之王
    └─ 512K LOC，$2.5B ARR，先发优势
    └─ 弱点：不能验证、不能学习、不能进化

  Cursor（Anysphere）—— IDE Agent 之王
    └─ $100M+ ARR，AI-Native 体验
    └─ 弱点：绑定 IDE、不能进化

  Agent OS（我们）—— 自我进化的 Agent 运行时
    └─ 17.5K LOC，轻量但强大
    └─ 优势：可验证执行 + 失败学习 + 自我进化
    └─ Claude Code 做不到的，我们能做到
    └─ Claude Code 不敢做的，我们敢做

我们的口号：
  "Not just a coding agent. An agent that gets better at coding."
  "不是一个编码助手，而是一个越用越聪明的编码助手。"
```

---

*版本：v6.0 · 2026-06-26*
*作者：小鸣*
*基于：AI Coding Agent 技术发展史（2013-2026）· Claude Code 512K 行源码逆向 · 行业框架对比*
