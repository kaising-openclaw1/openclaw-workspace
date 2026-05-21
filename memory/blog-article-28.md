# 手把手教你用 Python 构建 AI Agent 自动化测试框架：LLM-as-a-Judge 实战

> **目标平台：** 掘金 / 知乎 / V2EX / InfoQ / CSDN
> **字数：** 约 4500 字
> **标签：** AI Agent, LLM-as-a-Judge, 自动化测试, Python, 质量保障, MLOps
> **配套项目：** github.com/kaising-openclaw1/agent-test-framework

---

## 前言：你的 AI Agent 靠谱吗？

2026 年，AI Agent 已经从实验室走向了生产环境。企业用 Agent 做客服、数据分析、代码审查、文档生成……但一个被广泛忽视的问题是：**你怎么知道 Agent 的输出是靠谱的？**

传统软件测试有明确的"预期输出"——输入 2+2，期望得到 4。但 AI Agent 的输出是自然语言，同一个问题可以有多种"正确"回答。传统的 assertEqual 在这里完全失效。

这就是 **LLM-as-a-Judge** 的用武之地：用更强的大模型来评估你的 Agent 输出质量。

本文将带你从零构建一个完整的 AI Agent 测试框架，包含：
- Golden Dataset（黄金测试集）管理
- LLM-as-a-Judge 自动评估
- 回归测试与质量趋势追踪
- 一键生成可视化 HTML 报告

完整源码已开源：**Agent Test Framework**（链接见文末）。

---

## 一、为什么 AI Agent 需要专门的测试框架？

### 1.1 传统测试的局限

```python
# 传统单元测试 ✅
def test_add():
    assert add(2, 2) == 4  # 明确、确定

# AI Agent 测试 ❌
def test_customer_service():
    response = agent.handle("我要退款")
    assert response == "好的，请提供订单号"  # 太死板了！
```

Agent 对"我要退款"可以有无数种合格的回答：
- "好的，麻烦提供一下您的订单号，我帮您处理。"
- "理解您的需求，请问订单号是多少？我马上为您处理退款。"
- "没问题，请给我您的订单号，我来协助您完成退款流程。"

这些回答都合格，但 `assertEqual` 只会认其中一个。

### 1.2 LLM-as-a-Judge 的思路

用 GPT-4、Claude 等强模型作为"评委"，给定评分标准，让它判断 Agent 的输出质量：

```
请根据以下标准评估 Agent 的回答：
- 礼貌性：是否使用了礼貌用语
- 信息准确性：是否正确引导用户提供订单号
- 流程正确性：是否提及退款处理流程

Agent 回答："好的，请提供订单号"
评分：7/10 — 简洁但缺乏同理心，没有说明后续流程
```

这种方法既灵活又量化，还能生成改进建议。

---

## 二、构建 Golden Dataset（黄金测试集）

### 2.1 什么是 Golden Dataset？

Golden Dataset 是一组精心设计的测试用例，每个用例包含：
- **输入**：用户给 Agent 的问题或指令
- **期望输出**：语义描述（不是精确字符串）
- **评估标准**：从哪些维度判断输出质量
- **可用工具**：Agent 此时可以调用的工具列表

### 2.2 用 Python 实现 Golden Dataset 管理

```python
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class TestCase:
    """单个测试用例"""
    id: str
    input: str                    # 用户输入
    expected_output: str          # 期望输出（语义描述）
    category: str                 # 分类：问答/工具调用/推理/对话
    difficulty: str = "medium"    # 难度
    tools_available: list = field(default_factory=list)
    evaluation_criteria: list = field(default_factory=list)


class GoldenDataset:
    """Golden Dataset 管理器"""

    def __init__(self, name: str = "default"):
        self.name = name
        self.cases: dict[str, TestCase] = {}

    def add_case(self, case: TestCase) -> None:
        self.cases[case.id] = case

    def get_by_category(self, category: str) -> list[TestCase]:
        return [c for c in self.cases.values() if c.category == category]

    def get_by_difficulty(self, difficulty: str) -> list[TestCase]:
        return [c for c in self.cases.values() if c.difficulty == difficulty]

    @property
    def total(self) -> int:
        return len(self.cases)

    def save(self, path: str) -> None:
        data = {"name": self.name, "cases": {}}
        for cid, c in self.cases.items():
            data["cases"][cid] = {
                "input": c.input,
                "expected_output": c.expected_output,
                "category": c.category,
                "difficulty": c.difficulty,
                "tools_available": c.tools_available,
                "evaluation_criteria": c.evaluation_criteria,
            }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Golden Dataset 已保存：{path}（{self.total} 个用例）")

    @classmethod
    def load(cls, path: str) -> "GoldenDataset":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ds = cls(name=data["name"])
        for cid, cdata in data["cases"].items():
            ds.add_case(TestCase(id=cid, **{
                k: cdata[k] for k in [
                    "input", "expected_output", "category", "difficulty",
                    "tools_available", "evaluation_criteria"
                ]
            }))
        return ds
```

