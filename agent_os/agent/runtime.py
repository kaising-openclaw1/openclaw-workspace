"""
Agent OS — Agent 运行时
=======================
Agent 生命周期管理、沙箱执行、工具注册
"""

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("agent-os.agent.runtime")


class AgentStatus(Enum):
    CREATED = auto()
    INITIALIZING = auto()
    IDLE = auto()
    BUSY = auto()
    ERROR = auto()
    TERMINATED = auto()


@dataclass
class AgentSpec:
    """Agent 规格"""
    name: str
    description: str = ""
    model: str = ""
    system_prompt: str = ""
    tools: List[str] = field(default_factory=list)
    max_concurrency: int = 1
    timeout: float = 300.0
    memory_limit_mb: int = 512
    environment: Dict[str, str] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)


class AgentInstance:
    """Agent 实例"""

    def __init__(self, spec: AgentSpec):
        self.id = uuid.uuid4().hex[:12]
        self.spec = spec
        self.status = AgentStatus.CREATED
        self.created_at = time.time()
        self._event_bus = None
        self._context: Dict[str, Any] = {}

    async def initialize(self):
        self.status = AgentStatus.INITIALIZING
        await asyncio.sleep(0.1)  # 模拟初始化
        self.status = AgentStatus.IDLE
        logger.info(f"Agent 就绪: {self.spec.name} ({self.id})")

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.status = AgentStatus.BUSY
        try:
            result = await self._execute(task)
            self.status = AgentStatus.IDLE
            return result
        except Exception as e:
            self.status = AgentStatus.ERROR
            return {"error": str(e)}

    async def _execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务（由子类或插件实现）"""
        return {"message": f"Agent {self.spec.name} 已处理: {task.get('prompt', '')}"}

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.spec.name,
            "status": self.status.name,
            "model": self.spec.model,
            "created_at": self.created_at,
            "tools": self.spec.tools,
        }


class AgentRuntime:
    """
    Agent 运行时管理器

    管理多个 Agent 实例的生命周期：
    - 创建/销毁 Agent
    - 任务分配
    - 并发控制
    - 健康监控
    """

    def __init__(self):
        self._agents: Dict[str, AgentInstance] = {}
        self._agent_specs: Dict[str, AgentSpec] = {}
        self._event_bus = None

    async def create_agent(self, spec: AgentSpec) -> str:
        """创建 Agent"""
        agent = AgentInstance(spec)
        if self._event_bus:
            agent.set_event_bus(self._event_bus)
        await agent.initialize()
        self._agents[agent.id] = agent
        self._agent_specs[agent.id] = spec
        logger.info(f"Agent 已创建: {spec.name} ({agent.id})")
        return agent.id

    async def destroy_agent(self, agent_id: str):
        """销毁 Agent"""
        agent = self._agents.pop(agent_id, None)
        self._agent_specs.pop(agent_id, None)
        if agent:
            agent.status = AgentStatus.TERMINATED
            logger.info(f"Agent 已销毁: {agent_id}")

    async def run_agent(self, agent_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """在指定 Agent 上运行任务"""
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent 未找到: {agent_id}")
        return await agent.run(task)

    def get_agent(self, agent_id: str) -> Optional[AgentInstance]:
        return self._agents.get(agent_id)

    def list_agents(self, status: Optional[AgentStatus] = None) -> List[Dict[str, Any]]:
        agents = [a.to_dict() for a in self._agents.values()]
        if status:
            agents = [a for a in agents if a["status"] == status.name]
        return agents

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total": len(self._agents),
            "idle": sum(1 for a in self._agents.values() if a.status == AgentStatus.IDLE),
            "busy": sum(1 for a in self._agents.values() if a.status == AgentStatus.BUSY),
            "error": sum(1 for a in self._agents.values() if a.status == AgentStatus.ERROR),
        }

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus
