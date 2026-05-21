# Agent Test Framework 🧪

> **LLM-as-a-Judge 驱动的 AI Agent 自动化测试框架** — 让 AI 应用从"能用"到"靠谱"

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-orange.svg)]()

## 痛点

构建 AI Agent 时，你怎么知道它"好用"？
- ❌ 传统单元测试无法评估 LLM 输出的"质量"
- ❌ 每次改 prompt 都要手动测试一堆 case
- ❌ 没有量化指标，改完是好是坏全凭感觉
- ❌ 无法做回归测试：新功能会不会破坏旧能力？

**Agent Test Framework** 用 LLM 作为评判者（LLM-as-a-Judge），为 AI Agent 提供结构化、可重复、可量化的测试流程。

## 功能

- ✅ **Golden Dataset 管理** — 构建和维护 Agent 测试用例集
- ✅ **LLM-as-a-Judge 评估** — 用大模型自动评估 Agent 输出质量
- ✅ **多维度评分** — 准确性、完整性、安全性等自定义评分维度
- ✅ **回归追踪** — 记录每次测试结果，对比版本间质量变化
- ✅ **HTML 报告** — 一键生成可视化测试报告
- ✅ **分类统计** — 按用例类型/难度分组分析通过率

## 安装

```bash
pip install agent-test-framework
# 或直接从源码使用
git clone https://github.com/kaising-openclaw1/agent-test-framework.git
```

## 快速开始

### 1. 构建 Golden Dataset

```python
from agent_test_framework import GoldenDataset, TestCase

dataset = GoldenDataset(name="customer_service_v1")

dataset.add_case(TestCase(
    id="cs_greeting_01",
    input="你好，我想查一下我的订单状态",
    expected_output="热情问候，引导用户提供订单号",
    category="对话",
    difficulty="easy",
    tools_available=["order_lookup"],
    evaluation_criteria=["礼貌性", "信息准确性", "引导有效性"],
))

dataset.add_case(TestCase(
    id="cs_refund_01",
    input="我收到的商品有质量问题，要求退款",
    expected_output="表达歉意，确认订单信息，说明退款流程，给出明确时间线",
    category="工具调用",
    difficulty="hard",
    tools_available=["order_lookup", "refund_process", "customer_record"],
    evaluation_criteria=["同理心", "流程正确性", "信息完整性", "合规性"],
))

dataset.save("golden_dataset.json")
```

### 2. 运行测试

```python
from agent_test_framework import GoldenDataset, LLMEvaluator, TestRunner

# 加载数据集
dataset = GoldenDataset.load("golden_dataset.json")

# 定义你的 Agent 函数
def my_agent(input_text: str, tools: list) -> str:
    # 你的 Agent 实现
    return "..."

# 创建评估器和测试运行器
evaluator = LLMEvaluator(
    judge_model="gpt-4",
    scoring_rubric="10分制",
    pass_threshold=7.0,
)

runner = TestRunner(evaluator=evaluator, agent_fn=my_agent)

# 运行测试
results = runner.run_suite(dataset)

# 查看摘要
print(runner.summary())
# {
#   "total": 20,
#   "passed": 17,
#   "failed": 3,
#   "pass_rate": "85.0%",
#   "avg_score": "8.2/10",
#   "avg_latency_ms": "1250ms",
#   "category_stats": {...}
# }
```

### 3. 回归追踪

```python
from agent_test_framework import RegressionTracker

tracker = RegressionTracker()

# 记录当前版本结果
tracker.record("v1.0.0", results)

# 加载历史结果做对比
tracker.load("regression_history.json")
diff = tracker.compare("v1.0.0", "v1.1.0")

print(f"改进: {diff.improved} 个用例")
print(f"退化: {diff.regressed} 个用例")
```

### 4. 生成报告

```python
from agent_test_framework import generate_html_report

generate_html_report(
    results,
    output="test_report.html",
    title="Agent v1.0 测试报告",
    timestamp="2026-05-20",
)
```

## 架构

```
agent_test_framework/
├── __init__.py           # 公共 API
├── golden_dataset.py     # Golden Dataset 管理
├── evaluator.py          # LLM-as-a-Judge 评估器 + 测试运行器
├── regression.py         # 回归追踪
└── report.py             # HTML 报告生成
```

## 评分标准

默认使用 10 分制：

| 分数 | 评价 |
|------|------|
| 9-10 | 完全符合预期，质量优秀 |
| 7-8  | 基本符合预期，有轻微不足 |
| 5-6  | 部分符合预期，有明显改进空间 |
| 3-4  | 偏离预期，质量较差 |
| 1-2  | 完全不符合预期，不可接受 |

可通过 `pass_threshold` 参数调整及格线（默认 7.0）。

## 适用场景

- 🤖 **AI 客服 Agent** — 测试对话质量、工具调用准确性
- 📝 **内容生成 Agent** — 评估输出内容的准确性、风格一致性
- 🔍 **RAG 系统** — 验证检索+生成的端到端质量
- 🛠️ **Agent 开发迭代** — 每次改 prompt/model 后跑回归测试
- 📊 **质量监控** — 持续监控 Agent 质量趋势

## 与 CI/CD 集成

```yaml
# .github/workflows/test-agent.yml
- name: Run Agent Tests
  run: |
    python tests/run_agent_tests.py
    python tests/generate_report.py
```

## License

MIT License

## Author

大凯 · 小鸣
