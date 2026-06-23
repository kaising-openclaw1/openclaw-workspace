# Agent OS IR 规范 v1.0 — Intermediate Representation

> 定义：Task Graph 的标准表达形式
> 核心原则：Planner 输出 IR，Scheduler 只解析 IR，所有组件通过 IR 通信
> 版本：1.0.0 | 2026-06-22

---

## 目录

1. [设计原则](#一设计原则)
2. [核心类型系统](#二核心类型系统)
3. [Task Graph IR](#三task-graph-ir)
4. [Task IR](#四task-ir)
5. [Contract IR](#五contract-ir)
6. [Artifact IR](#六artifact-ir)
7. [Execution State IR](#七execution-state-ir)
8. [Failure Memory IR](#八failure-memory-ir)
9. [完整示例](#九完整示例)
10. [序列化格式](#十序列化格式)
11. [版本兼容性](#十一版本兼容性)

---

## 一、设计原则

### 1.1 三大目标

```
┌─────────────────────────────────────────────────────┐
│                    IR 规范                            │
│                                                      │
│  ① 可验证 ──── 每个 IR 片段都可以独立校验            │
│  ② 可序列化 ── JSON/Protobuf 无损互转               │
│  ③ 可扩展 ──── 版本化字段，向后兼容                  │
└─────────────────────────────────────────────────────┘
```

### 1.2 关键约束

- **无循环引用**：Task Graph 必须是 DAG，IR 中禁止自引用
- **无隐式依赖**：所有依赖必须在 `dependencies` 字段显式声明
- **无运行时类型**：所有类型在 IR 中静态声明（`input_schema` / `output_schema`）
- **无外部引用**：IR 是自包含的，不依赖外部上下文

### 1.3 命名规范

| 元素 | 命名规则 | 示例 |
|------|---------|------|
| task_id | snake_case | `analyze_logs`, `generate_report` |
| artifact_id | uuid v4 | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| schema_name | PascalCase | `AnalysisResult`, `ReportConfig` |
| field_name | snake_case | `error_count`, `summary_text` |
| version | semver | `1.0.0`, `2.1.0` |

---

## 二、核心类型系统

### 2.1 基础类型

```typescript
// IR 中使用的所有基础类型
type IRPrimitive = string | number | boolean | null;
type IRValue = IRPrimitive | IRValue[] | { [key: string]: IRValue };

// Schema 定义（JSON Schema 子集）
type IRSchema = {
  type: "object" | "array" | "string" | "number" | "boolean" | "null";
  properties?: { [key: string]: IRSchema };     // object 时
  items?: IRSchema;                               // array 时
  required?: string[];                            // 必填字段
  enum?: IRValue[];                               // 枚举值
  description?: string;                           // 人类可读描述
  default?: IRValue;                              // 默认值
  example?: IRValue;                              // 示例值
  // 约束
  minLength?: number;
  maxLength?: number;
  minimum?: number;
  maximum?: number;
  pattern?: string;                                // regex
};
```

### 2.2 状态枚举

```typescript
// Task 生命周期状态
type TaskStatus =
  | "pending"       // 已创建，依赖未满足
  | "ready"         // 依赖已满足，等待调度
  | "running"       // 正在执行
  | "validating"    // 执行完成，等待验证
  | "completed"     // 验证通过
  | "failed"        // 执行失败（不可恢复）
  | "skipped"       // 依赖失败，跳过执行
  | "retrying"      // 验证失败，重试中
  | "cancelled";    // 被用户/系统取消

// 验证结果
type Verdict =
  | "accepted"      // 验证通过
  | "rejected"      // 验证不通过
  | "needs_review"; // 需要人工介入

// 失败类型
type FailureKind =
  | "execution_error"     // 执行异常（超时/OOM/网络）
  | "schema_mismatch"     // 输出不符合 schema
  | "contradiction"       // 输出与已知事实矛盾
  | "hallucination"       // LLM 幻觉检测
  | "dependency_failed";  // 依赖任务失败
```

---

## 三、Task Graph IR

### 3.1 顶层结构

```typescript
// 完整的 Task Graph IR
type TaskGraphIR = {
  // 元数据
  graph_id: string;                           // UUID v4
  version: string;                            // IR 规范版本 ("1.0.0")
  created_at: string;                         // ISO 8601
  updated_at: string;                         // ISO 8601

  // 执行上下文
  session_id: string;                         // 会话 ID
  user_intent: string;                        // 原始用户意图（摘要）
  max_concurrency: number;                    // 最大并发数
  timeout_seconds: number;                    // 全局超时

  // 核心内容
  tasks: { [task_id: string]: TaskIR };       // 所有任务
  entry_points: string[];                     // 入口任务 ID 列表
  output_tasks: string[];                     // 最终输出任务 ID 列表

  // 全局约束
  global_constraints?: GlobalConstraint[];

  // 元协议
  metadata?: {
    planner_model?: string;                   // 生成此图的 Planner 模型
    planner_prompt_version?: string;          // Planner prompt 版本
    total_estimated_cost?: number;            // 预估总 token 成本
    tags?: string[];                          // 标签
  };
};
```

### 3.2 全局约束

```typescript
type GlobalConstraint = {
  kind: "resource_limit" | "time_limit" | "cost_limit" | "security_policy";
  value: IRValue;
  description?: string;
};

// 示例
const constraints: GlobalConstraint[] = [
  { kind: "cost_limit", value: 50000, description: "总 token 消耗不超过 50K" },
  { kind: "time_limit", value: 300, description: "总执行时间不超过 5 分钟" },
];
```

---

## 四、Task IR

### 4.1 核心结构

```typescript
type TaskIR = {
  // 标识
  id: string;                                 // task_id (graph 内唯一)
  name: string;                               // 人类可读名称
  description: string;                        // 任务描述（给 LLM 的指令）

  // 依赖
  dependencies: string[];                     // 依赖的 task_id 列表
  dependency_mode: "all" | "any";             // all=全部完成, any=任一完成

  // 执行配置
  executor: "llm" | "tool" | "code" | "human" | "composite";
  model?: string;                             // 指定 LLM 模型（executor=llm 时）
  tool_id?: string;                           // 工具 ID（executor=tool 时）
  timeout_seconds?: number;                   // 任务级超时（覆盖全局）
  max_retries?: number;                       // 最大重试次数（默认 2）
  retry_delay_seconds?: number;               // 重试间隔（默认 5）

  // 输入输出契约
  input_schema: IRSchema;                     // 输入数据 schema
  output_schema: IRSchema;                    // 输出数据 schema

  // 验证配置
  validation: ValidationConfig;

  // 成本控制
  cost?: {
    max_tokens?: number;                      // 最大 token 数
    max_cost_usd?: number;                    // 最大美元成本
  };

  // 上下文
  context?: {
    include_artifacts?: string[];             // 显式引用的 artifact_id
    max_context_tokens?: number;              // 上下文窗口上限
  };

  // 失败处理
  on_failure?: FailureHandler;

  // 扩展
  metadata?: { [key: string]: IRValue };
};
```

### 4.2 验证配置

```typescript
type ValidationConfig = {
  // 验证级别
  level: "none" | "schema_only" | "full";

  // Schema 验证（始终执行，除非 level=none）
  schema_validation: {
    strict: boolean;                          // true=严格模式, false=允许额外字段
    coerce_types?: boolean;                   // 是否尝试类型转换
  };

  // 语义验证（level=full 时执行）
  semantic?: {
    // 矛盾检测
    contradiction_check: boolean;
    contradiction_domains?: string[];         // 限定检测领域（空=全部）

    // 声明重叠检测
    claim_overlap_check: boolean;
    overlap_threshold?: number;               // Jaccard 相似度阈值（默认 0.85）

    // 自定义验证器
    custom_validators?: string[];             // 验证器 ID 列表
  };

  // 验证通过条件
  acceptance: {
    min_confidence: number;                   // 最低置信度（0-1）
    require_human_review?: boolean;           // 是否必须人工审核
  };
};
```

### 4.3 失败处理器

```typescript
type FailureHandler = {
  // 失败时的动作
  action: "retry" | "skip" | "fail_graph" | "fallback" | "notify_human";

  // fallback 配置
  fallback_task?: TaskIR;                    // 替代任务（action=fallback 时）

  // 降级策略
  degradation?: {
    reduce_quality?: boolean;                 // 允许降低质量
    use_cheaper_model?: string;               // 使用更便宜的模型
    simplify_schema?: boolean;                // 简化输出 schema
  };

  // 通知
  notify_on?: ("retry" | "skip" | "fail")[];
};
```

### 4.4 任务类型详解

#### LLM Task（最常用）
```typescript
// executor: "llm"
const llmTask: TaskIR = {
  id: "summarize_results",
  name: "汇总分析结果",
  description: "基于所有分析任务的输出，生成一份综合摘要报告",
  dependencies: ["analyze_logs", "check_anomalies"],
  dependency_mode: "all",
  executor: "llm",
  model: "deepseek-v4-flash",                // 可选，默认使用系统模型
  timeout_seconds: 120,
  max_retries: 2,
  input_schema: {
    type: "object",
    properties: {
      analysis_results: { type: "array", items: { type: "object" } },
      anomalies: { type: "array", items: { type: "object" } },
    },
    required: ["analysis_results"],
  },
  output_schema: {
    type: "object",
    properties: {
      summary: { type: "string", maxLength: 5000 },
      key_findings: { type: "array", items: { type: "string" } },
      confidence_score: { type: "number", minimum: 0, maximum: 1 },
    },
    required: ["summary", "key_findings"],
  },
  validation: {
    level: "full",
    schema_validation: { strict: true },
    semantic: {
      contradiction_check: true,
      claim_overlap_check: true,
      overlap_threshold: 0.85,
    },
    acceptance: { min_confidence: 0.7 },
  },
  on_failure: {
    action: "retry",
    degradation: { use_cheaper_model: "deepseek-v4-flash" },
  },
};
```

#### Tool Task
```typescript
// executor: "tool"
const toolTask: TaskIR = {
  id: "fetch_weather_data",
  name: "获取天气数据",
  description: "调用天气 API 获取指定城市的实时天气",
  dependencies: [],
  dependency_mode: "all",
  executor: "tool",
  tool_id: "weather_api",
  timeout_seconds: 30,
  max_retries: 3,
  input_schema: {
    type: "object",
    properties: {
      city: { type: "string", minLength: 1 },
      units: { type: "string", enum: ["metric", "imperial"], default: "metric" },
    },
    required: ["city"],
  },
  output_schema: {
    type: "object",
    properties: {
      temperature: { type: "number" },
      humidity: { type: "number", minimum: 0, maximum: 100 },
      conditions: { type: "string" },
    },
    required: ["temperature", "conditions"],
  },
  validation: {
    level: "schema_only",
    schema_validation: { strict: true },
    acceptance: { min_confidence: 1.0 },
  },
};
```

#### Code Task
```typescript
// executor: "code" — 执行一段生成的代码
const codeTask: TaskIR = {
  id: "transform_data",
  name: "数据转换",
  description: "执行数据清洗和格式转换",
  dependencies: ["fetch_raw_data"],
  dependency_mode: "all",
  executor: "code",
  timeout_seconds: 60,
  input_schema: {
    type: "object",
    properties: {
      raw_data: { type: "array", items: { type: "object" } },
      transform_rules: { type: "object" },
    },
    required: ["raw_data"],
  },
  output_schema: {
    type: "object",
    properties: {
      transformed_data: { type: "array", items: { type: "object" } },
      row_count: { type: "number" },
      errors: { type: "array", items: { type: "string" } },
    },
    required: ["transformed_data", "row_count"],
  },
  validation: {
    level: "schema_only",
    schema_validation: { strict: true },
    acceptance: { min_confidence: 1.0 },
  },
};
```

#### Human Task
```typescript
// executor: "human" — 需要人工介入
const humanTask: TaskIR = {
  id: "approve_final_report",
  name: "审批最终报告",
  description: "人工审核并批准最终报告",
  dependencies: ["generate_report"],
  dependency_mode: "all",
  executor: "human",
  timeout_seconds: 86400,                    // 24 小时
  input_schema: {
    type: "object",
    properties: {
      report: { type: "string" },
      draft_version: { type: "string" },
    },
    required: ["report"],
  },
  output_schema: {
    type: "object",
    properties: {
      approved: { type: "boolean" },
      feedback: { type: "string" },
      approved_version: { type: "string" },
    },
    required: ["approved"],
  },
  validation: {
    level: "none",                           // 人工任务不需要验证
    schema_validation: { strict: false },
    acceptance: { min_confidence: 1.0 },
  },
};
```

#### Composite Task
```typescript
// executor: "composite" — 包含子图的复合任务
const compositeTask: TaskIR = {
  id: "full_analysis_pipeline",
  name: "完整分析流水线",
  description: "执行完整的数据分析流水线（包含子任务图）",
  dependencies: [],
  dependency_mode: "all",
  executor: "composite",
  timeout_seconds: 600,
  input_schema: {
    type: "object",
    properties: {
      data_source: { type: "string" },
      analysis_type: { type: "string", enum: ["full", "quick", "deep"] },
    },
    required: ["data_source"],
  },
  output_schema: {
    type: "object",
    properties: {
      final_report: { type: "string" },
      all_metrics: { type: "object" },
    },
    required: ["final_report"],
  },
  validation: {
    level: "full",
    schema_validation: { strict: true },
    semantic: { contradiction_check: true, claim_overlap_check: true },
    acceptance: { min_confidence: 0.8 },
  },
  // Composite 特有：子图
  subgraph?: TaskGraphIR;                    // 子任务图（递归）
};
```

---

## 五、Contract IR

Contract 是 Task 的输入输出契约，用于 Executor 和 Validator 之间的数据交换。

### 5.1 Input Contract

```typescript
// Executor 收到的输入
type InputContract = {
  task_id: string;
  task_name: string;
  task_description: string;                  // 给 LLM 的完整指令

  // 输入数据（来自上游任务的 Artifact）
  inputs: {
    [dependency_task_id: string]: {          // 按依赖任务 ID 索引
      artifacts: ArtifactIR[];               // 该任务产生的所有 Artifact
    };
  };

  // 全局上下文
  global_context?: {
    session_id: string;
    user_intent: string;
    world_state?: WorldStateSnapshot;
    failure_memory?: FailureMemorySnapshot;
  };

  // 执行约束
  constraints: {
    max_tokens?: number;
    max_cost_usd?: number;
    timeout_seconds: number;
    allowed_tools?: string[];
  };
};
```

### 5.2 Output Contract

```typescript
// Executor 产生的输出
type OutputContract = {
  task_id: string;
  status: "success" | "failure" | "partial";

  // 输出数据
  artifacts: ArtifactIR[];

  // 执行元信息
  execution_meta: {
    model_used?: string;
    tokens_used?: number;
    cost_usd?: number;
    started_at: string;                      // ISO 8601
    completed_at: string;                    // ISO 8601
    retry_count: number;
  };

  // 失败信息
  error?: {
    kind: FailureKind;
    message: string;
    details?: IRValue;
    stack_trace?: string;
  };

  // 置信度
  confidence?: number;                       // 0-1
};
```

### 5.3 Validation Contract

```typescript
// Validator 的验证结果
type ValidationContract = {
  task_id: string;
  verdict: Verdict;

  // Schema 验证结果
  schema_check: {
    passed: boolean;
    errors?: Array<{
      path: string;                          // JSON path
      expected: string;
      actual: string;
    }>;
  };

  // 语义验证结果
  semantic_check?: {
    contradictions?: Array<{
      claim_a: string;
      claim_b: string;
      severity: "low" | "medium" | "high";
      explanation: string;
    }>;
    overlaps?: Array<{
      claim: string;
      similar_to_task: string;
      similarity: number;
    }>;
    confidence_assessment?: {
      score: number;
      reasoning: string;
    };
  };

  // 验证元信息
  meta: {
    validator_model: string;
    validation_tokens: number;
    validation_time_ms: number;
  };
};
```

---

## 六、Artifact IR

Artifact 是 Task 产生的数据单元，在 Store 中持久化。

### 6.1 核心结构

```typescript
type ArtifactIR = {
  // 标识
  id: string;                                // UUID v4
  task_id: string;                           // 产生此 Artifact 的 Task
  name: string;                              // 人类可读名称

  // 内容
  type: "text" | "json" | "code" | "image" | "file" | "composite";
  content: IRValue;                          // 实际数据
  mime_type?: string;                        // MIME type

  // Schema
  schema?: IRSchema;                         // 此 Artifact 的数据 schema

  // 元数据
  size_bytes?: number;
  checksum?: string;                         // SHA-256
  created_at: string;                        // ISO 8601

  // 版本
  version: number;                           // 递增版本号
  parent_artifact_id?: string;               // 前一个版本 ID

  // 标签
  tags?: string[];
};
```

### 6.2 Artifact 引用

```typescript
// 在 Task IR 中引用 Artifact
type ArtifactRef = {
  artifact_id: string;                       // 直接引用
  // 或
  task_id?: string;                          // 引用某任务的最新 Artifact
  name?: string;                             // Artifact 名称
  version?: number;                          // 指定版本（默认最新）
};
```

---

## 七、Execution State IR

运行时状态快照，用于 `freeze()` / `resume()` 和故障恢复。

### 7.1 状态快照

```typescript
type ExecutionSnapshot = {
  // 标识
  snapshot_id: string;                       // UUID v4
  graph_id: string;
  timestamp: string;                         // ISO 8601

  // 任务状态
  task_states: {
    [task_id: string]: {
      status: TaskStatus;
      retry_count: number;
      started_at?: string;
      completed_at?: string;
      error?: {
        kind: FailureKind;
        message: string;
      };
    };
  };

  // 就绪队列
  ready_queue: string[];                     // 当前就绪的 task_id

  // 运行中
  running_tasks: string[];                   // 当前正在执行的 task_id

  // 已完成
  completed_artifacts: {
    [task_id: string]: ArtifactIR[];         // 已产生的 Artifact
  };

  // 调度器状态
  scheduler_state: {
    active_count: number;
    completed_count: number;
    failed_count: number;
    total_count: number;
    concurrency_slots: number;               // 当前可用并发槽
  };

  // 上下文（压缩后）
  compressed_context?: {
    world_state_hash: string;
    failure_memory_hash: string;
  };
};
```

### 7.2 恢复点

```typescript
type RecoveryPoint = {
  snapshot: ExecutionSnapshot;
  // 从哪个任务开始恢复
  resume_from: string[];                     // task_id 列表
  // 恢复策略
  strategy: "restart_failed" | "restart_all" | "continue";
};
```

---

## 八、Failure Memory IR

Failure Memory 是压缩后的学习信号，用于指导 Planner 避免重复错误。

### 8.1 失败记录

```typescript
type FailureRecord = {
  id: string;                                // UUID v4
  task_id: string;
  graph_id: string;

  // 失败信息
  kind: FailureKind;
  message: string;

  // 压缩后的学习信号
  compressed_signal: {
    // 一句话总结（给 Planner 的提示）
    lesson: string;
    // 根因分析
    root_cause: string;
    // 建议的修复方式
    suggested_fix: string;
    // 关键词（用于检索匹配）
    keywords: string[];
  };

  // 上下文（压缩后）
  context_hash?: string;                     // 输入上下文的 hash
  similar_failures?: string[];               // 相似失败记录 ID

  // 统计
  occurrence_count: number;
  first_seen: string;
  last_seen: string;

  // Token 预算
  token_cost: number;                        // 此记录占用的 token 数
};
```

### 8.2 失败记忆快照

```typescript
type FailureMemorySnapshot = {
  // 当前图相关的失败记录
  relevant_failures: FailureRecord[];
  // 全局高频失败模式
  top_patterns: Array<{
    pattern: string;
    frequency: number;
    last_occurrence: string;
  }>;
  // Token 预算上限
  total_token_budget: number;
  used_tokens: number;
};
```

---

## 九、完整示例

### 9.1 数据分析流水线

```json
{
  "graph_id": "g-123e4567-e89b-12d3-a456-426614174000",
  "version": "1.0.0",
  "created_at": "2026-06-22T16:00:00.000Z",
  "updated_at": "2026-06-22T16:00:00.000Z",
  "session_id": "s-abc123",
  "user_intent": "分析服务器日志，检测异常并生成报告",
  "max_concurrency": 3,
  "timeout_seconds": 600,

  "entry_points": ["fetch_logs"],
  "output_tasks": ["generate_report"],

  "tasks": {
    "fetch_logs": {
      "id": "fetch_logs",
      "name": "获取日志",
      "description": "从指定服务器获取最近24小时的日志文件",
      "dependencies": [],
      "dependency_mode": "all",
      "executor": "tool",
      "tool_id": "log_fetcher",
      "timeout_seconds": 30,
      "max_retries": 3,
      "input_schema": {
        "type": "object",
        "properties": {
          "server": { "type": "string", "description": "服务器地址" },
          "hours": { "type": "number", "default": 24 }
        },
        "required": ["server"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "log_entries": {
            "type": "array",
            "items": { "type": "object" },
            "description": "日志条目列表"
          },
          "total_lines": { "type": "number" },
          "time_range": { "type": "string" }
        },
        "required": ["log_entries", "total_lines"]
      },
      "validation": {
        "level": "schema_only",
        "schema_validation": { "strict": true },
        "acceptance": { "min_confidence": 1.0 }
      }
    },

    "analyze_errors": {
      "id": "analyze_errors",
      "name": "分析错误",
      "description": "分析日志中的错误条目，分类统计错误类型和频率",
      "dependencies": ["fetch_logs"],
      "dependency_mode": "all",
      "executor": "llm",
      "model": "deepseek-v4-flash",
      "timeout_seconds": 120,
      "max_retries": 2,
      "input_schema": {
        "type": "object",
        "properties": {
          "log_entries": { "type": "array", "items": { "type": "object" } }
        },
        "required": ["log_entries"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "error_summary": { "type": "string" },
          "error_types": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "type": { "type": "string" },
                "count": { "type": "number" },
                "severity": { "type": "string", "enum": ["low", "medium", "high", "critical"] }
              },
              "required": ["type", "count", "severity"]
            }
          },
          "total_errors": { "type": "number" }
        },
        "required": ["error_summary", "error_types", "total_errors"]
      },
      "validation": {
        "level": "full",
        "schema_validation": { "strict": true },
        "semantic": {
          "contradiction_check": true,
          "claim_overlap_check": true,
          "overlap_threshold": 0.85
        },
        "acceptance": { "min_confidence": 0.7 }
      },
      "on_failure": {
        "action": "retry",
        "degradation": { "use_cheaper_model": "deepseek-v4-flash" }
      }
    },

    "check_anomalies": {
      "id": "check_anomalies",
      "name": "检测异常",
      "description": "基于日志数据检测异常模式（流量突增、错误率飙升等）",
      "dependencies": ["fetch_logs"],
      "dependency_mode": "all",
      "executor": "llm",
      "timeout_seconds": 120,
      "input_schema": {
        "type": "object",
        "properties": {
          "log_entries": { "type": "array", "items": { "type": "object" } }
        },
        "required": ["log_entries"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "anomalies": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "type": { "type": "string" },
                "description": { "type": "string" },
                "severity": { "type": "string", "enum": ["low", "medium", "high", "critical"] },
                "affected_services": { "type": "array", "items": { "type": "string" } }
              },
              "required": ["type", "description", "severity"]
            }
          },
          "overall_risk": { "type": "string", "enum": ["low", "medium", "high"] }
        },
        "required": ["anomalies", "overall_risk"]
      },
      "validation": {
        "level": "full",
        "schema_validation": { "strict": true },
        "semantic": {
          "contradiction_check": true,
          "claim_overlap_check": true
        },
        "acceptance": { "min_confidence": 0.7 }
      }
    },

    "generate_report": {
      "id": "generate_report",
      "name": "生成报告",
      "description": "基于错误分析和异常检测结果，生成一份综合运维报告",
      "dependencies": ["analyze_errors", "check_anomalies"],
      "dependency_mode": "all",
      "executor": "llm",
      "timeout_seconds": 180,
      "input_schema": {
        "type": "object",
        "properties": {
          "error_summary": { "type": "string" },
          "error_types": { "type": "array", "items": { "type": "object" } },
          "total_errors": { "type": "number" },
          "anomalies": { "type": "array", "items": { "type": "object" } },
          "overall_risk": { "type": "string" }
        },
        "required": ["error_summary", "anomalies"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "report_title": { "type": "string" },
          "executive_summary": { "type": "string", "maxLength": 2000 },
          "detailed_findings": { "type": "string" },
          "recommendations": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "priority": { "type": "string", "enum": ["P0", "P1", "P2", "P3"] },
                "action": { "type": "string" },
                "expected_impact": { "type": "string" }
              },
              "required": ["priority", "action"]
            }
          },
          "report_format": { "type": "string", "enum": ["markdown", "html", "pdf"] }
        },
        "required": ["report_title", "executive_summary", "recommendations"]
      },
      "validation": {
        "level": "full",
        "schema_validation": { "strict": true },
        "semantic": {
          "contradiction_check": true,
          "claim_overlap_check": true
        },
        "acceptance": { "min_confidence": 0.8 }
      },
      "on_failure": {
        "action": "fallback",
        "fallback_task": {
          "id": "generate_report_fallback",
          "name": "生成简化报告",
          "description": "生成简化版报告（降级方案）",
          "dependencies": ["analyze_errors", "check_anomalies"],
          "dependency_mode": "all",
          "executor": "llm",
          "timeout_seconds": 120,
          "input_schema": { "type": "object", "properties": {} },
          "output_schema": {
            "type": "object",
            "properties": {
              "summary": { "type": "string" },
              "key_issues": { "type": "array", "items": { "type": "string" } }
            },
            "required": ["summary", "key_issues"]
          },
          "validation": {
            "level": "schema_only",
            "schema_validation": { "strict": false },
            "acceptance": { "min_confidence": 0.5 }
          }
        }
      }
    }
  },

  "global_constraints": [
    { "kind": "cost_limit", "value": 30000, "description": "总 token 消耗不超过 30K" },
    { "kind": "time_limit", "value": 600, "description": "总执行时间不超过 10 分钟" }
  ],

  "metadata": {
    "planner_model": "deepseek-v4-flash",
    "planner_prompt_version": "1.0.0",
    "total_estimated_cost": 15000,
    "tags": ["ops", "log-analysis", "automated"]
  }
}
```

### 9.2 对应的 Artifact 示例

```json
{
  "id": "a-223e4567-e89b-12d3-a456-426614174000",
  "task_id": "analyze_errors",
  "name": "错误分析结果",
  "type": "json",
  "content": {
    "error_summary": "检测到 3 类主要错误：数据库连接超时（45次）、内存溢出（12次）、权限拒绝（8次）",
    "error_types": [
      { "type": "DB_CONNECTION_TIMEOUT", "count": 45, "severity": "high" },
      { "type": "OUT_OF_MEMORY", "count": 12, "severity": "critical" },
      { "type": "PERMISSION_DENIED", "count": 8, "severity": "medium" }
    ],
    "total_errors": 65
  },
  "mime_type": "application/json",
  "size_bytes": 512,
  "checksum": "sha256-a1b2c3d4e5f6...",
  "created_at": "2026-06-22T16:05:00.000Z",
  "version": 1,
  "tags": ["analysis", "errors"]
}
```

### 9.3 对应的 Execution Snapshot 示例

```json
{
  "snapshot_id": "s-323e4567-e89b-12d3-a456-426614174000",
  "graph_id": "g-123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-06-22T16:03:00.000Z",
  "task_states": {
    "fetch_logs": { "status": "completed", "retry_count": 0, "completed_at": "2026-06-22T16:01:30.000Z" },
    "analyze_errors": { "status": "running", "retry_count": 0, "started_at": "2026-06-22T16:02:00.000Z" },
    "check_anomalies": { "status": "running", "retry_count": 0, "started_at": "2026-06-22T16:02:05.000Z" },
    "generate_report": { "status": "pending", "retry_count": 0 }
  },
  "ready_queue": [],
  "running_tasks": ["analyze_errors", "check_anomalies"],
  "completed_artifacts": {
    "fetch_logs": [
      {
        "id": "a-123e4567-e89b-12d3-a456-426614174000",
        "task_id": "fetch_logs",
        "name": "原始日志",
        "type": "json",
        "content": { "log_entries": [], "total_lines": 15000, "time_range": "2026-06-21T16:00~2026-06-22T16:00" }
      }
    ]
  },
  "scheduler_state": {
    "active_count": 2,
    "completed_count": 1,
    "failed_count": 0,
    "total_count": 4,
    "concurrency_slots": 1
  }
}
```

---

## 十、序列化格式

### 10.1 JSON（主要格式）

```typescript
// 默认序列化格式
type SerializedIR = string;                  // JSON string

// 序列化选项
type SerializationOptions = {
  pretty?: boolean;                          // 美化输出
  sort_keys?: boolean;                       // 排序 key
  skip_validation?: boolean;                 // 跳过 schema 验证
  max_depth?: number;                        // 最大深度（默认 10）
};
```

### 10.2 Protobuf（高性能场景）

```protobuf
// 未来扩展：Protobuf schema 示例
syntax = "proto3";
package agentos.ir.v1;

message TaskGraph {
  string graph_id = 1;
  string version = 2;
  string created_at = 3;
  // ... 其他字段
}
```

### 10.3 压缩格式

```typescript
// 大数据量场景使用压缩
type CompressedIR = {
  format: "gzip" | "zstd";
  original_size: number;
  compressed_size: number;
  checksum: string;
  data: string;                              // base64 编码的压缩数据
};
```

---

## 十一、版本兼容性

### 11.1 版本策略

| 版本变化 | 兼容性 | 示例 |
|---------|--------|------|
| patch (1.0.x) | 完全向后兼容 | 新增可选字段 |
| minor (1.x.0) | 向后兼容 | 新增必需字段（有默认值） |
| major (x.0.0) | 不兼容 | 删除/重命名字段 |

### 11.2 版本协商

```typescript
// 组件之间协商 IR 版本
type VersionNegotiation = {
  supported_versions: string[];              // 支持的版本列表
  preferred_version: string;                 // 首选版本
  min_version: string;                       // 最低可接受版本
};
```

### 11.3 迁移指南

```markdown
# 版本迁移

## 1.0.0 → 1.1.0
- 新增: `TaskIR.on_failure.degradation` 字段
- 新增: `TaskGraphIR.global_constraints` 字段
- 兼容: 旧 IR 无需修改

## 1.0.0 → 2.0.0
- 变更: `TaskIR.executor` 类型从 string 改为 enum
- 变更: `ArtifactIR.content` 从 string 改为 IRValue
- 迁移: 需要更新序列化/反序列化逻辑
```

---

## 附录 A：JSON Schema 校验

完整的 IR 校验 JSON Schema 定义在 `specs/ir-schema.json`。

```bash
# 使用 ajv 校验 IR
npx ajv validate -s specs/ir-schema.json -d examples/sample-graph.json
```

## 附录 B：IR 工具函数

```python
# 建议的 Python 工具函数接口
class IRError(Exception): ...

def validate_ir(ir: dict) -> list[str]:
    """校验 IR 合法性，返回错误列表（空=合法）"""
    ...

def serialize_ir(ir: TaskGraphIR, options: SerializationOptions = None) -> str:
    """序列化 IR 为 JSON"""
    ...

def deserialize_ir(data: str) -> TaskGraphIR:
    """反序列化 JSON 为 IR"""
    ...

def diff_ir(before: TaskGraphIR, after: TaskGraphIR) -> list[Change]:
    """比较两个 IR 的差异"""
    ...

def merge_ir(base: TaskGraphIR, patch: TaskGraphIR) -> TaskGraphIR:
    """合并两个 IR（用于增量更新）"""
    ...
```

---

> **文档版本**: 1.0.0
> **最后更新**: 2026-06-22
> **作者**: 小鸣 🦊
