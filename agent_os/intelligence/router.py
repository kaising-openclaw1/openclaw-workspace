"""
Agent OS — 智能路由层：智力分级路由
===================================
自动选择最优模型，不浪费任何智力
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar

logger = logging.getLogger("agent-os.intelligence.router")


class IntelligenceLevel(Enum):
    """智力等级"""
    TINY = 0       # 简单分类/提取 (e.g., keyword extraction)
    LIGHT = 1      # 基础问答 (e.g., Qwen2.5-7B)
    MEDIUM = 2     # 一般推理 (e.g., DeepSeek-V3)
    HIGH = 3       # 复杂推理 (e.g., GPT-4o, Claude 3.5 Sonnet)
    MAXIMUM = 4    # 最高智力 (e.g., Claude Opus, o3, DeepSeek-R1)


class TaskComplexity(Enum):
    """任务复杂度"""
    TRIVIAL = auto()     # 0.1s, 简单提取/格式化
    SIMPLE = auto()      # 1s, 基础问答
    MODERATE = auto()    # 10s, 一般分析
    COMPLEX = auto()     # 60s, 多步推理
    VERY_COMPLEX = auto() # 300s+, 深度研究/代码生成


@dataclass
class ModelCapability:
    """模型能力描述"""
    name: str
    provider: str
    intelligence_level: IntelligenceLevel
    context_window: int
    max_output_tokens: int
    supports_tools: bool = False
    supports_vision: bool = False
    supports_streaming: bool = True
    cost_per_1k_input: float = 0.0   # USD
    cost_per_1k_output: float = 0.0  # USD
    latency_p50_ms: float = 1000.0
    latency_p99_ms: float = 5000.0
    benchmark_score: float = 0.5     # 综合能力评分 0-1
    tags: List[str] = field(default_factory=list)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """估算成本"""
        return (
            (input_tokens / 1000) * self.cost_per_1k_input +
            (output_tokens / 1000) * self.cost_per_1k_output
        )


@dataclass
class TaskProfile:
    """任务画像"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: str = ""
    description: str = ""
    estimated_complexity: TaskComplexity = TaskComplexity.MODERATE
    estimated_input_tokens: int = 1000
    estimated_output_tokens: int = 500
    requires_tools: bool = False
    requires_vision: bool = False
    requires_streaming: bool = True
    max_latency_ms: float = 30000.0
    max_cost_usd: float = 1.0
    priority: int = 5  # 1-10
    security_level: int = 1  # 1-5
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingDecision:
    """路由决策"""
    task_id: str
    selected_model: str
    selected_provider: str
    intelligence_level: IntelligenceLevel
    estimated_cost: float
    estimated_latency: float
    reason: str
    alternatives: List[str] = field(default_factory=list)
    confidence: float = 1.0


