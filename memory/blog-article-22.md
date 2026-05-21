# 手把手教你用 Python 构建 AI Agent 测试框架：让你的 AI 应用从"能用"到"靠谱"

> **作者：** Kai Studio  
> **发布日期：** 2026-05-11  
> **预估阅读时间：** 20 分钟  
> **技术栈：** Python 3.9+、pytest、LLM-as-a-Judge、Golden Dataset、回归测试  

---

## 引言：你的 AI Agent 到底可不可靠？

2026 年 3 月，Gartner 发布了一份 AI Agent 部署调研报告。数据显示：

- **87%** 的企业已经部署或正在评估 AI Agent
- **只有 14.4%** 的 AI Agent 通过了安全审批流程
- **平均每个 Agent 有 2.3 个未被发现的严重缺陷**

问题不在于 AI 不够聪明，而在于我们缺乏系统性的测试方法。传统的单元测试对确定性代码有效，但面对 LLM 的**概率性输出**和 Agent 的**多步推理**，老方法不管用了。

今天，我们从零构建一个完整的 **AI Agent 测试框架**，包含：

1. **Golden Dataset** —— 构建测试用例集
2. **LLM-as-a-Judge** —— 用更强模型评估弱模型输出
3. **回归测试** —— 确保模型升级不引入回退
4. **工具调用测试** —— 验证 Agent 是否正确调用外部工具
5. **压力测试** —— 模拟复杂对话场景下的行为一致性
6. **可视化报告** —— 生成可交付的质量报告

这套框架可以直接用于你的企业知识库、客服 Agent、MCP 工具系统——任何基于 LLM 的应用。

---

## 一、为什么传统测试对 AI 不够用？

### 1.1 确定性 vs 概率性

传统代码：

```python
def add(a, b):
    return a + b

assert add(2, 3) == 5  # 永远成立
```

AI 输出：

```python
response = llm.generate("2+3等于多少？")
# 第一次："5"
# 第二次："等于 5"
# 第三次："结果是 5，我来解释一下..."
```

同一输入，不同输出。`assert response == "5"` 会随机失败。

### 1.2 单步 vs 多步

传统测试关注输入→输出的映射。但 AI Agent 是**多步决策链**：

```
用户提问 → 理解意图 → 选择工具 → 调用工具 → 分析结果 → 组织回答
```

任何一步出错，最终结果就不对。但你可能只看到"回答质量差"，不知道哪一步出了问题。

### 1.3 这就是我们需要的

我们需要一套 **AI 原生测试框架**，能够：

- ✅ 评估输出的**语义质量**而非字面匹配
- ✅ 追踪 Agent 的**内部决策过程**
- ✅ 检测**回归问题**（新版本比旧版本差）
- ✅ 生成**可解释的测试报告**

---

## 二、核心架构设计

```
┌─────────────────────────────────────────────────┐
│              AI Agent Test Framework              │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Golden   │  │ LLM-as-  │  │ Tool Call    │   │
│  │ Dataset  │→ │ a-Judge  │→ │ Validator    │   │
│  │ Manager  │  │ Evaluator│  │              │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
│       ↓              ↓              ↓            │
│  ┌──────────────────────────────────────────┐   │
│  │          Regression Tracker              │   │
│  └──────────────────────────────────────────┘   │
│       ↓                                         │
│  ┌──────────────────────────────────────────┐   │
│  │          Report Generator                │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

## 三、实现 Golden Dataset 管理器

Golden Dataset 是测试的基础——一组精心设计的"输入→期望输出"对。

### 3.1 数据结构

```python
"""agent_test_framework/golden_dataset.py"""
from dataclasses import dataclass, field
from typing import Optional, Callable
import json
from pathlib import Path


@dataclass
class TestCase:
    """单个测试用例"""
    id: str
    input: str                    # 输入内容
    expected_output: str          # 期望输出（语义描述）
    category: str                 # 分类：问答/工具调用/推理/对话
    difficulty: str = "medium"    # 难度：easy/medium/hard
    tools_available: list = field(default_factory=list)  # 可用工具
    metadata: dict = field(default_factory=dict)
    evaluation_criteria: list = field(default_factory=list)  # 评分标准


