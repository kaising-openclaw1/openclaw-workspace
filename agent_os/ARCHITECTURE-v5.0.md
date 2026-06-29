# Agent OS v5.0 — 自我进化的 Code Agent 架构

> 基于 2026-06-25 三方交叉评审（ChatGPT + Gemini + Google AI）
> 目标：超越 Claude Code 的终端 AI 编程助手，核心差异 = 自我进化能力

---

## 一、战略定位

### 不是"另一个 Claude Code"
Claude Code 是端工作流（端到端端侧开发 Agent）。
Agent OS 是企业级生产流编排（Agent Orchestration）。

**我们的定位**：终端 AI 编程助手 + 自我进化能力。
- 替代 Claude Code 的日常功能（文件读写、代码搜索、命令执行）
- 超越 Claude Code 的核心差异（可验证执行图 + 自我进化）

### 为什么 Claude Code 做不到自我进化
1. 512K LOC 的庞大代码库，修改风险极高
2. 没有内置的 DAG 执行引擎，无法保证修改后的行为正确
3. 没有 Failure Memory，每次失败都是孤立事件
4. 商业产品不允许"自我修改"——安全合规问题

### 我们的优势
1. 从零开始设计，架构干净（6K LOC vs 512K LOC）
2. 内置 Execution Engine（DAG + Validator + Failure Memory）
3. 可以设计"自我进化"作为核心能力，而不是事后补丁
4. 轻量级，可以快速迭代

---

## 二、核心架构

```
┌─────────────────────────────────────────────────────┐
│                   Code Agent                         │
│  ┌─────────────────────────────────────────────┐    │
│  │  Layer 1: Bootstrap (信任根, ~500 LOC)       │    │
│  │  └─ 启动加载 + 健康监控 + 回滚保护           │    │
│  │  └─ 永远手写，不能被自己修改                  │    │
│  ├─────────────────────────────────────────────┤    │
│  │  Layer 2: Execution Engine (~8K LOC)         │    │
│  │  ├─ Core Loop (主对话循环)                   │    │
│  │  ├─ Task Graph (增量 DAG)                    │    │
│  │  ├─ Scheduler (任务调度)                     │    │
│  │  ├─ Executor (LLM + Tool 执行)              │    │
│  │  ├─ Validator (L0 Schema + L0.5 结构)       │    │
│  │  ├─ Artifact Store (产物存储)                │    │
│  │  └─ Failure Memory (失败经验)                │    │
│  ├─────────────────────────────────────────────┤    │
│  │  Layer 3: Meta-Layer (自我进化, ~3K LOC)     │    │
│  │  ├─ Monitor (性能数据采集)                   │    │
│  │  ├─ Analyzer (瓶颈识别 + 改进建议)           │    │
│  │  ├─ Evolution Manager (补丁生成 + 沙箱)     │    │
│  │  └─ Verifier (补丁验证)                     │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

---

## 三、自我进化机制

### 3.1 进化范围（安全分级）

| 级别 | 可修改内容 | 审批要求 | 风险 |
|------|-----------|---------|------|
| L0 | 参数调优（temperature, max_tokens, retry_count） | 自动 | 极低 |
| L1 | 提示词优化（system prompt, tool descriptions） | 自动 + 沙箱 | 低 |
| L2 | 工具注册表（新增/修改工具） | 人类审批 | 中 |
| L3 | 核心循环（Execution Loop 逻辑） | 人类审批 + 冷却期 | 高 |
| ❌ | Bootstrap（信任根代码） | 永远不允许 | 致命 |

### 3.2 进化流程

```
1. Monitor 采集数据
   ├─ 任务成功率
   ├─ 工具调用失败率
   ├─ 用户反馈（隐式：是否接受结果）
   └─ 性能指标（延迟、Token 消耗）

2. Analyzer 分析瓶颈
   ├─ 识别失败模式
   ├─ 定位低效环节
   └─ 生成改进建议

3. Evolution Manager 生成补丁
   ├─ 基于 Failure Memory 生成修复
   ├─ 在沙箱中运行验证
   └─ 通过 Verifier 检查

4. 部署
   ├─ L0/L1: 自动部署（沙箱通过后）
   ├─ L2: 人类审批后部署
   └─ L3: 人类审批 + 冷却期（1000 Task / 24h）
```

### 3.3 安全约束

1. **沙箱测试**：每次修改必须在隔离环境运行完整测试套件
2. **回滚机制**：每次修改前备份，失败自动回滚
3. **冷却期**：L3 修改后至少运行 1000 Task 或 24h 才能再次修改
4. **不可修改区域**：Bootstrap 代码、Verifier 代码、测试代码
5. **人类审批**：L2+ 修改必须人类确认

---

## 四、MVP 范围（Phase 0）

### 目标：先做到 Claude Code 能做的事

**核心功能**：
- [x] 文件读写（read_file, write_file, edit_file）
- [x] 代码搜索（search_code, grep, analyze_project）
- [x] 命令执行（run_command）
- [ ] 终端交互界面
- [ ] 会话管理（保存/恢复）
- [ ] Git 集成
- [ ] 项目上下文理解

**自我进化（Phase 0 不做）**：
- [ ] L0 参数调优（Phase 1）
- [ ] L1 提示词优化（Phase 2）
- [ ] L2/L3 代码修改（Phase 3）

### 技术栈
- Python（复用现有 agent_os 代码）
- 火山引擎 DeepSeek（已有 API）
- SQLite（会话存储）

---

## 五、与 Claude Code 的对比

| 维度 | Claude Code | Agent OS (目标) |
|------|------------|----------------|
| 代码量 | 512K LOC | 15-20K LOC |
| 核心语言 | TypeScript | Python |
| 执行模型 | 扁平消息 | DAG 执行图 |
| 验证机制 | 无 | L0 + L0.5 + L1 |
| 失败学习 | 无 | Failure Memory |
| 自我进化 | 无 | Meta-Layer (Phase 1+) |
| 沙箱隔离 | 无 | 沙箱测试 |
| 可审计性 | 无 | 完整执行追踪 |

---

## 六、关键风险

1. **LLM 能力天花板**：如果 DeepSeek V4 的代码理解能力不够，所有上层都白搭
2. **自我进化失控**：系统修改自己后行为异常，难以调试
3. **用户信任**：用户不敢让 AI 修改自己的代码，更不敢让它修改自己
4. **工程复杂度**：Execution Engine + Meta-Layer 的双层架构，调试难度翻倍
5. **与 Claude Code 的差距**：人家 512K LOC 的成熟度，我们短期追不上

---

## 七、下一步

1. 继续与 ChatGPT + Google AI 迭代论证架构，直到双方都认为成功率 ≥90%
2. 确定 MVP 核心业务场景
3. 写 300 LOC Kernel Prototype 验证 Execution Loop
4. 逐步构建完整系统
