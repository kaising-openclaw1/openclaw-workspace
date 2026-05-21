"""自我修正模块"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class SelfCorrect:
    """自我修正配置 - 让 Agent 可以反思和优化自己的输出"""

    max_attempts: int = 3
    prompt: str = "请仔细检查你的回答是否有错误、遗漏或可以改进的地方。如果有问题，请修正后重新提交。"
