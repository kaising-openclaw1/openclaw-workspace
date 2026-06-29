# Agent OS v7.0 — 下一代 AI 编码 Agent 架构

> 基于 2026-06-26 全面研究：ChatGPT/OpenAI Codex 设计哲学 · Google 生产级 Agent 原则 · Claude Code 512K 行泄露源码逆向 · 2026 行业五大转变
> 核心理念：**不做 Claude Code 的平替，做 Claude Code 的下一代**

---

## 零、2026 年 AI 编码 Agent 行业的五个根本转变

在开始架构设计之前，必须理解行业正在发生的结构性变化。这些变化不是趋势，是已经发生的范式转移。

### 转变 1：从"补全"到"委托"

```
2023: "AI 帮我补全这行代码"
2024: "AI 帮我写这个函数"
2025: "AI 帮我重构这个模块"
2026: "AI 帮我处理这个 Issue，做完提 PR"
```

**架构含义**：Agent 不再只是"对话式工具"，而是"异步协作者"。这意味着：
- 任务必须有明确的边界（scope）
- 执行必须可审计（audit trail）
- 结果必须可验证（verification）
- 失败必须可回滚（rollback）

### 转变 2：从"提示词技巧"到"系统工程"

```
2024: "写更好的 prompt"
2025: "用更好的模型"
2026: "设计更好的系统"
```

**架构含义**：上下文管理、权限控制、MCP 工具、沙箱隔离、审计日志、成本控制——这些系统工程问题比模型质量更重要。Claude Code 512K 行代码中模型调用 < 0.1%，剩下的全是系统工程。

### 转变 3：MCP 正在成为 Agent 基础设施

```
2025: MCP = "Claude 的插件系统"
2026: MCP = "Agent 的 USB-C"
```

**架构含义**：MCP 不是可选的"生态功能"，而是核心架构决策。工具定义、权限、审计、注入防护——这些必须在架构层面原生支持，而不是事后插件。

### 转变 4：安全边界 = 产品功能

```
2025: "Agent 能做什么？"
2026: "Agent 不能做什么？"
```

**架构含义**：权限、沙箱、审计、策略分发——这些是核心产品需求，不是"安全补丁"。OWASP 已经发布了 MCP Top 10 安全风险。不能访问 `~/.ssh`、不能外联未授权域名、不能读取未授权的文件——这些需要架构级支持。

### 转变 5：上下文工程取代"无限上下文"

```
2024: "100K 上下文窗口！"
2025: "200K 上下文窗口！"
2026: "上下文质量比上下文大小重要 10 倍"
```

**架构含义**：AGENTS.md、CLAUDE.md、rules、memories、skills、subagents、hooks——这些都是"上下文工程"的不同形式。核心问题不是"能塞多少 token"，而是"如何让 Agent 在正确的上下文中做正确的事"。

---

## 一、从 Claude Code 泄露中学到的 7 个架构教训

### 教训 1：核心循环只有 200 行，但这是最重要的 200 行

Claude Code 的核心 agent loop 极其简单：

```typescript
while (true) {
  const response = await callAPI(messages);
  messages.push(response);
  if (response.stop_reason === "end_turn") break;
  const results = await executeTools(response);
  messages.push({ role: "user", content: results });
}
```

**我们的结论**：核心循环必须极简。所有复杂度推到外围（工具系统、权限、上下文管理）。

### 教训 2：46,000 行的 QueryEngine.ts 是真正的核心

这不是"模型调用"——这是编排层。处理：LLM API 调用、流式响应、缓存管理、工具执行循环、错误恢复、输出截断。

**我们的结论**：编排层是护城河，不是模型调用。我们需要一个类似但更轻量的 Engine 核心。

### 教训 3：29,000 行的工具定义层

Schema 验证、权限执行、错误处理——每个工具都有完整的定义、输入输出 schema、权限级别。

**我们的结论**：工具系统必须是声明式的、类型安全的、可审计的。

### 教训 4：缓存感知的系统提示

Claude Code 的系统提示是模块化组装的，缓存边界放在段之间。稳定内容（基础指令）跨请求缓存，动态内容（当前文件上下文）每轮刷新。目标：prompt cache hit rate > 70%。

**我们的结论**：上下文管理必须缓存感知，这是成本优化的核心。