class GoldenDataset:
    """Golden Dataset 管理器"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.cases: dict[str, TestCase] = {}
    
    def add_case(self, case: TestCase) -> None:
        self.cases[case.id] = case
    
    def add_cases(self, cases: list[TestCase]) -> None:
        for case in cases:
            self.add_case(case)
    
    def get_by_category(self, category: str) -> list[TestCase]:
        return [c for c in self.cases.values() if c.category == category]
    
    def get_by_difficulty(self, difficulty: str) -> list[TestCase]:
        return [c for c in self.cases.values() if c.difficulty == difficulty]
    
    @property
    def total(self) -> int:
        return len(self.cases)
    
    def save(self, path: str) -> None:
        data = {
            "name": self.name,
            "cases": {
                cid: {
                    "input": c.input,
                    "expected_output": c.expected_output,
                    "category": c.category,
                    "difficulty": c.difficulty,
                    "tools_available": c.tools_available,
                    "metadata": c.metadata,
                    "evaluation_criteria": c.evaluation_criteria,
                }
                for cid, c in self.cases.items()
            }
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
            ds.add_case(TestCase(
                id=cid,
                input=cdata["input"],
                expected_output=cdata["expected_output"],
                category=cdata["category"],
                difficulty=cdata.get("difficulty", "medium"),
                tools_available=cdata.get("tools_available", []),
                metadata=cdata.get("metadata", {}),
                evaluation_criteria=cdata.get("evaluation_criteria", []),
            ))
        print(f"Golden Dataset 已加载：{ds.total} 个用例")
        return ds
```

### 3.2 构建测试用例集

```python
"""examples/build_golden_dataset.py"""
from agent_test_framework.golden_dataset import GoldenDataset, TestCase


def build_customer_service_dataset() -> GoldenDataset:
    """构建客服场景的测试用例集"""
    
    ds = GoldenDataset(name="customer_service_v1")
    
    # === 基础问答 ===
    ds.add_cases([
        TestCase(
            id="cs_001",
            input="我的订单什么时候发货？",
            expected_output="客服应询问订单号或登录账号，以便查询订单状态和发货时间",
            category="问答",
            difficulty="easy",
            evaluation_criteria=["引导用户提供订单信息", "语气友好专业", "不编造发货时间"],
        ),
        TestCase(
            id="cs_002",
            input="我要退货，商品有质量问题",
            expected_output="客服应引导用户通过售后流程申请退货，说明需要准备的材料（订单号、照片等），并承诺处理时效",
            category="问答",
            difficulty="medium",
            evaluation_criteria=[
                "提供明确的退货流程",
                "说明所需材料",
                "给出处理时效",
                "表达歉意和理解"
            ],
        ),
    ])
    
    # === 工具调用 ===
    ds.add_cases([
        TestCase(
            id="cs_010",
            input="帮我查一下订单 ORD-2026-0511003 的物流信息",
            expected_output="Agent 应调用 order_query 工具查询订单详情，然后调用 tracking 工具获取物流信息，最后整合成用户友好的回复",
            category="工具调用",
            difficulty="medium",
            tools_available=["order_query", "tracking", "customer_profile"],
            evaluation_criteria=[
                "调用 order_query 工具",
                "使用正确的订单号",
                "调用 tracking 工具",
                "整合信息后回复用户",
                "不调用不相关的工具",
            ],
        ),
        TestCase(
            id="cs_011",
            input="我要修改收货地址，新地址是：北京市朝阳区XX路123号",
            expected_output="Agent 应先调用 customer_profile 验证用户身份，然后调用 order_update 修改地址，最后确认修改结果",
            category="工具调用",
            difficulty="hard",
            tools_available=["customer_profile", "order_update", "notification"],
            evaluation_criteria=[
                "先验证用户身份",
                "调用 order_update 修改地址",
                "使用用户提供的新地址",
                "确认修改成功",
                "不调用 notification 发送垃圾消息",
            ],
        ),
    ])
    
    # === 推理场景 ===
    ds.add_cases([
        TestCase(
            id="cs_020",
            input="我买了三件衣服，两件合适，一件尺寸不对。我想换大一号的，但同款没库存了。怎么办？",
            expected_output="客服应先确认订单信息和商品库存，然后给出替代方案（换款/退款/补货通知），让用户选择",
            category="推理",
            difficulty="hard",
            tools_available=["order_query", "inventory_check", "return_exchange", "restock_notify"],
            evaluation_criteria=[
                "查询订单确认商品信息",
                "检查同款是否有其他库存",
                "提供换款建议",
                "提供退款选项",
                "提供补货通知选项",
                "让用户做选择而非强制决定",
            ],
        ),
    ])
    
    # === 对话一致性 ===
    ds.add_cases([
        TestCase(
            id="cs_030",
            input="昨天我问的那个问题，你们处理了吗？",
            expected_output="Agent 应识别到上下文缺失，请求用户提供更多信息，而不是假装知道用户说什么",
            category="对话",
            difficulty="medium",
            evaluation_criteria=[
                "承认无法获取历史对话",
                "礼貌请求用户提供更多上下文",
                "不编造虚假的回复记录",
            ],
        ),
    ])
    
    return ds


if __name__ == "__main__":
    ds = build_customer_service_dataset()
    ds.save("data/golden_dataset.json")
```

---

## 四、实现 LLM-as-a-Judge 评估器

### 4.1 核心评估逻辑

```python
"""agent_test_framework/evaluator.py"""
from dataclasses import dataclass, field
from typing import Optional
import json
import time

# 模拟 LLM 调用（实际使用时替换为你的 LLM API）
def call_llm(messages: list[dict], model: str = "gpt-4") -> str:
    """
    调用 LLM 进行评估。
    实际使用时替换为 OpenAI / Claude / DeepSeek 等 API 调用。
    """
    # 这里用占位实现，实际项目接入真实 API
    return '{"score": 8, "reasoning": "输出符合预期"}'


@dataclass
class EvaluationResult:
    """单次评估结果"""
    case_id: str
    score: float                    # 0-10 分
    passed: bool                    # 是否通过
    reasoning: str                  # 评估理由
    rubric_scores: dict = field(default_factory=dict)  # 各维度分数
    latency_ms: float = 0
    tokens_used: int = 0


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
        self,
        case_input: str,
        case_expected: str,
        agent_output: str,
        criteria: list[str],
    ) -> list[dict]:
        """构建评估 Prompt"""
        criteria_text = "\n".join(f"- {c}" for c in criteria) if criteria else "无特定标准"
        
        system_prompt = f"""你是一个专业的 AI Agent 评估专家。请根据以下标准评估 Agent 的输出质量。

