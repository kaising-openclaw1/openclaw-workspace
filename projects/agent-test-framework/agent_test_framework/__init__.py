"""AI Agent 测试框架 — 让 AI 应用从"能用"到"靠谱" """

__version__ = "1.0.0"

from .golden_dataset import GoldenDataset, TestCase
from .evaluator import LLMEvaluator, TestRunner, EvaluationResult
from .regression import RegressionTracker, TestRun
from .report import generate_html_report

__all__ = [
    "GoldenDataset",
    "TestCase",
    "LLMEvaluator",
    "TestRunner",
    "EvaluationResult",
    "RegressionTracker",
    "TestRun",
    "generate_html_report",
]