### 2.3 构建一个客服 Agent 的测试集

```python
dataset = GoldenDataset(name="customer_service_v1")

# 用例 1：简单问候
dataset.add_case(TestCase(
    id="cs_greeting_01",
    input="你好，我想查一下我的订单状态",
    expected_output="热情问候，引导用户提供订单号",
    category="对话",
    difficulty="easy",
    tools_available=["order_lookup"],
    evaluation_criteria=["礼貌性", "引导有效性"],
))

# 用例 2：退款请求
dataset.add_case(TestCase(
    id="cs_refund_01",
    input="我收到的商品有质量问题，要求退款",
    expected_output="表达歉意，确认订单信息，说明退款流程，给出明确时间线",
    category="工具调用",
    difficulty="hard",
    tools_available=["order_lookup", "refund_process"],
    evaluation_criteria=["同理心", "流程正确性", "信息完整性"],
))

# 用例 3：投诉升级
dataset.add_case(TestCase(
    id="cs_escalation_01",
    input="你们的产品太差了！我要投诉你们经理！",
    expected_output="安抚情绪，道歉，记录投诉内容，提供升级渠道",
    category="对话",
    difficulty="hard",
    tools_available=["complaint_record", "escalate_to_manager"],
    evaluation_criteria=["情绪安抚", "合规性", "升级流程正确性"],
))

dataset.save("golden_dataset.json")
print(f"共 {dataset.total} 个测试用例")
```

一个好的 Golden Dataset 应该覆盖：
- 不同难度（简单问答 → 复杂多步任务）
- 不同类别（对话、工具调用、推理、安全边界）
- 边界情况（恶意输入、模糊指令、多语言）

---

## 三、实现 LLM-as-a-Judge 评估器

### 3.1 评估器核心逻辑

```python
from dataclasses import dataclass, field
import json
import time


def call_llm(messages: list[dict], model: str = "gpt-4") -> str:
    """接入你的 LLM API（OpenAI / Claude / DeepSeek 等）"""
    # 这里替换为实际的 API 调用
    raise NotImplementedError("请接入你的 LLM API")


@dataclass
class EvaluationResult:
    """单次评估结果"""
    case_id: str
    score: float
    passed: bool
    reasoning: str
    rubric_scores: dict = field(default_factory=dict)
    latency_ms: float = 0


class LLMEvaluator:
    """LLM-as-a-Judge 评估器"""

    def __init__(
        self,
        judge_model: str = "gpt-4",
        scoring_rubric: str = "10分制",
        pass_threshold: float = 7.0,
    ):
        self.judge_model = judge_model
        self.scoring_rubric = scoring_rubric
        self.pass_threshold = pass_threshold

    def build_evaluation_prompt(
        self, case_input, case_expected, agent_output, criteria
    ) -> list[dict]:
        criteria_text = "\n".join(f"- {c}" for c in criteria)

        system_prompt = f"""你是一个专业的 AI Agent 评估专家。
评分标准（{self.scoring_rubric}）：
- 9-10 分：完全符合预期，质量优秀
- 7-8 分：基本符合预期，有轻微不足
- 5-6 分：部分符合预期，有明显改进空间
- 3-4 分：偏离预期，质量较差
- 1-2 分：完全不符合预期，不可接受

请以 JSON 格式返回评估结果：
{{"score": 分数, "reasoning": "详细评估理由",
 "rubric_scores": {{"准确性": 分数, "完整性": 分数}}}}"""

        user_prompt = f"""## 用户输入
{case_input}

## 期望输出
{case_expected}

## Agent 实际输出
{agent_output}

## 评估标准
{criteria_text}"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def evaluate(self, case_id, case_input, case_expected,
                 agent_output, criteria=None) -> EvaluationResult:
        criteria = criteria or []
        start = time.time()

        messages = self.build_evaluation_prompt(
            case_input, case_expected, agent_output, criteria
        )
        response = call_llm(messages, model=self.judge_model)
        latency_ms = (time.time() - start) * 1000

        try:
            result = json.loads(response)
            score = float(result.get("score", 0))
            return EvaluationResult(
                case_id=case_id, score=score,
                passed=score >= self.pass_threshold,
                reasoning=result.get("reasoning", ""),
                rubric_scores=result.get("rubric_scores", {}),
                latency_ms=latency_ms,
            )
        except json.JSONDecodeError:
            return EvaluationResult(
                case_id=case_id, score=0, passed=False,
                reasoning=f"JSON 解析失败: {response[:200]}",
                latency_ms=latency_ms,
            )
```

