"""工作流状态管理"""

from __future__ import annotations
import time
from typing import Any, Dict, List


class WorkflowState:
    """工作流运行时状态"""

    def __init__(self) -> None:
        self.start_time: float = 0
        self.end_time: float = 0
        self.step_count: int = 0
        self.results: List[str] = []
        self.errors: List[str] = []
        self.variables: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        """设置变量"""
        self.variables[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(key, default)

    @property
    def needs_revision(self) -> bool:
        """是否需要修改（最后一步的结果）"""
        if not self.results:
            return False
        last = self.results[-1].lower()
        return "需要修改" in last or "needs revision" in last

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "step_count": self.step_count,
            "results": self.results,
            "errors": self.errors,
            "variables": self.variables,
            "elapsed": self.end_time - self.start_time if self.end_time else 0,
        }
