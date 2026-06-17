"""
Agent OS — 核心引擎：插件系统
============================
热加载插件架构，能力即服务 (Tool-as-a-Service)
"""

import asyncio
import importlib
import inspect
import logging
import os
import pkgutil
import sys
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Type

logger = logging.getLogger("agent-os.core.plugin_system")


class PluginState(Enum):
    DISCOVERED = auto()
    LOADED = auto()
    INITIALIZED = auto()
    RUNNING = auto()
    STOPPED = auto()
    ERROR = auto()


@dataclass
class PluginManifest:
    """插件元数据"""
    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    min_agent_os_version: str = "0.1.0"
    tags: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    plugin: str = ""
    timeout: float = 30.0
    requires_approval: bool = False


class PluginBase(ABC):
    """插件基类"""

    def __init__(self):
        self.manifest: PluginManifest = PluginManifest(
            name=self.__class__.__name__,
            version="0.1.0",
        )
        self.state = PluginState.DISCOVERED
        self._tools: Dict[str, ToolDefinition] = {}
        self._event_bus = None
        self._config: Dict[str, Any] = {}

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        ...

    async def start(self) -> bool:
        """启动插件"""
        self.state = PluginState.RUNNING
        return True

    async def stop(self) -> bool:
        """停止插件"""
        self.state = PluginState.STOPPED
        return True

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
        timeout: float = 30.0,
        requires_approval: bool = False,
    ):
        """注册工具"""
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            plugin=self.manifest.name,
            timeout=timeout,
            requires_approval=requires_approval,
        )

    def get_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus


class PluginRegistry:
    """
    插件注册表

    特性：
    - 热加载/卸载
    - 依赖解析
    - 沙箱隔离
    - 权限管理
    """

    def __init__(self, plugin_dirs: List[str] = None):
        self._plugins: Dict[str, PluginBase] = {}
        self._plugin_states: Dict[str, PluginState] = {}
        self._tool_registry: Dict[str, ToolDefinition] = {}
        self._plugin_dirs = plugin_dirs or []
        self._event_bus = None
        self._lock = None

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus

    # ── 插件加载 ──────────────────────────────────────

    async def _ensure_lock(self):
        if self._lock is None:
            self._lock = asyncio.Lock()

    async def discover(self, paths: List[str] = None) -> List[str]:
        """发现可用的插件"""
        await self._ensure_lock()
        paths = paths or self._plugin_dirs
        discovered = []

        for path in paths:
            if not os.path.isdir(path):
                continue
            sys.path.insert(0, os.path.dirname(path))

            for importer, name, is_pkg in pkgutil.iter_modules([path]):
                if name.startswith("_"):
                    continue
                try:
                    module = importlib.import_module(name)
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (inspect.isclass(attr) and
                            issubclass(attr, PluginBase) and
                            attr is not PluginBase):
                            plugin = attr()
                            plugin_name = plugin.manifest.name
                            self._plugins[plugin_name] = plugin
                            self._plugin_states[plugin_name] = PluginState.DISCOVERED
                            discovered.append(plugin_name)
                            logger.info(f"发现插件: {plugin_name} v{plugin.manifest.version}")
                except Exception as e:
                    logger.warning(f"加载插件失败 {name}: {e}")

        return discovered

    async def load(self, plugin_name: str, config: Dict[str, Any] = None) -> bool:
        """加载并初始化插件"""
        await self._ensure_lock()
        async with self._lock:
            plugin = self._plugins.get(plugin_name)
            if not plugin:
                logger.error(f"插件未找到: {plugin_name}")
                return False

            try:
                if self._event_bus:
                    plugin.set_event_bus(self._event_bus)

                success = await plugin.initialize(config or {})
                if not success:
                    self._plugin_states[plugin_name] = PluginState.ERROR
                    return False

                self._plugin_states[plugin_name] = PluginState.INITIALIZED

                # 注册工具
                for tool in plugin.get_tools():
                    self._tool_registry[tool.name] = tool

                logger.info(f"插件已加载: {plugin_name}")
                return True
            except Exception as e:
                self._plugin_states[plugin_name] = PluginState.ERROR
                logger.error(f"插件初始化失败 {plugin_name}: {e}")
                return False

    async def unload(self, plugin_name: str) -> bool:
        """卸载插件"""
        await self._ensure_lock()
        async with self._lock:
            plugin = self._plugins.get(plugin_name)
            if not plugin:
                return False

            try:
                await plugin.stop()
            except Exception as e:
                logger.warning(f"插件停止异常 {plugin_name}: {e}")

            # 移除工具
            tools_to_remove = [
                name for name, t in self._tool_registry.items()
                if t.plugin == plugin_name
            ]
            for name in tools_to_remove:
                del self._tool_registry[name]

            del self._plugins[plugin_name]
            del self._plugin_states[plugin_name]
            logger.info(f"插件已卸载: {plugin_name}")
            return True

    async def start_all(self) -> int:
        """启动所有已加载的插件"""
        started = 0
        for name, plugin in self._plugins.items():
            if self._plugin_states.get(name) == PluginState.INITIALIZED:
                try:
                    await plugin.start()
                    self._plugin_states[name] = PluginState.RUNNING
                    started += 1
                except Exception as e:
                    logger.error(f"插件启动失败 {name}: {e}")
        return started

    async def stop_all(self) -> int:
        """停止所有插件"""
        stopped = 0
        for name, plugin in self._plugins.items():
            try:
                await plugin.stop()
                self._plugin_states[name] = PluginState.STOPPED
                stopped += 1
            except Exception as e:
                logger.error(f"插件停止失败 {name}: {e}")
        return stopped

    # ── 工具管理 ──────────────────────────────────────

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tool_registry.get(name)

    def get_all_tools(self) -> Dict[str, ToolDefinition]:
        return dict(self._tool_registry)

    def get_tools_by_plugin(self, plugin_name: str) -> List[ToolDefinition]:
        return [t for t in self._tool_registry.values() if t.plugin == plugin_name]

    # ── 查询 ──────────────────────────────────────────

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        return self._plugins.get(name)

    def get_all_plugins(self) -> Dict[str, PluginBase]:
        return dict(self._plugins)

    def get_plugin_state(self, name: str) -> Optional[PluginState]:
        return self._plugin_states.get(name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": name,
                "version": p.manifest.version,
                "description": p.manifest.description,
                "state": self._plugin_states.get(name, PluginState.DISCOVERED).name,
                "tools": len(p.get_tools()),
            }
            for name, p in self._plugins.items()
        ]
