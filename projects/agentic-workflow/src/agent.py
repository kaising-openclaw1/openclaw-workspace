"""Agent 定义与人设管理"""

from __future__ import annotations
from typing import Any, Callable, List, Optional
from dataclasses import dataclass, field

from .tool import Tool


@dataclass
class Agent:
    """AI 智能体 - 具有角色、能力和工具的自主执行单元"""

    name: str
    role: str = ""
    tools: List[Tool] = field(default_factory=list)
    llm_config: Optional["LLMConfig"] = None  # type: ignore  # noqa: F821
    temperature: float = 0.7
    max_tokens: int = 4096

    # 自我修正
    self_correct: Optional["SelfCorrect"] = None  # type: ignore  # noqa: F821
    _attempts: int = 0

    # 状态
    last_result: str = ""
    needs_revision: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.tools, list) and not all(
            hasattr(t, "name") and hasattr(t, "func") for t in self.tools
        ):
            # 允许传入装饰器包装前的函数，自动包装
            self.tools = [Tool(name=fn.__name__, description=fn.__doc__ or "")(fn) for fn in self.tools if callable(fn)]  # type: ignore

    def build_prompt(self, task: str, context: dict[str, str] | None = None) -> str:
        """构建 Agent 的系统提示词"""
        lines = [
            f"你是一个AI助手，名字叫「{self.name}」。",
        ]
        if self.role:
            lines.append(f"你的角色和能力：{self.role}")

        if self.tools:
            tool_list = "\n".join(
                f"- {t.name}: {t.description}" for t in self.tools
            )
            lines.append(f"你可以使用以下工具：\n{tool_list}")
            lines.append(
                "如果需要工具，请用 JSON 格式返回：{\"tool\": \"tool_name\", \"args\": {...}}"
            )

        if self.self_correct and self._attempts > 0:
            lines.append(f"\n这是你的第 {self._attempts + 1} 次尝试。")
            lines.append("请检查之前的结果是否有问题，并改进：")
            lines.append(f"之前的结果：{self.last_result}")
            lines.append(self.self_correct.prompt)

        if context:
            lines.append("\n相关上下文：")
            for key, value in context.items():
                lines.append(f"- {key}: {value}")

        lines.append(f"\n当前任务：{task}")
        return "\n".join(lines)

    async def execute(
        self,
        task: str,
        context: dict[str, str] | None = None,
        llm_call: Callable | None = None,
    ) -> str:
        """执行任务"""
        prompt = self.build_prompt(task, context)

        if llm_call:
            result = await llm_call(prompt, self)
        else:
            # 默认：使用 Agent 自带的 LLM 配置
            from .llm import call_llm
            result = await call_llm(prompt, self.llm_config, self.temperature, self.max_tokens)

        self.last_result = result
        self.needs_revision = "需要修改" in result or "needs revision" in result.lower()

        # 自我修正
        if (
            self.self_correct
            and self.needs_revision
            and self._attempts < self.self_correct.max_attempts
        ):
            self._attempts += 1
            return await self.execute(task, context, llm_call)

        return result

    def reset(self) -> None:
        """重置 Agent 状态"""
        self.last_result = ""
        self.needs_revision = False
        self._attempts = 0
