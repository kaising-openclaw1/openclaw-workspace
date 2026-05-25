"""
Metrics - 专用评估指标

提供多种预定义指标，可组合使用：
- AccuracyMetric: 任务完成准确度
- LatencyMetric: 响应延迟分析
- CostMetric: Token 成本分析
- ConsistencyMetric: 多轮对话一致性
"""

from __future__ import annotations

import re
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class MetricResult:
    name: str
    value: float
    unit: str
    grade: str  # A, B, C, D, F
    details: Dict[str, Any]


class AccuracyMetric:
    """
    任务完成准确度评估

    支持多种评估模式：
    - exact_match: 完全匹配
    - keyword_match: 关键词匹配
    - semantic_sim: 语义相似度（简化版）
    - code_execution: 代码可执行性
    """

    def __init__(self, mode: str = "keyword_match"):
        self.mode = mode

    def evaluate(self, output: str, reference: Optional[str] = None,
                 keywords: Optional[List[str]] = None,
                 code: bool = False) -> MetricResult:
        if self.mode == "exact_match":
            return self._exact_match(output, reference or "")
        elif self.mode == "keyword_match":
            return self._keyword_match(output, keywords or [])
        elif self.mode == "code_execution":
            return self._code_check(output)
        else:
            return self._keyword_match(output, keywords or [])

    def _exact_match(self, output: str, reference: str) -> MetricResult:
        if not reference:
            return MetricResult("accuracy", 0, "%", "F", {"reason": "no_reference"})
        match = output.strip().lower() == reference.strip().lower()
        return MetricResult(
            "accuracy", 100.0 if match else 0.0, "%",
            "A" if match else "F",
            {"matched": match},
        )

    def _keyword_match(self, output: str, keywords: List[str]) -> MetricResult:
        if not keywords:
            return MetricResult("accuracy", 50.0, "%", "C", {"reason": "no_keywords"})
        matched = [kw for kw in keywords if kw.lower() in output.lower()]
        ratio = len(matched) / len(keywords) * 100
        grade = "A" if ratio >= 90 else "B" if ratio >= 70 else "C" if ratio >= 50 else "D" if ratio >= 30 else "F"
        return MetricResult(
            "accuracy", round(ratio, 1), "%", grade,
            {"matched": matched, "missing": [k for k in keywords if k not in matched]},
        )

    def _code_check(self, output: str) -> MetricResult:
        """检查代码块是否完整"""
        code_blocks = re.findall(r'```(?:python)?\n(.*?)```', output, re.DOTALL)
        if not code_blocks:
            return MetricResult("accuracy", 20.0, "%", "F", {"reason": "no_code_blocks"})
        score = min(100, len(code_blocks) * 30)
        grade = "A" if score >= 90 else "B" if score >= 70 else "C" if score >= 50 else "D"
        return MetricResult(
            "accuracy", float(score), "%", grade,
            {"code_blocks": len(code_blocks), "avg_length": sum(len(b) for b in code_blocks) // len(code_blocks)},
        )


class LatencyMetric:
    """
    延迟分析指标

    分析响应延迟的分布和趋势
    """

    GRADE_THRESHOLDS = {
        "A": 1000,   # < 1s
        "B": 3000,   # < 3s
        "C": 5000,   # < 5s
        "D": 10000,  # < 10s
    }

    def evaluate(self, latencies_ms: List[float]) -> MetricResult:
        if not latencies_ms:
            return MetricResult("latency", 0, "ms", "F", {"reason": "no_data"})

        latencies = sorted(latencies_ms)
        n = len(latencies)
        mean = sum(latencies) / n
        median = latencies[n // 2]
        p95 = latencies[int(n * 0.95)]
        p99 = latencies[int(n * 0.99)]
        jitter = p95 - p5 if n > 1 else 0
        p5 = latencies[max(0, int(n * 0.05))]

        grade = "F"
        for g, threshold in sorted(self.GRADE_THRESHOLDS.items(), key=lambda x: x[1]):
            if median <= threshold:
                grade = g
                break

        return MetricResult(
            "latency", round(mean, 1), "ms", grade,
            {
                "median_ms": round(median, 1),
                "p95_ms": round(p95, 1),
                "p99_ms": round(p99, 1),
                "min_ms": round(latencies[0], 1),
                "max_ms": round(latencies[-1], 1),
                "jitter_ms": round(jitter, 1),
                "samples": n,
            },
        )


class CostMetric:
    """
    Token 成本分析

    评估每次调用的成本并提供优化建议
    """

    def __init__(self, input_price_per_1k: float = 0.001,
                 output_price_per_1k: float = 0.002):
        self.input_price = input_price_per_1k
        self.output_price = output_price_per_1k

    def evaluate(self, token_usages: List[Dict[str, int]]) -> MetricResult:
        if not token_usages:
            return MetricResult("cost", 0, "USD", "F", {"reason": "no_data"})

        total_input = sum(u.get("input", 0) for u in token_usages)
        total_output = sum(u.get("output", 0) for u in token_usages)
        total_cost = (total_input * self.input_price + total_output * self.output_price) / 1000
        avg_cost = total_cost / len(token_usages)

        # 成本等级（基于平均成本）
        grade = "A" if avg_cost < 0.001 else "B" if avg_cost < 0.005 else "C" if avg_cost < 0.02 else "D" if avg_cost < 0.05 else "F"

        # 优化建议
        suggestions = []
        input_output_ratio = total_input / max(total_output, 1)
        if input_output_ratio > 5:
            suggestions.append("输入token过多，考虑减少上下文或使用摘要")
        avg_tokens = (total_input + total_output) / len(token_usages)
        if avg_tokens > 4000:
            suggestions.append("平均token数较高，考虑使用更小的模型或限制输出长度")
        if not suggestions:
            suggestions.append("成本控制在合理范围内")

        return MetricResult(
            "cost", round(avg_cost, 6), "USD", grade,
            {
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_cost_usd": round(total_cost, 6),
                "avg_cost_per_call_usd": round(avg_cost, 6),
                "input_output_ratio": round(input_output_ratio, 2),
                "suggestions": suggestions,
            },
        )


class ConsistencyMetric:
    """
    多轮对话一致性评估

    检测 Agent 在多轮对话中是否保持：
    - 事实一致性
    - 风格一致性
    - 逻辑连贯性
    """

    def evaluate(self, conversation_history: List[Dict[str, str]]) -> MetricResult:
        if len(conversation_history) < 2:
            return MetricResult("consistency", 100.0, "%", "A",
                                {"reason": "insufficient_turns"})

        scores = []
        for i in range(1, len(conversation_history)):
            prev = conversation_history[i - 1]
            curr = conversation_history[i]
            score = self._compare_turns(prev, curr)
            scores.append(score)

        avg = sum(scores) / len(scores)
        grade = "A" if avg >= 90 else "B" if avg >= 75 else "C" if avg >= 60 else "D" if avg >= 40 else "F"

        return MetricResult(
            "consistency", round(avg, 1), "%", grade,
            {
                "turns_analyzed": len(conversation_history),
                "pairwise_scores": [round(s, 1) for s in scores],
                "min_score": round(min(scores), 1),
                "max_score": round(max(scores), 1),
            },
        )

    def _compare_turns(self, prev: Dict[str, str], curr: Dict[str, str]) -> float:
        """比较相邻两轮的一致性"""
        score = 80.0  # 基础分

        # 检查关键词/实体一致性
        prev_entities = self._extract_entities(prev.get("output", ""))
        curr_entities = self._extract_entities(curr.get("output", ""))

        if prev_entities and curr_entities:
            overlap = len(prev_entities & curr_entities)
            union = len(prev_entities | curr_entities)
            entity_score = (overlap / union) * 20 if union > 0 else 10
            score += entity_score

        # 检查矛盾（简单关键词冲突检测）
        contradictions = [
            ("是", "不是"), ("可以", "不可以"), ("支持", "不支持"),
            ("推荐", "不推荐"), ("正确", "错误"),
        ]
        for a, b in contradictions:
            prev_text = prev.get("output", "").lower()
            curr_text = curr.get("output", "").lower()
            if a in prev_text and b in curr_text:
                score -= 30
            elif b in prev_text and a in curr_text:
                score -= 30

        return max(0, min(100, score))

    def _extract_entities(self, text: str) -> set:
        """简单实体提取（关键词抽取）"""
        # 提取数字、英文单词、中文专有名词
        entities = set()
        # 数字
        entities.update(re.findall(r'\d+\.?\d*', text))
        # 英文单词（4+字符）
        entities.update(w.lower() for w in re.findall(r'[A-Za-z]{4,}', text))
        return entities