评分标准（{self.scoring_rubric}）：
- 9-10 分：完全符合预期，质量优秀
- 7-8 分：基本符合预期，有轻微不足
- 5-6 分：部分符合预期，有明显改进空间
- 3-4 分：偏离预期，质量较差
- 1-2 分：完全不符合预期，不可接受

请以 JSON 格式返回评估结果：
{{"score": 分数, "reasoning": "详细评估理由", "rubric_scores": {{"准确性": 分数, "完整性": 分数, "安全性": 分数}}}}"""

        user_prompt = f"""## 用户输入
{case_input}

## 期望输出
{case_expected}

## Agent 实际输出
{agent_output}

## 评估标准
{criteria_text}

请评估并返回 JSON。"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    
    def evaluate(
        self,
        case_id: str,
        case_input: str,
        case_expected: str,
        agent_output: str,
        criteria: list[str] = None,
    ) -> EvaluationResult:
        """评估单个用例"""
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
                case_id=case_id,
                score=score,
                passed=score >= self.pass_threshold,
                reasoning=result.get("reasoning", ""),
                rubric_scores=result.get("rubric_scores", {}),
                latency_ms=latency_ms,
            )
        except json.JSONDecodeError:
            return EvaluationResult(
                case_id=case_id,
                score=0,
                passed=False,
                reasoning=f"评估器返回了无效 JSON: {response[:200]}",
                latency_ms=latency_ms,
            )


class TestRunner:
    """测试运行器"""
    
    def __init__(self, evaluator: LLMEvaluator, agent_fn: callable):
        self.evaluator = evaluator
        self.agent_fn = agent_fn  # 调用 Agent 的函数
        self.results: list[EvaluationResult] = []
    
    def run_suite(self, dataset: "GoldenDataset") -> list[EvaluationResult]:
        """运行完整测试套件"""
        results = []
        total = dataset.total
        print(f"\n开始测试：{total} 个用例\n")
        
        for i, (cid, case) in enumerate(dataset.cases.items(), 1):
            print(f"[{i}/{total}] 运行 {cid}...", end=" ")
            
            # 调用 Agent
            start = time.time()
            agent_output = self.agent_fn(case.input, case.tools_available)
            latency = (time.time() - start) * 1000
            
            # 评估输出
            result = self.evaluator.evaluate(
                case_id=cid,
                case_input=case.input,
                case_expected=case.expected_output,
                agent_output=agent_output,
                criteria=case.evaluation_criteria,
            )
            result.latency_ms = latency
            
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} ({result.score:.1f}/10, {latency:.0f}ms)")
            
            results.append(result)
        
        self.results = results
        return results
    
    def summary(self) -> dict:
        """生成测试摘要"""
        if not self.results:
            return {"error": "无测试结果"}
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        avg_score = sum(r.score for r in self.results) / total
        avg_latency = sum(r.latency_ms for r in self.results) / total
        
        # 按类别统计
        category_stats = {}
        for r in self.results:
            cat = r.case_id.split("_")[0] if "_" in r.case_id else "unknown"
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "passed": 0, "scores": []}
            category_stats[cat]["total"] += 1
            if r.passed:
                category_stats[cat]["passed"] += 1
            category_stats[cat]["scores"].append(r.score)
        
        for cat in category_stats:
            scores = category_stats[cat]["scores"]
            category_stats[cat]["avg_score"] = sum(scores) / len(scores)
            category_stats[cat]["pass_rate"] = category_stats[cat]["passed"] / category_stats[cat]["total"]
            del category_stats[cat]["scores"]
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed/total*100:.1f}%",
            "avg_score": f"{avg_score:.1f}/10",
            "avg_latency_ms": f"{avg_latency:.0f}ms",
            "category_stats": category_stats,
        }
```

---

## 五、实现回归测试追踪器

回归测试确保模型升级或 Agent 改版不会引入回退。

```python
"""agent_test_framework/regression.py"""
from dataclasses import dataclass
import json
from pathlib import Path
from datetime import datetime


@dataclass
class TestRun:
    """一次测试运行的快照"""
    timestamp: str
    agent_version: str
    model_name: str
    results: list[dict]  # EvaluationResult 序列化
    summary: dict


class RegressionTracker:
    """回归测试追踪器"""
    
    def __init__(self, history_path: str = "data/test_history"):
        self.history_path = Path(history_path)
        self.history_path.mkdir(parents=True, exist_ok=True)
        self.runs: list[TestRun] = self._load_history()
    
    def _load_history(self) -> list[TestRun]:
        runs = []
        for f in sorted(self.history_path.glob("run_*.json")):
            with open(f) as fh:
                data = json.load(fh)
                runs.append(TestRun(**data))
        return runs
    
    def save_run(self, run: TestRun) -> None:
        filename = f"run_{run.timestamp.replace(':', '-').replace(' ', '_')}.json"
        filepath = self.history_path / filename
        with open(filepath, "w") as f:
            json.dump({
                "timestamp": run.timestamp,
                "agent_version": run.agent_version,
                "model_name": run.model_name,
                "results": run.results,
                "summary": run.summary,
            }, f, ensure_ascii=False, indent=2)
        self.runs.append(run)
    
    def compare_runs(self, baseline_id: int, current_id: int) -> dict:
        """比较两次测试运行"""
        baseline = self.runs[baseline_id]
        current = self.runs[current_id]
        
        baseline_pass_rate = baseline.summary.get("pass_rate", "0%")
        current_pass_rate = current.summary.get("pass_rate", "0%")
        baseline_score = baseline.summary.get("avg_score", "0/10")
        current_score = current.summary.get("avg_score", "0/10")
        
        # 逐用例对比
        regression_cases = []
        for b_res in baseline.results:
            c_res = next(
                (r for r in current.results if r["case_id"] == b_res["case_id"]),
                None
            )
            if c_res:
                if b_res["score"] > c_res["score"] + 1:  # 分数下降超过 1 分
                    regression_cases.append({
                        "case_id": b_res["case_id"],
                        "before": b_res["score"],
                        "after": c_res["score"],
                        "delta": c_res["score"] - b_res["score"],
                    })
        
        return {
            "baseline": {
                "version": baseline.agent_version,
                "model": baseline.model_name,
                "pass_rate": baseline_pass_rate,
                "avg_score": baseline_score,
            },
            "current": {
                "version": current.agent_version,
                "model": current.model_name,
                "pass_rate": current_pass_rate,
                "avg_score": current_score,
            },
            "regressions": regression_cases,
            "regression_count": len(regression_cases),
        }
