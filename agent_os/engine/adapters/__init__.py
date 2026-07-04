"""
Agent OS v7.0 — Model Adapters
================================
模型适配器实现：OpenAI-compatible + Anthropic Claude
"""

from .openai_adapter import OpenAIAdapter
from .anthropic_adapter import AnthropicAdapter

__all__ = [
    "OpenAIAdapter",
    "AnthropicAdapter",
]