class ModelRegistry:
    """模型注册表"""

    def __init__(self):
        self._models: Dict[str, ModelCapability] = {}
        self._provider_models: Dict[str, List[str]] = {}

    def register(self, model: ModelCapability):
        """注册模型"""
        self._models[model.name] = model
        self._provider_models.setdefault(model.provider, []).append(model.name)

    def register_builtin(self):
        """注册内置模型"""
        builtins = [
            ModelCapability("deepseek-v4-flash", "deepseek", IntelligenceLevel.MEDIUM,
                            65536, 8192, True, False, True, 0.0003, 0.0006, 800, 3000, 0.65),
            ModelCapability("deepseek-r1", "deepseek", IntelligenceLevel.MAXIMUM,
                            131072, 32768, True, False, True, 0.002, 0.008, 5000, 15000, 0.92),
            ModelCapability("gpt-4o", "openai", IntelligenceLevel.HIGH,
                            128000, 16384, True, True, True, 0.005, 0.015, 1500, 5000, 0.88),
            ModelCapability("gpt-4o-mini", "openai", IntelligenceLevel.MEDIUM,
                            128000, 16384, True, True, True, 0.00015, 0.0006, 600, 2000, 0.72),
            ModelCapability("claude-3.5-sonnet", "anthropic", IntelligenceLevel.HIGH,
                            200000, 8192, True, True, True, 0.003, 0.015, 1200, 4000, 0.87),
            ModelCapability("claude-3-opus", "anthropic", IntelligenceLevel.MAXIMUM,
                            200000, 8192, True, True, True, 0.015, 0.075, 3000, 10000, 0.94),
            ModelCapability("qwen2.5-7b", "local", IntelligenceLevel.LIGHT,
                            32768, 4096, False, False, True, 0.0, 0.0, 200, 800, 0.45),
            ModelCapability("qwen2.5-72b", "local", IntelligenceLevel.MEDIUM,
                            131072, 8192, True, True, True, 0.0, 0.0, 500, 2000, 0.70),
            ModelCapability("gemini-2.0-flash", "google", IntelligenceLevel.MEDIUM,
                            1048576, 8192, True, True, True, 0.0001, 0.0004, 500, 1500, 0.75),
            ModelCapability("gemini-2.0-pro", "google", IntelligenceLevel.HIGH,
                            2097152, 16384, True, True, True, 0.002, 0.008, 1000, 3000, 0.85),
            ModelCapability("minimax-m3", "minimax", IntelligenceLevel.MEDIUM,
                            131072, 8192, True, False, True, 0.0002, 0.0005, 700, 2500, 0.68),
        ]
        for m in builtins:
            self.register(m)

    def get(self, name: str) -> Optional[ModelCapability]:
        return self._models.get(name)

    def get_by_level(self, level: IntelligenceLevel) -> List[ModelCapability]:
        """获取指定智力等级的所有模型"""
        return [m for m in self._models.values() if m.intelligence_level == level]

    def get_cheapest(self, level: IntelligenceLevel) -> Optional[ModelCapability]:
        """获取指定等级最便宜的模型"""
        models = self.get_by_level(level)
        if not models:
            return None
        return min(models, key=lambda m: m.cost_per_1k_input + m.cost_per_1k_output)

    def get_fastest(self, level: IntelligenceLevel) -> Optional[ModelCapability]:
        """获取指定等级最快的模型"""
        models = self.get_by_level(level)
        if not models:
            return None
        return min(models, key=lambda m: m.latency_p50_ms)

    def get_best(self, level: IntelligenceLevel) -> Optional[ModelCapability]:
        """获取指定等级评分最高的模型"""
        models = self.get_by_level(level)
        if not models:
            return None
        return max(models, key=lambda m: m.benchmark_score)

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": m.name,
                "provider": m.provider,
                "level": m.intelligence_level.name,
                "context": m.context_window,
                "cost_in": m.cost_per_1k_input,
                "cost_out": m.cost_per_1k_output,
                "score": m.benchmark_score,
            }
            for m in self._models.values()
        ]