### 教训 5：44 个隐藏功能标志

KAIROS（自主守护进程模式）、ULTRAPLAN（云端深度规划）、多 Agent 协调、语音控制——这些功能已经实现，只是被编译时标志隐藏。

**我们的结论**：功能标志系统是架构必需品。我们的"自我进化"概念与 KAIROS 方向一致——但 KAIROS 已经写好了，我们还在规划。

### 教训 6：权限执行是竞速游戏

4 路并行审批（用户策略 → 风险分类器 → 上下文规则 → 用户实时），最快返回的路线决定结果。

**我们的结论**：权限系统必须低延迟，不能成为用户体验瓶颈。

### 教训 7：React + Ink 终端渲染

用游戏引擎技术做终端 UI。这不是"花哨"——这是响应式实时交互的必要条件。

**我们的结论**：终端 UI 是产品体验的核心，不是"命令行输出"。

---

## 二、ChatGPT/OpenAI Codex 的设计哲学

### Codex 的三个核心设计原则

**1. 异步优先（Async-first）**
Codex 的核心价值不是"实时配对"，而是"异步委托"。你提交任务，它在你离线时工作，完成后提 PR。这比实时交互更适合复杂任务。

**对我们的启示**：Agent OS 应该同时支持同步（CLI 交互）和异步（后台任务）两种模式。同步用于日常编码，异步用于复杂重构。

**2. 沙箱隔离（Sandbox-first）**
Codex 在完全隔离的沙箱中运行，网络隔离、文件系统隔离。这不仅是安全措施，也是产品特性——用户敢让 Codex 做更多事，因为知道它跑在沙箱里。

**对我们的启示**：沙箱不是"安全功能"，是"信任基础设施"。没有沙箱，Agent 的能力上限会被用户的不信任限制。

**3. PR 工作流集成（PR-native）**
Codex 的输出不是"代码建议"，而是"Pull Request"。这改变了工作流：不再是"AI 写了什么→我手动合并"，而是"AI 提了 PR→我 review→合并"。

**对我们的启示**：Agent 的输出应该是可 review 的、可回滚的、可审计的。Git 集成不是"功能"，是"架构要求"。

### Google 的生产级 Agent 原则

Google Cloud 的 Agent 指南提出了一个关键框架：

```
Think → Act → Observe
   ↓        ↓        ↓
Reason   Execute   Evaluate
```

加上四层基础设施：
- **短期记忆**（Session State）—— 当前对话上下文
- **长期记忆**（Memory Service）—— 跨会话知识
- **信息检索**（RAG）—— 外部知识库
- **工具执行**（Tool Use）—— 外部系统交互
- **安全框架**（Security）—— 边界和策略

**对我们的启示**：记忆系统不是"一个功能"，而是多层架构。短期（会话内）、中期（项目内）、长期（跨项目）——每层有不同的存储和检索策略。

---

## 三、Agent OS v7.0 架构

### 3.1 一句话定位

> **Agent OS 是一个"Agent 工程平台"——不是另一个 Claude Code，而是 Claude Code 的下一代。它让开发者可以构建、部署、治理和进化自己的编码 Agent。**

### 3.2 核心架构：四层 + 双模 + 一核心

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
│  │  LAYER 0: BOOTSTRAP（信任根, ~500 LOC）                      │   │
│  │  永远手写，永远不改。启动加载 + 健康监控 + 回滚保护          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                               │                                     │
│                               ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  LAYER 1: ENGINE（引擎核心, ~3K LOC）                        │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  Engine Core (~500 LOC)                              │   │   │
│  │  │  └─ Agent Loop (while True, ~200 LOC)                │   │   │
│  │  │  └─ Message Pipeline (采集→压缩→注入→预算)           │   │   │
│  │  │  └─ Tool Execution Loop (调用→权限→执行→反馈)        │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │   │
│  │  │ 上下文    │ │ 工具系统  │ │ 权限模型  │ │ 记忆系统     │   │   │
│  │  │ 管道(4层) │ │ (声明式)  │ │ (3层竞速) │ │ (短/中/长)  │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                               │                                     │
│                               ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  LAYER 2: SERVICES（服务层, ~5K LOC）                        │   │
│  │                                                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │   │
│  │  │ 同步模式  │ │ 异步模式  │ │ MCP 网关 │ │ Git 集成     │   │   │
│  │  │ (CLI交互) │ │ (后台任务)│ │ (协议桥) │ │ (PR工作流)   │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │   │
│  │                                                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │   │
│  │  │ 沙箱管理  │ │ 会话管理  │ │ 成本控制  │ │ 审计日志     │   │   │
│  │  │ (隔离)   │ │ (持久化)  │ │ (预算)   │ │ (不可篡改)   │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                               │                                     │
│                               ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  LAYER 3: GOVERNANCE（治理层, ~3K LOC）                      │   │
│  │                                                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │   │
│  │  │ 策略引擎  │ │ 监控分析  │ │ 进化管理  │ │ 功能标志     │   │   │
│  │  │ (规则)   │ │ (可观测)  │ │ (自我进化)│ │ (Feature Flag)│   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 双模运行：同步 + 异步