### 3.2 接入实际 LLM API

以 DeepSeek API 为例（成本低，中文能力强）：

```python
from openai import OpenAI


def call_llm(messages, model="deepseek-chat"):
    client = OpenAI(
        api_key="your-deepseek-key",
        base_url="https://api.deepseek.com",
    )
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,  # 低温度保证评分一致性
    )
    return response.choices[0].message.content
```

> 💡 **成本控制技巧**：评估器用低成本模型即可，不一定需要 GPT-4。DeepSeek、Qwen 等国产模型在评分任务上表现已经相当不错，每次评估成本不到 ¥0.01。

---

## 四、测试运行器 + 回归追踪

### 4.1 批量运行测试

```python
class TestRunner:
    """测试运行器"""

    def __init__(self, evaluator: LLMEvaluator, agent_fn):
        self.evaluator = evaluator
        self.agent_fn = agent_fn  # 你的 Agent 函数
        self.results: list[EvaluationResult] = []

    def run_suite(self, dataset: GoldenDataset) -> list[EvaluationResult]:
        results = []
        total = dataset.total
        print(f"\n开始测试：{total} 个用例\n")

        for i, (cid, case) in enumerate(dataset.cases.items(), 1):
            print(f"[{i}/{total}] {cid}...", end=" ")

            agent_output = self.agent_fn(case.input, case.tools_available)

            result = self.evaluator.evaluate(
                case_id=cid,
                case_input=case.input,
                case_expected=case.expected_output,
                agent_output=agent_output,
                criteria=case.evaluation_criteria,
            )

            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} ({result.score:.1f}/10)")
            results.append(result)

        self.results = results
        return results

    def summary(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        avg_score = sum(r.score for r in self.results) / total

        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": f"{passed/total*100:.1f}%",
            "avg_score": f"{avg_score:.1f}/10",
        }
```

### 4.2 回归追踪

```python
class RegressionTracker:
    """回归追踪器 — 记录历史结果，对比版本变化"""

    def __init__(self):
        self.runs: dict[str, list[EvaluationResult]] = {}

    def record(self, version: str, results: list[EvaluationResult]):
        self.runs[version] = results

    def compare(self, v1: str, v2: str) -> dict:
        r1 = {r.case_id: r.score for r in self.runs[v1]}
        r2 = {r.case_id: r.score for r in self.runs[v2]}

        improved = [cid for cid in r2 if r2.get(cid, 0) > r1.get(cid, 0)]
        regressed = [cid for cid in r2 if r2.get(cid, 0) < r1.get(cid, 0)]

        return {
            "improved": improved,
            "regressed": regressed,
            "v1_avg": sum(r1.values()) / len(r1),
            "v2_avg": sum(r2.values()) / len(r2),
        }
```

### 4.3 完整使用示例