class IntelligenceRouter:
    """
    智力分级路由引擎

    核心算法：
    1. 任务画像 → 复杂度评估
    2. 复杂度 → 所需智力等级
    3. 智力等级 → 候选模型列表
    4. 多目标优化：成本 × 延迟 × 能力
    5. 动态调整：基于历史成功率
    """

    def __init__(self, registry: Optional[ModelRegistry] = None):
        self._registry = registry or ModelRegistry()
        self._registry.register_builtin()
        self._routing_history: List[Dict[str, Any]] = []
        self._model_success_rates: Dict[str, List[bool]] = {}
        self._event_bus = None

    @property
    def registry(self) -> ModelRegistry:
        return self._registry

    # ── 复杂度评估 ────────────────────────────────────

    def estimate_complexity(self, task: TaskProfile) -> TaskComplexity:
        """评估任务复杂度"""
        # 基于输入特征
        score = 0

        # 输入长度
        if task.estimated_input_tokens < 100:
            score += 1
        elif task.estimated_input_tokens < 1000:
            score += 2
        elif task.estimated_input_tokens < 10000:
            score += 3
        else:
            score += 5

        # 输出长度
        if task.estimated_output_tokens < 100:
            score += 1
        elif task.estimated_output_tokens < 1000:
            score += 2
        else:
            score += 4

        # 工具需求
        if task.requires_tools:
            score += 2

        # 视觉需求
        if task.requires_vision:
            score += 3

        # 优先级加权
        score += task.priority * 0.5

        # 安全等级加权
        score += task.security_level * 0.5

        # 映射到复杂度等级
        if score <= 3:
            return TaskComplexity.TRIVIAL
        elif score <= 6:
            return TaskComplexity.SIMPLE
        elif score <= 10:
            return TaskComplexity.MODERATE
        elif score <= 15:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.VERY_COMPLEX

    def complexity_to_intelligence(self, complexity: TaskComplexity) -> IntelligenceLevel:
        """复杂度 → 所需智力等级"""
        mapping = {
            TaskComplexity.TRIVIAL: IntelligenceLevel.TINY,
            TaskComplexity.SIMPLE: IntelligenceLevel.LIGHT,
            TaskComplexity.MODERATE: IntelligenceLevel.MEDIUM,
            TaskComplexity.COMPLEX: IntelligenceLevel.HIGH,
            TaskComplexity.VERY_COMPLEX: IntelligenceLevel.MAXIMUM,
        }
        return mapping.get(complexity, IntelligenceLevel.MEDIUM)

    # ── 路由决策 ──────────────────────────────────────

    def route(self, task: TaskProfile) -> RoutingDecision:
        """路由决策：选择最优模型"""
        complexity = self.estimate_complexity(task)
        required_level = self.complexity_to_intelligence(complexity)

        # 获取候选模型
        candidates = self._registry.get_by_level(required_level)
        if not candidates:
            # 降级：使用低一级的模型
            lower_level = IntelligenceLevel(max(0, required_level.value - 1))
            candidates = self._registry.get_by_level(lower_level)
            fallback = True
        else:
            fallback = False

        if not candidates:
            return RoutingDecision(
                task_id=task.id,
                selected_model="none",
                selected_provider="none",
                intelligence_level=IntelligenceLevel.TINY,
                estimated_cost=0,
                estimated_latency=0,
                reason="no_available_model",
            )

        # 多目标评分
        def score_model(m: ModelCapability) -> float:
            # 能力分 (0-1)
            capability_score = m.benchmark_score

            # 成本分 (0-1, 越低越好)
            est_cost = m.estimate_cost(
                task.estimated_input_tokens,
                task.estimated_output_tokens,
            )
            cost_score = 1.0 - min(est_cost / task.max_cost_usd, 1.0) if task.max_cost_usd > 0 else 0.5

            # 延迟分 (0-1, 越低越好)
            latency_score = 1.0 - min(m.latency_p50_ms / task.max_latency_ms, 1.0) if task.max_latency_ms > 0 else 0.5

            # 成功率 (0-1)
            history = self._model_success_rates.get(m.name, [])
            reliability_score = sum(history) / len(history) if history else 0.8

            # 加权综合
            weights = {"capability": 0.4, "cost": 0.25, "latency": 0.2, "reliability": 0.15}
            return (
                weights["capability"] * capability_score +
                weights["cost"] * cost_score +
                weights["latency"] * latency_score +
                weights["reliability"] * reliability_score
            )

        # 评分排序
        scored = [(score_model(m), m) for m in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_model = scored[0]
        alternatives = [m.name for _, m in scored[1:4]]

        # 构建决策原因
        reasons = []
        if fallback:
            reasons.append(f"降级: 无 {required_level.name} 级别模型可用")
        reasons.append(
            f"评分: {best_score:.2f} | "
            f"成本: ${best_model.estimate_cost(task.estimated_input_tokens, task.estimated_output_tokens):.4f} | "
            f"延迟: {best_model.latency_p50_ms:.0f}ms"
        )

        decision = RoutingDecision(
            task_id=task.id,
            selected_model=best_model.name,
            selected_provider=best_model.provider,
            intelligence_level=best_model.intelligence_level,
            estimated_cost=best_model.estimate_cost(
                task.estimated_input_tokens, task.estimated_output_tokens
            ),
            estimated_latency=best_model.latency_p50_ms,
            reason="; ".join(reasons),
            alternatives=alternatives,
            confidence=best_score,
        )

        # 记录路由历史
        self._routing_history.append({
            "task_id": task.id,
            "complexity": complexity.name,
            "required_level": required_level.name,
            "decision": {
                "model": decision.selected_model,
                "score": best_score,
            },
            "timestamp": time.time(),
        })

        return decision

    def record_result(self, model_name: str, success: bool):
        """记录模型执行结果"""
        self._model_success_rates.setdefault(model_name, []).append(success)
        # 只保留最近 100 条
        if len(self._model_success_rates[model_name]) > 100:
            self._model_success_rates[model_name] = \
                self._model_success_rates[model_name][-100:]

    def get_stats(self) -> Dict[str, Any]:
        """获取路由统计"""
        total = len(self._routing_history)
        if total == 0:
            return {"total_routes": 0}

        level_dist = {}
        for r in self._routing_history:
            level = r["required_level"]
            level_dist[level] = level_dist.get(level, 0) + 1

        return {
            "total_routes": total,
            "level_distribution": level_dist,
            "model_success_rates": {
                name: {
                    "rate": sum(h) / len(h) if h else 0,
                    "count": len(h),
                }
                for name, h in self._model_success_rates.items()
            },
        }

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus
