"""LLM-as-a-Judge 评估器 + 测试运行器"""

from dataclasses import dataclass, field
import json
import time


def call_llm(messages: list[dict], model: str = "gpt-4") -> str:
    """
    LLM 调用接口。实际使用时替换为 OpenAI / Claude / DeepSeek API。
    """
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
    
    def __init__(self, evaluator: LLMEvaluator, agent_fn):
        self.evaluator = evaluator
        self.agent_fn = agent_fn
        self.results: list[EvaluationResult] = []
    
    def run_suite(self, dataset) -> list[EvaluationResult]:
        """运行完整测试套件"""
        results = []
        total = dataset.total
        print(f"\n开始测试：{total} 个用例\n")
        
        for i, (cid, case) in enumerate(dataset.cases.items(), 1):
            print(f"[{i}/{total}] 运行 {cid}...", end=" ")
            
            start = time.time()
            agent_output = self.agent_fn(case.input, case.tools_available)
            latency = (time.time() - start) * 1000
            
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