```python
# 1. 加载测试集
dataset = GoldenDataset.load("golden_dataset.json")

# 2. 创建评估器（用 DeepSeek 做评委，成本低）
evaluator = LLMEvaluator(
    judge_model="deepseek-chat",
    pass_threshold=7.0,
)

# 3. 定义你的 Agent
def my_agent(input_text: str, tools: list) -> str:
    # 这里接入你的实际 Agent 实现
    return "你好，请提供订单号，我帮你查询。"

# 4. 运行测试
runner = TestRunner(evaluator=evaluator, agent_fn=my_agent)
results = runner.run_suite(dataset)

# 5. 查看摘要
print("\n=== 测试摘要 ===")
summary = runner.summary()
for k, v in summary.items():
    print(f"  {k}: {v}")

# 6. 回归对比（第二次运行时）
tracker = RegressionTracker()
tracker.record("v1.0", results)
# ... 改进 Agent 后再次运行 ...
tracker.record("v1.1", new_results)
diff = tracker.compare("v1.0", "v1.1")
print(f"改进: {len(diff['improved'])} 个用例")
print(f"退化: {len(diff['regressed'])} 个用例")
```

---

## 五、实际应用场景

### 场景 1：Prompt 优化

改了 Agent 的 System Prompt 后，怎么知道有没有变好？

```bash
# 改 Prompt 前
$ python test_agent.py
总用例: 20 | 通过: 14 (70.0%) | 平均分: 6.8/10

# 改 Prompt 后
$ python test_agent.py
总用例: 20 | 通过: 17 (85.0%) | 平均分: 8.1/10
```

数据说话，不再凭感觉。

### 场景 2：模型切换评估

从 GPT-4 切换到 Claude，效果怎么样？

```python
# 同一个 Agent 实现，只换底层模型
results_gpt4 = run_with_model("gpt-4")
results_claude = run_with_model("claude-sonnet-4")

print(f"GPT-4:  {summary_gpt4['pass_rate']} 平均分 {summary_gpt4['avg_score']}")
print(f"Claude: {summary_claude['pass_rate']} 平均分 {summary_claude['avg_score']}")
```

### 场景 3：CI/CD 集成

```yaml
# .github/workflows/test-agent.yml
name: Test AI Agent
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Agent Tests
        run: python tests/run_suite.py
      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: test-report
          path: test_report.html
```

### 场景 4：生产质量监控

定期在生产环境抽样评估：

```python
# 每天凌晨运行，评估昨天的真实对话
yesterday_logs = load_production_logs(date="2026-05-19")
sample = random.sample(yesterday_logs, 50)

results = evaluator.evaluate_batch(sample)
if results.avg_score < 6.0:
    alert("Agent 质量下降！请立即检查")
```

---

## 六、最佳实践 & 避坑指南

### 6.1 Golden Dataset 的构建原则

1. **从真实场景出发**：不要凭空编造用例，从实际用户对话中提取
2. **覆盖边界情况**：恶意输入、模糊指令、多语言混合
3. **定期更新**：产品迭代后测试集也要跟着更新
4. **分级管理**：核心用例（必须通过）+ 扩展用例（锦上添花）

### 6.2 LLM-as-a-Judge 的局限性

1. **评委也会犯错**：用多个评委交叉验证
2. **一致性不够**：设置低 temperature（0.1-0.3）
3. **成本问题**：高频测试用低成本模型，关键评估用强模型
4. **自我偏好**：同模型评估同模型输出可能偏高分

### 6.3 评估成本控制

| 模型 | 单次评估成本（20 用例） | 推荐用途 |
|------|----------------------|----------|
| DeepSeek Chat | ~¥0.10 | 日常回归测试 |
| Qwen Plus | ~¥0.15 | 日常回归测试 |
| Claude Sonnet | ~¥0.30 | 重要版本发布 |
| GPT-4o | ~¥0.50 | 关键质量审计 |

---

## 七、开源项目

本文的完整实现已开源为 **Agent Test Framework**：

- 📦 **GitHub：** github.com/kaising-openclaw1/agent-test-framework
- ⭐ 功能：Golden Dataset + LLM 评估 + 回归追踪 + HTML 报告
- 🚀 安装：`pip install agent-test-framework`
- 📖 文档：见仓库 README

这个框架已经在我们的客服 Agent、RAG 系统、代码审查工具上经过了实战检验。如果你也在构建 AI Agent，不妨试试用它来确保你的 Agent 从"能用"变成"靠谱"。

---

**你觉得 AI Agent 的测试是个被低估的问题吗？欢迎在评论区分享你的看法和实践经验！**

---

*作者：大凯 · 小鸣*
*发布时间：2026-05-20*
