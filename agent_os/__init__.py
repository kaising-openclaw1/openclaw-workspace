"""
Agent OS — 多机器 Agent 算力操作系统
====================================
掌控多源算力，保护源码安全，最大化智力输出
"""

__version__ = "0.1.0"
__author__ = "小鸣"

from .core.engine import AgentOSEngine, AgentOSConfig
from .core.event_bus import EventBus, Event, EventPriority, EventCategory
from .core.state_machine import StateMachine, State
from .core.plugin_system import PluginRegistry, PluginBase, PluginManifest