这是 v7.0 最核心的架构决策——从 v6.0 的"双环"进化为"双模"：

```
同步模式（Sync Mode）—— 日常编码
  └─ 类似 Claude Code 的实时交互
  └─ 用户等待结果
  └─ 适用于：文件编辑、代码搜索、简单重构
  └─ 延迟要求：< 5s

异步模式（Async Mode）—— 复杂任务
  └─ 类似 Codex 的任务委托
  └─ 用户提交后离开，完成后通知
  └─ 适用于：大规模重构、测试修复、Issue 处理
  └─ 延迟要求：< 30min
  └─ 输出：Pull Request + 变更摘要

模式切换：
  └─ 用户显式切换（/async, /sync）
  └─ 任务复杂度自动切换（>5 步 → 异步）
  └─ 用户离开终端时自动切换
```

**为什么从"双环"进化到"双模"？**

v6.0 的"双环"（外环扁平消息 + 内环 DAG）本质上是同一个交互模式下的两种执行策略。v7.0 的"双模"是两个完全不同的交互模式：

- 同步模式 = Claude Code 模式（实时、交互、低延迟）
- 异步模式 = Codex 模式（委托、后台、高自治）

这比"双环"更根本——它改变了用户与 Agent 的关系。

### 3.4 四层上下文管道

基于 Claude Code 泄露分析 + Google 记忆分层理论：

```
Layer 1: 会话上下文（Session Context）
  └─ 当前对话历史
  └─ 存储：内存（MessageHistory）
  └─ 压缩策略：保留最近 N 条 + 系统提示
  └─ 预算：60% 总 token

Layer 2: 项目上下文（Project Context）
  └─ AGENTS.md / CLAUDE.md 等效
  └─ 项目结构、编码规范、架构决策
  └─ 存储：文件系统（.agent-os/ 目录）
  └─ 预算：20% 总 token

Layer 3: 长期记忆（Long-term Memory）
  └─ 跨会话的知识积累
  └─ 用户偏好、常见错误、项目历史
  └─ 存储：向量数据库（SQLite + embeddings）
  └─ 检索：语义搜索（仅相关片段）
  └─ 预算：10% 总 token

Layer 4: 工具上下文（Tool Context）
  └─ MCP 工具定义、工具返回结果
  └─ 按需加载（不是所有工具都注入）
  └─ 预算：10% 总 token
```

### 3.5 声明式工具系统（MCP 原生）

每个工具的定义（受 Claude Code 泄露启发）：

```python
@dataclass
class Tool:
    name: str
    description: str
    version: str = "1.0.0"
    
    # Schema
    input: JSONSchema
    output: JSONSchema
    
    # 权限
    permission: "auto" | "confirm" | "policy" | "deny"
    risk_level: "read" | "write" | "exec" | "agent"
    
    # 执行
    timeout: int = 30
    retry: int = 0
    idempotent: bool = False
    
    # MCP
    mcp_compatible: bool = True
    mcp_server: str = ""  # 如果来自 MCP 服务器
    
    # 审计
    audit: bool = True
    log_input: bool = True
    log_output: bool = False  # 敏感输出不记录
    
    # 成本
    cost_weight: float = 1.0  # 用于成本预算
    
    # 处理器
    handler: Callable | None = None
```

### 3.6 权限模型（3 层竞速）

受 Claude Code 4 路竞速启发，但简化为 3 层：

