"""
Agent Evaluation Framework - 评估 AI Agent 性能的综合工具

Features:
- 任务完成率评估
- 响应质量评分
- Token 成本分析
- 延迟测量
- 多轮对话一致性
- 自动化基准测试
"""

from .evaluator import AgentEvaluator
from .metrics import AccuracyMetric, LatencyMetric, CostMetric, ConsistencyMetric
from .reporter import EvalReporter
from .benchmark import BenchmarkSuite

__version__ = "1.0.0"
__all__ = [
    "AgentEvaluator",
    "AccuracyMetric",
    "LatencyMetric",
    "CostMetric",
    "ConsistencyMetric",
    "EvalReporter",
    "BenchmarkSuite",
]