```

---

## 六、生成可视化质量报告

```python
"""agent_test_framework/report.py"""
from pathlib import Path


def generate_html_report(summary: dict, results: list, output_path: str = "report.html") -> None:
    """生成 HTML 质量报告"""
    
    # 构建结果表格
    rows = ""
    for r in results:
        status = "✅" if r.get("passed") else "❌"
        score_color = "#22c55e" if r.get("score", 0) >= 7 else "#ef4444"
        rows += f"""
        <tr>
            <td>{r['case_id']}</td>
            <td><span style="color:{score_color};font-weight:bold">{r.get('score', 0):.1f}</span></td>
            <td>{status}</td>
            <td style="color:#888;font-size:0.85rem">{r.get('reasoning', '')[:100]}</td>
        </tr>"""
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>AI Agent 质量报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
               max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }}
        h1 {{ border-bottom: 2px solid #d4a574; padding-bottom: 0.5rem; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 2rem 0; }}
        .stat {{ text-align: center; padding: 1.5rem; background: #f5f5f5; border-radius: 12px; }}
        .stat .num {{ font-size: 2rem; font-weight: 800; color: #d4a574; }}
        .stat .label {{ font-size: 0.85rem; color: #666; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #fafafa; font-weight: 600; }}
        .footer {{ margin-top: 3rem; color: #888; font-size: 0.85rem; text-align: center; }}
    </style>
</head>
<body>
    <h1>📊 AI Agent 质量报告</h1>
    <p>生成时间：{summary.get('timestamp', 'N/A')}</p>
    
    <div class="summary">
        <div class="stat">
            <div class="num">{summary.get('total', 0)}</div>
            <div class="label">总用例数</div>
        </div>
        <div class="stat">
            <div class="num" style="color:#22c55e">{summary.get('passed', 0)}</div>
            <div class="label">通过</div>
        </div>
        <div class="stat">
            <div class="num" style="color:#ef4444">{summary.get('failed', 0)}</div>
            <div class="label">失败</div>
        </div>
        <div class="stat">
            <div class="num">{summary.get('pass_rate', 'N/A')}</div>
            <div class="label">通过率</div>
        </div>
    </div>

    <table>
        <thead>
            <tr><th>用例 ID</th><th>评分</th><th>状态</th><th>评估理由</th></tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    
    <div class="footer">
        Generated by Kai Studio AI Agent Test Framework
    </div>
</body>
</html>"""
    
    Path(output_path).write_text(html, encoding="utf-8")
    print(f"质量报告已生成：{output_path}")
```

---

## 七、完整运行示例

```python
"""examples/run_full_test.py"""
from agent_test_framework.golden_dataset import GoldenDataset
from agent_test_framework.evaluator import LLMEvaluator, TestRunner
from agent_test_framework.regression import RegressionTracker, TestRun
from agent_test_framework.report import generate_html_report
from datetime import datetime


def mock_agent(input_text: str, tools: list) -> str:
    """模拟 Agent 输出（实际使用时替换为真实 Agent）"""
    responses = {
        "cs_001": "请问您的订单号是什么？我帮您查一下发货状态。",
        "cs_002": "非常抱歉给您带来不便。请您提供订单号，并拍一下商品质量问题的照片。我们会在 24 小时内处理退货申请。",
        "cs_010": "好的，让我查一下订单 ORD-2026-0511003 的物流信息...",
        "cs_011": "收到您的新地址。为了安全起见，请先登录账号验证身份，然后我来帮您修改收货地址。",
        "cs_020": "我查了一下，同款确实没有大一号库存了。我建议您：1）换同款其他颜色；2）退款重新选；3）登记补货通知。您看哪个方便？",
        "cs_030": "抱歉，我无法获取昨天的对话记录。能简单说一下您之前咨询的问题吗？我来帮您跟进。",
    }
    
    # 从输入中提取 case_id
    for case_id, response in responses.items():
        if case_id in str(tools) or True:  # 简化模拟
            return responses.get(case_id, "我来帮您处理这个问题。")
    return "我来帮您处理这个问题。"


def main():
    # 1. 加载 Golden Dataset
    ds = GoldenDataset.load("data/golden_dataset.json")
    print(f"加载了 {ds.total} 个测试用例\n")
    
    # 2. 创建评估器和测试运行器
    evaluator = LLMEvaluator(
        judge_model="gpt-4",
        pass_threshold=7.0,
    )
    runner = TestRunner(evaluator=evaluator, agent_fn=mock_agent)
    
    # 3. 运行测试套件
    results = runner.run_suite(ds)
    
    # 4. 生成摘要
    summary = runner.summary()
    summary["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    print(f"\n{'='*50}")
    print(f"测试完成！")
    print(f"通过率：{summary['pass_rate']}")
    print(f"平均分：{summary['avg_score']}")
    print(f"平均延迟：{summary['avg_latency_ms']}")
    
    # 5. 生成报告
    generate_html_report(summary, [vars(r) for r in results])
    
    # 6. 保存回归测试快照
    tracker = RegressionTracker()
    run = TestRun(
        timestamp=summary["timestamp"],
        agent_version="v1.0.0",
        model_name="gpt-4",
        results=[vars(r) for r in results],
        summary=summary,
    )
    tracker.save_run(run)
    print("回归测试快照已保存")


if __name__ == "__main__":
    main()
```

---

## 八、实际应用：测试你的 AI 客服 Agent

假设你已经有一个客服 Agent（比如前面文章里构建的 CS-Agent），现在用它来运行真实测试：

```python
from your_cs_agent.main import CSAgent  # 你的真实 Agent

agent = CSAgent(model="deepseek-chat")

def real_agent_fn(input_text: str, tools: list) -> str:
    response = agent.chat(input_text, tools=tools)
    return response.content

runner = TestRunner(
    evaluator=LLMEvaluator(judge_model="gpt-4", pass_threshold=7.0),
    agent_fn=real_agent_fn,
)

results = runner.run_suite(ds)
```

测试结果会告诉你：
- 哪些场景下 Agent 表现良好 ✅
- 哪些场景需要优化 Prompt 或工具定义 ❌
- 模型升级后是否引入了回退 📉

---

## 九、进阶技巧

### 9.1 自动化 Golden Dataset 生成

用强模型自动生成测试用例：

```python
def generate_golden_cases(topic: str, count: int = 20) -> list[TestCase]:
    """用 GPT-4 自动生成测试用例"""
    prompt = f"""为 {topic} 场景生成 {count} 个测试用例。
每个用例包含：用户输入、期望输出描述、难度等级、评估标准。
以 JSON 数组格式返回。"""
    # 调用 LLM 生成 → 解析 → 返回 TestCase 列表
    pass
```

### 9.2 多模型对比测试

```python
models = ["gpt-4", "claude-3-opus", "deepseek-chat", "qwen-max"]
for model in models:
    agent = CSAgent(model=model)
    runner = TestRunner(evaluator, agent_fn=make_agent_fn(agent))
    results = runner.run_suite(ds)
    print(f"{model}: {runner.summary()['pass_rate']}")
```

### 9.3 CI/CD 集成

```yaml
# .github/workflows/agent-test.yml
name: Agent Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pytest
      - run: python examples/run_full_test.py
      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: quality-report
          path: report.html
```

---

## 总结

AI Agent 测试不是可选项，而是**必选项**。没有系统性测试的 AI Agent 就像没有质检的生产线——你不知道什么时候会出问题。

这套框架的核心价值：

1. **Golden Dataset** —— 用结构化用例替代模糊的"感觉不错"
2. **LLM-as-a-Judge** —— 用语义评估替代字面匹配
3. **回归追踪** —— 确保每次变更都有据可查
4. **可视化报告** —— 让质量数据驱动决策

> 完整代码已开源：**GitHub → [kaising-openclaw1/agent-test-framework](https://github.com/kaising-openclaw1/agent-test-framework)**

---

*觉得有用？⭐ 给个 star，或者关注 Kai Studio，后续还有更多 AI 工程化实战内容。*
