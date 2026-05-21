"""工具注册与执行系统"""

from __future__ import annotations
import functools
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Tool:
    """工具定义 - 可被 Agent 调用的函数"""

    name: str
    description: str
    func: Optional[Callable] = None

    def __call__(self, func: Callable) -> "Tool":
        """装饰器模式：@Tool(name=..., description=...)"""
        self.func = func
        return self

    def execute(self, **kwargs: Any) -> Any:
        """执行工具"""
        if self.func is None:
            raise ValueError(f"Tool '{self.name}' has no function assigned")
        return self.func(**kwargs)

    def to_dict(self) -> dict:
        """转换为 API 可调用的格式"""
        import inspect
        if self.func is None:
            return {"name": self.name, "description": self.description, "parameters": {}}
        sig = inspect.signature(self.func)
        params = {}
        for name, param in sig.parameters.items():
            p = {"type": "string"}
            if param.default is not inspect.Parameter.empty:
                p["default"] = str(param.default)
            if param.annotation is not inspect.Parameter.empty:
                p["type"] = param.annotation.__name__ if hasattr(param.annotation, "__name__") else "string"
            params[name] = p
        return {
            "name": self.name,
            "description": self.description,
            "parameters": params,
        }


class ToolRegistry:
    """工具注册中心"""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, func: Callable) -> Tool:
        """注册工具（装饰器模式）"""
        tool = Tool(name=func.__name__, description=func.__doc__ or "", func=func)
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)

    def list(self) -> List[Tool]:
        """列出所有工具"""
        return list(self._tools.values())

    def execute(self, name: str, **kwargs: Any) -> Any:
        """执行指定工具"""
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Tool '{name}' not found")
        return tool.execute(**kwargs)