```
Route 1: 策略引擎（Policy Engine）
  └─ 全局策略（YAML 配置）
  └─ 项目策略（.agent-os/policy.yaml）
  └─ 会话策略（用户当前设置）
  └─ 匹配：工具名 + 资源路径 + 操作类型

Route 2: 风险分类器（Risk Classifier）
  └─ 基于工具类型 + 参数的风险评分
  └─ 规则引擎（不是 ML，保证确定性）
  └─ 输出：allow | deny | confirm

Route 3: 用户确认（User Confirm）
  └─ 终端提示（同步模式）
  └─ 推送通知（异步模式）
  └─ 超时默认：deny（安全优先）

竞速规则：
  └─ 任何 Route 返回 deny → DENY
  └─ 所有 Route 返回 allow → ALLOW
  └─ 混合 → CONFIRM
```

### 3.7 自我进化机制（与 KAIROS 对齐）

Claude Code 泄露揭示了 KAIROS——一个自主守护进程模式。我们的"自我进化"概念与 KAIROS 方向一致，但更激进：

```
KAIROS（Claude Code 隐藏功能）:
  └─ 持久化后台 Agent
  └─ 主动监控项目变化
  └─ 在适当时机自主行动

Agent OS 自我进化:
  └─ 包含 KAIROS 的所有能力
  └─ 加上：系统自我优化
  └─ 加上：从失败中学习
  └─ 加上：架构自动演进

进化安全分级:
  L0: 参数调优 → 自动
  L1: 提示词优化 → 自动 + 沙箱
  L2: 工具注册表 → 人类审批
  L3: 核心逻辑 → 人类审批 + 冷却期
  ❌: Bootstrap → 永远不允许
```

### 3.8 异步任务系统（对标 Codex）

```
任务提交:
  └─ CLI: /async "重构 user 模块，拆分为 user/auth/profile"
  └─ API: POST /api/v1/tasks { type: "refactor", ... }
  └─ Git: 提交 Issue → Agent 自动认领

任务执行:
  └─ 沙箱隔离（每个任务独立目录）
  └─ 网络隔离（仅允许白名单域名）
  └─ 时间限制（默认 30min，可配置）
  └─ 成本预算（默认 $0.50/任务，可配置）

任务输出:
  └─ Pull Request（Git 集成）
  └─ 变更摘要（修改了哪些文件、为什么）
  └─ 测试结果（运行了哪些测试、通过率）
  └─ 审计追踪（每一步的操作记录）

任务通知:
  └─ 终端通知（同步模式用户）
  └─ 推送通知（移动端）
  └─ Slack/Webhook（团队协作）
```

---

## 四、与竞品的根本差异

### 4.1 定位矩阵

```
                   生产级
                    │
                    │
    Claude Code ◄───┼───► Cursor
    (实时交互)      │    (IDE 集成)
                    │
                    │
    Codex ◄─────────┼───────► Agent OS ←── 我们在这里
    (异步委托)      │           │
                    │           │
                    │           ▼
                平台级       治理+进化
```

### 4.2 功能对标

| 维度 | Claude Code | Codex | Cursor | Agent OS v7.0 |
|------|------------|-------|--------|---------------|
| 交互模式 | 同步 | 异步 | 同步 | **双模（同步+异步）** |
| 执行环境 | 本地终端 | 云端沙箱 | IDE 内嵌 | **本地+云端可选** |
| 工具系统 | 40+ 工具 | 有限 | 插件 | **声明式+MCP 原生** |
| 权限模型 | 4 路竞速 | 沙箱隔离 | 简单确认 | **3 层策略引擎** |
| 记忆系统 | 会话+CLAUDE.md | 会话 | 无 | **4 层（会/项/长/工）** |
| 异步任务 | ❌（KAIROS 隐藏） | ✅ 核心功能 | ❌ | **✅ 原生支持** |
| 自我进化 | ❌（不可能） | ❌ | ❌ | **✅ L0-L3 分级** |
| 功能标志 | ✅ 44 个隐藏 | ❌ | ❌ | **✅ 原生支持** |
| 审计日志 | ❌ | ✅ 沙箱日志 | ❌ | **✅ 不可篡改审计** |
| 成本控制 | ❌ | ✅ Pro 订阅 | ❌ | **✅ 每任务预算** |
| MCP 协议 | ✅ 原生 | ✅ 有限 | ✅ 插件 | **✅ 原生+网关** |
| 开源 | ❌ | ❌ | ❌ | **✅ 开源核心** |

