"""
Agent OS — 3 层上下文管道
==========================
ChatGPT × Gemini 融合共识：Phase 0 做 3 层
  Layer 1: 会话上下文（Session Context）— 当前对话历史
  Layer 2: 项目上下文（Project Context）— 项目结构、规范
  Layer 3: 工具上下文（Tool Context）— MCP 工具定义、结果
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("agent-os.engine.context_pipeline")


@dataclass
class ContextLayer:
    """上下文层"""
    name: str
    content: str
    token_budget: float  # 占总 token 的百分比 (0.0-1.0)
    priority: int = 0   # 越高越优先保留

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "content_length": len(self.content),
            "token_budget": self.token_budget,
        }


class ContextPipeline:
    """
    3 层上下文管道
    采集 → 压缩 → 注入 → 预算
    """

    def __init__(self, max_tokens: int = 128000):
        self.max_tokens = max_tokens
        self._layers: List[ContextLayer] = []
        self._token_estimator = lambda s: len(s) // 2  # 粗略估计

    def add_layer(self, layer: ContextLayer):
        """添加上下文层"""
        self._layers.append(layer)
        # 按优先级排序
        self._layers.sort(key=lambda l: l.priority, reverse=True)

    def remove_layer(self, name: str):
        """移除上下文层"""
        self._layers = [l for l in self._layers if l.name != name]

    def assemble(self) -> str:
        """
        组装所有上下文层
        按 token 预算分配空间
        """
        total_budget = self.max_tokens
        parts: List[str] = []

        for layer in self._layers:
            budget = int(total_budget * layer.token_budget)
            content = layer.content

            # 如果内容超过预算，截断
            estimated_tokens = self._token_estimator(content)
            if estimated_tokens > budget:
                # 保留开头和结尾
                keep_chars = budget * 2
                if keep_chars < len(content):
                    head = content[:keep_chars // 2]
                    tail = content[-(keep_chars // 4):]
                    content = f"{head}\n\n...[truncated, {len(content)} chars total]...\n\n{tail}"
                    logger.info(f"Layer '{layer.name}' truncated to ~{budget} tokens")

            parts.append(f"=== {layer.name.upper()} ===\n{content}")

        return "\n\n".join(parts)

    def estimate_usage(self) -> Dict[str, Any]:
        """估算各层 token 使用情况"""
        usage = {}
        total = 0
        for layer in self._layers:
            tokens = self._token_estimator(layer.content)
            usage[layer.name] = {
                "chars": len(layer.content),
                "estimated_tokens": tokens,
                "budget_pct": layer.token_budget,
            }
            total += tokens
        usage["total_estimated_tokens"] = total
        usage["max_tokens"] = self.max_tokens
        usage["usage_pct"] = round(total / self.max_tokens * 100, 1)
        return usage

    def clear(self):
        """清空所有层"""
        self._layers.clear()


# ═══════════════════════════════════════════════════════════════
# 预构建的上下文层工厂
# ═══════════════════════════════════════════════════════════════

def create_session_layer(
    messages: List[Dict[str, Any]],
    max_recent: int = 20,
) -> ContextLayer:
    """创建会话上下文层"""
    recent = messages[-max_recent:] if len(messages) > max_recent else messages
    lines = []
    for msg in recent:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        # 截断过长消息
        if len(content) > 2000:
            content = content[:1000] + f"\n...[+{len(content)-2000} more chars]...\n" + content[-1000:]
        lines.append(f"[{role}]: {content}")
    return ContextLayer(
        name="session",
        content="\n".join(lines),
        token_budget=0.60,  # 60% 预算
        priority=10,
    )


def create_project_layer(
    project_info: Dict[str, Any],
) -> ContextLayer:
    """创建项目上下文层"""
    parts = []
    if project_info.get("name"):
        parts.append(f"Project: {project_info['name']}")
    if project_info.get("description"):
        parts.append(f"Description: {project_info['description']}")
    if project_info.get("structure"):
        parts.append(f"Structure:\n{project_info['structure']}")
    if project_info.get("rules"):
        parts.append(f"Rules:\n{project_info['rules']}")
    if project_info.get("config"):
        parts.append(f"Config:\n{json.dumps(project_info['config'], indent=2, ensure_ascii=False)}")
    return ContextLayer(
        name="project",
        content="\n".join(parts),
        token_budget=0.20,  # 20% 预算
        priority=5,
    )


def create_tool_layer(
    tool_definitions: List[Dict[str, Any]],
    tool_results: Optional[List[Dict[str, Any]]] = None,
) -> ContextLayer:
    """创建工具上下文层"""
    parts = ["Available Tools:"]
    for tool in tool_definitions:
        name = tool.get("name", "unknown")
        desc = tool.get("description", "")
        params = tool.get("parameters", {})
        parts.append(f"  - {name}: {desc}")
        if params:
            props = params.get("properties", {})
            required = params.get("required", [])
            for p_name, p_info in props.items():
                req = " (required)" if p_name in required else ""
                p_desc = p_info.get("description", "")
                p_type = p_info.get("type", "any")
                parts.append(f"      {p_name}: {p_type}{req} — {p_desc}")

    if tool_results:
        parts.append("\nRecent Tool Results:")
        for r in tool_results[-5:]:  # 最多 5 条
            name = r.get("name", "unknown")
            result = r.get("result", {})
            result_str = json.dumps(result, ensure_ascii=False)[:500]
            parts.append(f"  {name}: {result_str}")

    return ContextLayer(
        name="tools",
        content="\n".join(parts),
        token_budget=0.10,  # 10% 预算
        priority=3,
    )
