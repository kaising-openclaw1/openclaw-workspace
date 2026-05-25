"""
AgentEvaluator - AI Agent 综合评估引擎

支持对任意 LLM-based Agent 进行多维度评估：
- 任务完成率
- 响应质量
- Token 成本
- 延迟
- 多轮一致性
- 鲁棒性（对抗输入）
"""

from __future__ import annotations

import time
import json
import hashlib
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class EvalTask:
    """单个评估任务"""
    name: str
    input_text: str
    expected_output: Optional[str] = None
    expected_keywords: Optional[List[str]] = None
    max_tokens: int = 2048
    category: str = "general"  # coding, reasoning, creative, qa, etc.


@dataclass
class EvalResult:
    """单次评估结果"""
    task_name: str
    category: str
    success: bool
    score: float  # 0-100
    latency_ms: float
    tokens_used: int
    cost_usd: float
    output: str
    error: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)


class AgentEvaluator:
    """
    AI Agent 评估器

    Usage:
        evaluator = AgentEvaluator(
            agent_fn=my_agent_call,
            cost_per_token={"input": 0.001, "output": 0.002},
        )
        results = evaluator.run(tasks)
        report = evaluator.generate_report(results)
    """

    def __init__(
        self,
        agent_fn: Callable[[str, Dict], str],
        cost_per_token: Optional[Dict[str, float]] = None,
        timeout_seconds: float = 60.0,
    ):
        self.agent_fn = agent_fn
        self.cost_per_token = cost_per_token or {"input": 0.001, "output": 0.002}
        self.timeout_seconds = timeout_seconds
        self.results: List[EvalResult] = []

    def run_task(self, task: EvalTask) -> EvalResult:
        """运行单个评估任务"""
        start_time = time.time()
        error = None
        output = ""
        tokens_used = 0

        try:
            output = self.agent_fn(
                task.input_text,
                {"max_tokens": task.max_tokens, "category": task.category},
            )
            tokens_used = self._estimate_tokens(task.input_text) + self._estimate_tokens(output)
        except Exception as e:
            error = str(e)

        latency_ms = (time.time() - start_time) * 1000
        cost_usd = self._calculate_cost(tokens_used)

        # 评分
        score = self._score_output(task, output, error)
        success = score >= 50 and error is None

        result = EvalResult(
            task_name=task.name,
            category=task.category,
            success=success,
            score=score,
            latency_ms=round(latency_ms, 2),
            tokens_used=tokens_used,
            cost_usd=round(cost_usd, 6),
            output=output,
            error=error,
        )

        self.results.append(result)
        return result

    def run_batch(
        self,
        tasks: List[EvalTask],
        progress_callback: Optional[Callable[[int, int, EvalResult], None]] = None,
    ) -> List[EvalResult]:
        """批量运行评估任务"""
        results = []
        for i, task in enumerate(tasks):
            result = self.run_task(task)
            results.append(result)
            if progress_callback:
                progress_callback(i + 1, len(tasks), result)
        return results

    def run_stress_test(
        self,
        task: EvalTask,
        iterations: int = 10,
    ) -> Dict[str, Any]:
        """
        压力测试：同一任务多次运行，测量一致性

        Returns:
            包含均值、标准差、P99 延迟等统计信息
        """
        latencies = []
        scores = []
        costs = []
        outputs = []

        for _ in range(iterations):
            result = self.run_task(task)
            latencies.append(result.latency_ms)
            scores.append(result.score)
            costs.append(result.cost_usd)
            outputs.append(result.output)

        # 计算一致性（输出相似度）
        consistency = self._output_consistency(outputs)

        latencies.sort()
        return {
            "task_name": task.name,
            "iterations": iterations,
            "latency_mean_ms": round(sum(latencies) / len(latencies), 2),
            "latency_p50_ms": round(latencies[len(latencies) // 2], 2),
            "latency_p99_ms": round(latencies[int(len(latencies) * 0.99)], 2),
            "latency_std_ms": round(self._std(latencies), 2),
            "score_mean": round(sum(scores) / len(scores), 2),
            "score_std": round(self._std(scores), 2),
            "cost_mean_usd": round(sum(costs) / len(costs), 6),
            "cost_total_usd": round(sum(costs), 6),
            "consistency": round(consistency, 4),
            "success_rate": round(sum(1 for s in scores if s >= 50) / iterations, 4),
        }

    def run_robustness_test(
        self,
        base_task: EvalTask,
        perturbation_fn: Callable[[str], str],
        num_perturbations: int = 5,
    ) -> Dict[str, Any]:
        """
        鲁棒性测试：对输入施加扰动，评估 Agent 稳定性

        Args:
            base_task: 基础任务
            perturbation_fn: 输入扰动函数
            num_perturbations: 扰动次数
        """
        baseline = self.run_task(base_task)
        perturbed_results = []

        for i in range(num_perturbations):
            perturbed_input = perturbation_fn(base_task.input_text)
            perturbed_task = EvalTask(
                name=f"{base_task.name}_perturbed_{i}",
                input_text=perturbed_input,
                expected_output=base_task.expected_output,
                expected_keywords=base_task.expected_keywords,
                category=base_task.category,
            )
            result = self.run_task(perturbed_task)
            perturbed_results.append(result)

        score_variance = self._std([r.score for r in perturbed_results])
        avg_score = sum(r.score for r in perturbed_results) / len(perturbed_results)

        return {
            "baseline_score": baseline.score,
            "perturbed_avg_score": round(avg_score, 2),
            "score_variance": round(score_variance, 2),
            "robustness_score": round(max(0, 100 - score_variance * 2), 2),
            "results": [
                {
                    "name": r.task_name,
                    "score": r.score,
                    "success": r.success,
                }
                for r in perturbed_results
            ],
        }

    def generate_report(self, results: Optional[List[EvalResult]] = None) -> Dict[str, Any]:
        """生成评估报告"""
        results = results or self.results
        if not results:
            return {"error": "No results available"}

        by_category: Dict[str, List[EvalResult]] = {}
        for r in results:
            by_category.setdefault(r.category, []).append(r)

        category_scores = {}
        for cat, cat_results in by_category.items():
            scores = [r.score for r in cat_results]
            success_count = sum(1 for r in cat_results if r.success)
            category_scores[cat] = {
                "avg_score": round(sum(scores) / len(scores), 2),
                "success_rate": round(success_count / len(cat_results), 4),
                "total_tasks": len(cat_results),
                "avg_latency_ms": round(sum(r.latency_ms for r in cat_results) / len(cat_results), 2),
                "total_cost_usd": round(sum(r.cost_usd for r in cat_results), 6),
            }

        all_scores = [r.score for r in results]
        all_latencies = [r.latency_ms for r in results]
        total_cost = sum(r.cost_usd for r in results)

        return {
            "total_tasks": len(results),
            "success_count": sum(1 for r in results if r.success),
            "success_rate": round(sum(1 for r in results if r.success) / len(results), 4),
            "avg_score": round(sum(all_scores) / len(all_scores), 2),
            "avg_latency_ms": round(sum(all_latencies) / len(all_latencies), 2),
            "total_cost_usd": round(total_cost, 6),
            "by_category": category_scores,
            "weakest_category": min(category_scores, key=lambda c: category_scores[c]["avg_score"]),
            "strongest_category": max(category_scores, key=lambda c: category_scores[c]["avg_score"]),
            "score_distribution": {
                "excellent_90_100": sum(1 for s in all_scores if s >= 90),
                "good_70_89": sum(1 for s in all_scores if 70 <= s < 90),
                "fair_50_69": sum(1 for s in all_scores if 50 <= s < 70),
                "poor_below_50": sum(1 for s in all_scores if s < 50),
            },
        }

    def export_report(self, results: Optional[List[EvalResult]] = None, fmt: str = "json") -> str:
        """导出评估报告"""
        report = self.generate_report(results)
        if fmt == "json":
            return json.dumps(report, indent=2, ensure_ascii=False)
        elif fmt == "markdown":
            return self._to_markdown(report)
        else:
            return json.dumps(report, indent=2, ensure_ascii=False)

    def _to_markdown(self, report: Dict[str, Any]) -> str:
        """将报告转为 Markdown 格式"""
        lines = [
            "# AI Agent 评估报告\n",
            f"- **总任务数：** {report['total_tasks']}",
            f"- **成功率：** {report['success_rate'] * 100:.1f}%",
            f"- **平均得分：** {report['avg_score']}/100",
            f"- **平均延迟：** {report['avg_latency_ms']:.0f}ms",
            f"- **总成本：** ${report['total_cost_usd']:.6f}\n",
            "## 分类表现\n",
            "| 分类 | 平均分 | 成功率 | 任务数 | 平均延迟 | 总成本 |",
            "|------|--------|--------|--------|----------|--------|",
        ]

        for cat, stats in report["by_category"].items():
            lines.append(
                f"| {cat} | {stats['avg_score']} | {stats['success_rate'] * 100:.1f}% "
                f"| {stats['total_tasks']} | {stats['avg_latency_ms']:.0f}ms "
                f"| ${stats['total_cost_usd']:.6f} |"
            )

        lines.extend([
            "\n## 得分分布\n",
            f"- 优秀 (90-100): {report['score_distribution']['excellent_90_100']}",
            f"- 良好 (70-89): {report['score_distribution']['good_70_89']}",
            f"- 一般 (50-69): {report['score_distribution']['fair_50_69']}",
            f"- 较差 (<50): {report['score_distribution']['poor_below_50']}",
            f"\n> 最强领域: {report['strongest_category']}",
            f"> 最弱领域: {report['weakest_category']}",
        ])

        return "\n".join(lines)

    # ---- 私有方法 ----

    def _estimate_tokens(self, text: str) -> int:
        """粗略估计 token 数量（中英文混合场景）"""
        # 中文约 1.5 字符/token，英文约 4 字符/token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return max(1, chinese_chars // 2 + other_chars // 4)

    def _calculate_cost(self, tokens: int) -> float:
        """计算成本"""
        # 假设 input:output ≈ 1:1
        input_cost = (tokens // 2) * self.cost_per_token.get("input", 0.001) / 1000
        output_cost = (tokens // 2) * self.cost_per_token.get("output", 0.002) / 1000
        return input_cost + output_cost

    def _score_output(
        self,
        task: EvalTask,
        output: str,
        error: Optional[str],
    ) -> float:
        """对输出进行评分"""
        if error:
            return 0.0
        if not output or not output.strip():
            return 10.0

        score = 50.0  # 基础分

        # 关键词匹配
        if task.expected_keywords:
            matched = sum(1 for kw in task.expected_keywords if kw.lower() in output.lower())
            keyword_ratio = matched / len(task.expected_keywords)
            score += keyword_ratio * 30

        # 输出长度合理性
        output_len = len(output)
        if 100 <= output_len <= 5000:
            score += 10
        elif output_len > 5000:
            score += 5  # 太长扣分

        # 期望输出匹配
        if task.expected_output:
            import difflib
            similarity = difflib.SequenceMatcher(None, output.lower(), task.expected_output.lower()).ratio()
            score += similarity * 10

        return min(100.0, max(0.0, score))

    def _output_consistency(self, outputs: List[str]) -> float:
        """计算多个输出之间的一致性"""
        if len(outputs) < 2:
            return 1.0

        # 使用哈希相似度粗略估算
        hashes = [hashlib.md5(o.encode()).hexdigest()[:8] for o in outputs]
        unique = len(set(hashes))
        return 1.0 - (unique - 1) / max(len(outputs) - 1, 1)

    @staticmethod
    def _std(values: List[float]) -> float:
        """计算标准差"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return variance ** 0.5