### 4.3 我们的核心差异化

```
Claude Code 做不到的:
  └─ 异步任务委托（KAIROS 隐藏但未发布）
  └─ 自我进化（512K LOC 不敢改）
  └─ 每任务成本控制（商业模型限制）
  └─ 审计日志（没有设计）

Codex 做不到的:
  └─ 实时交互（云端延迟）
  └─ 本地文件系统访问（沙箱限制）
  └─ 自我进化（商业产品不允许）
  └─ 开源（闭源）

Cursor 做不到的:
  └─ 终端原生体验（绑定 IDE）
  └─ 异步任务（没有设计）
  └─ 自我进化（商业产品不允许）

Agent OS 三者都能做:
  └─ 同步交互（像 Claude Code）
  └─ 异步委托（像 Codex）
  └─ 开源核心（像 Cursor 没有的）
  └─ 自我进化（三者都没有）
```

---

## 五、代码量预算（修正版）

基于 v6.0 评估的教训 + Claude Code 泄露的实际数据：

```
Layer 0: Bootstrap (~500 LOC)
  loader.py                    200 LOC
  guardian.py                  300 LOC

Layer 1: Engine (~3,000 LOC)
  engine_core.py               500 LOC  # Agent Loop + Message Pipeline
  message_history.py           300 LOC  # 消息历史 + 压缩
  context_pipeline.py          800 LOC  # 4 层上下文
  tool_registry.py             300 LOC  # 声明式工具注册
  permission_racer.py          400 LOC  # 3 层竞速
  memory_manager.py            400 LOC  # 短/中/长记忆
  injection_detector.py        300 LOC  # 注入检测

Layer 2: Services (~5,000 LOC)
  sync_mode.py                 400 LOC  # CLI 交互
  async_mode.py                600 LOC  # 后台任务
  mcp_gateway.py               500 LOC  # MCP 协议桥
  git_integration.py           400 LOC  # Git + PR
  sandbox_manager.py           500 LOC  # 沙箱隔离
  session_manager.py           300 LOC  # 会话持久化
  cost_controller.py           300 LOC  # 成本预算
  audit_logger.py              400 LOC  # 审计日志
  terminal_ui.py               800 LOC  # Rich 终端
  core_tools.py               1200 LOC  # 20 个核心工具

Layer 3: Governance (~3,000 LOC)
  policy_engine.py             500 LOC  # 策略引擎
  monitor.py                   500 LOC  # 监控采集
  analyzer.py                  500 LOC  # 分析
  evolution_manager.py         800 LOC  # 进化管理
  feature_flags.py             300 LOC  # 功能标志
  rollback.py                  400 LOC  # 回滚机制

测试 (~3,500 LOC)
  test_engine.py               500 LOC
  test_context.py              400 LOC
  test_tools.py                500 LOC
  test_permissions.py          400 LOC
  test_memory.py               300 LOC
  test_async.py                400 LOC
  test_mcp.py                  300 LOC
  test_governance.py           400 LOC
  test_evolution.py            300 LOC

总计: ~15,000 LOC（含测试）
等效 TypeScript: ~48,000 LOC（Python:TS ≈ 1:3.2）
Claude Code: 512,000 LOC
覆盖率: 48K / 512K ≈ 9.4%
```

**关键变化 vs v6.0：**
- 从 22,500 LOC 降到 15,000 LOC（去掉了不必要的 DAG 复杂度）
- 增加了异步模式、记忆系统、策略引擎、功能标志
- 去掉了 Mesh 网络（Phase 2 再说）
- 测试占比从 17% 提升到 23%

---

## 六、实施路线图

### Phase 0：Engine 核心（2 周）

```
Week 1: Engine Core
  ├─ engine_core.py (500 LOC) — Agent Loop
  ├─ message_history.py (300 LOC)
  ├─ tool_registry.py (300 LOC)
  └─ core_tools.py (500 LOC) — 5 个基础工具

Week 2: 同步模式
  ├─ sync_mode.py (400 LOC) — CLI 交互
  ├─ permission_racer.py (400 LOC)
  ├─ context_pipeline.py (400 LOC) — 基础 2 层
  └─ terminal_ui.py (400 LOC) — 基础终端

里程碑: 可以日常编码使用（同步模式）
```

### Phase 1：服务层（2 周）

```
Week 3: 异步模式
  ├─ async_mode.py (600 LOC)
  ├─ sandbox_manager.py (500 LOC)
  ├─ git_integration.py (400 LOC)
  └─ session_manager.py (300 LOC)

Week 4: MCP + 记忆
  ├─ mcp_gateway.py (500 LOC)
  ├─ memory_manager.py (400 LOC)
  ├─ cost_controller.py (300 LOC)
  └─ audit_logger.py (400 LOC)

里程碑: 异步任务跑通，MCP 工具可用
```

### Phase 2：治理层（2 周）

```
Week 5: 策略 + 监控
  ├─ policy_engine.py (500 LOC)
  ├─ monitor.py (500 LOC)
  ├─ feature_flags.py (300 LOC)
  └─ rollback.py (400 LOC)

Week 6: 自我进化
  ├─ analyzer.py (500 LOC)
  ├─ evolution_manager.py (800 LOC)
  ├─ injection_detector.py (300 LOC)
  └─ core_tools.py (剩余 700 LOC)

里程碑: 自我进化 L0/L1 可用，功能标志系统就绪
```

### Phase 3：生产化（2 周）

```
Week 7: 完整工具 + 测试
  ├─ core_tools.py (全部 20 个)
  ├─ context_pipeline.py (完整 4 层)
  ├─ terminal_ui.py (完整版)
  └─ 测试覆盖

Week 8: 集成 + 文档
  ├─ 集成测试
  ├─ 用户文档
  ├─ API 文档
  └─ 打包发布

里程碑: 生产可用 v1.0.0
```

---

## 七、关键风险

### 7.1 技术风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 异步模式复杂度 | 高 | 高 | 先跑通同步，异步 Phase 1 |
| 沙箱隔离不彻底 | 中 | 致命 | 使用容器化（Docker） |
| 自我进化失控 | 低 | 致命 | Bootstrap 不可修改 + 沙箱 + 回滚 |
| MCP 协议变化 | 中 | 中 | 抽象网关层，隔离变化 |
| Python 终端生态 | 中 | 中 | Rich + Prompt Toolkit 已验证 |

### 7.2 竞争风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Claude Code 发布 KAIROS | 高 | 高 | 差异化在自我进化，不是异步 |
| Codex 开源 | 低 | 中 | 开源不是护城河，治理是 |
| Cursor 做 CLI | 中 | 中 | 终端体验需要深度积累 |
| 社区复制 | 中 | 低 | 开源核心 + 企业版 |

### 7.3 产品风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 用户不理解双模 | 高 | 中 | 默认同步，自动切换 |
| 异步任务信任问题 | 高 | 高 | 沙箱 + 审计 + 可回滚 |
| 自我进化恐惧 | 高 | 高 | 默认关闭，显式启用 |
| 成本不可控 | 中 | 高 | 每任务预算 + 上限 |

---

## 八、总结

### 8.1 从 v6.0 到 v7.0 的关键进化

```
v6.0 的问题:
  └─ 过度关注"双环"（技术细节）
  └─ 低估了异步模式的重要性
  └─ 缺少治理层（策略、审计、成本）
  └─ 自我进化设计过于激进

v7.0 的改进:
  └─ 从"双环"进化为"双模"（交互模式）
  └─ 异步模式成为一等公民
  └─ 新增治理层（策略引擎 + 审计 + 成本控制）
  └─ 自我进化分级（L0-L3 + Bootstrap 不可修改）
  └─ 代码量从 22,500 LOC 降到 15,000 LOC
```

### 8.2 一句话总结

> **Claude Code 是"更好的终端工具"，Codex 是"更好的云端助手"，Cursor 是"更好的 IDE"。Agent OS 是"更好的工程平台"——它让你构建、部署、治理和进化你自己的编码 Agent。**

### 8.3 我们的口号

```
"Not a tool. A platform for your tools."
"不是一个工具，是你构建工具的 platform。"
```

---

*版本：v7.0 · 2026-06-26*
*作者：小鸣*
*基于：ChatGPT/OpenAI Codex 设计哲学 · Google 生产级 Agent 原则 · Claude Code 512K 行泄露源码逆向 · 2026 行业五大转变*
