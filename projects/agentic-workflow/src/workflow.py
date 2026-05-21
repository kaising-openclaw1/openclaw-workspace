"""工作流编排引擎"""

from __future__ import annotations
import asyncio
import time
from typing import Any, Callable, Dict, List, Optional

from .agent import Agent
from .dag import DAG
from .llm import LLMConfig
from .logger import WorkflowLogger
from .state import WorkflowState


class Workflow:
    """多智能体工作流编排引擎"""

    def __init__(
        self,
        name: str = "workflow",
        agents: Optional[List[Agent]] = None,
        steps: Optional[List[dict]] = None,
        dag: Optional[DAG] = None,
        llm: Optional[LLMConfig] = None,
    ) -> None:
        self.name = name
        self.agents: Dict[str, Agent] = {}
        self.steps = steps or []
        self.dag = dag
        self.llm = llm
        self.logger = WorkflowLogger(name)
        self.state = WorkflowState()

        if agents:
            for agent in agents:
                self.agents[agent.name] = agent

    def add_agent(self, agent: Agent) -> None:
        """添加 Agent"""
        self.agents[agent.name] = agent

    def _get_agent(self, name: str) -> Agent:
        """获取 Agent"""
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not found. Available: {list(self.agents.keys())}")
        return self.agents[name]

    def _resolve_task(self, task: str, context: dict) -> str:
        """解析任务模板中的变量"""
        for key, value in context.items():
            task = task.replace(f"{{{key}}}", str(value))
        return task

    def _build_context(self, step_index: int) -> dict:
        """构建当前步骤的上下文"""
        context = {}
        for i, result in enumerate(self.state.results):
            context[f"step_{i + 1}_result"] = result[:500]  # 截断避免过长
        return context

    async def _execute_step(self, step: dict, context: dict) -> str:
        """执行单个工作流步骤"""
        agent_name = step["agent"]
        agent = self._get_agent(agent_name)
        task = self._resolve_task(step["task"], context)

        # 检查条件
        if "condition" in step:
            condition = step["condition"]
            if not eval(f"self.state.{condition}", {"self": self.state}):
                self.logger.log_skip(agent_name, task, condition)
                return "(skipped)"

        self.logger.log_start(agent_name, task)
        start = time.time()

        result = await agent.execute(task, context)

        elapsed = time.time() - start
        self.logger.log_complete(agent_name, task, elapsed, len(result))

        return result

    async def run(
        self,
        custom_llm_call: Optional[Callable] = None,
        **kwargs: Any,
    ) -> dict:
        """
        执行工作流

        支持两种方式：
        1. 顺序步骤（steps 参数）
        2. DAG 编排（dag 参数）
        """
        self.logger.log_workflow_start(self.name, len(self.agents))
        self.state.start_time = time.time()

        if self.dag:
            result = await self._run_dag(custom_llm_call, **kwargs)
        else:
            result = await self._run_sequential(custom_llm_call, **kwargs)

        self.state.end_time = time.time()
        elapsed = self.state.end_time - self.state.start_time
        self.logger.log_workflow_complete(self.name, elapsed, len(self.state.results))

        return {
            "workflow": self.name,
            "status": "completed",
            "steps": len(self.state.results),
            "results": self.state.results,
            "elapsed_seconds": elapsed,
            "log": self.logger.get_log(),
        }

    async def _run_sequential(
        self,
        custom_llm_call: Optional[Callable] = None,
        **kwargs: Any,
    ) -> dict:
        """顺序执行步骤"""
        for i, step in enumerate(self.steps):
            context = self._build_context(i)
            context.update(kwargs)

            result = await self._execute_step(step, context)
            self.state.results.append(result)
            self.state.step_count += 1

        return self.state.to_dict()

    async def _run_dag(
        self,
        custom_llm_call: Optional[Callable] = None,
        **kwargs: Any,
    ) -> dict:
        """DAG 编排执行"""
        groups = self.dag.get_parallel_groups()
        nodes = self.dag.nodes

        for group in groups:
            tasks = []
            for node_id in group:
                node = nodes[node_id]
                agent = self._get_agent(node["agent"])
                task_text = self._resolve_task(node["task"], kwargs)
                context = self._build_context(self.state.step_count)
                context.update(kwargs)

                async def _exec(agent=agent, task=task_text, context=context, node_id=node_id):
                    self.logger.log_start(agent.name, f"[{node_id}] {task}")
                    start = time.time()
                    result = await agent.execute(task, context)
                    elapsed = time.time() - start
                    self.logger.log_complete(agent.name, f"[{node_id}] {task}", elapsed, len(result))
                    return node_id, result

                tasks.append(_exec())

            # 并行执行同一组的节点
            results = await asyncio.gather(*tasks)
            for node_id, result in results:
                self.state.results.append(result)
                self.state.step_count += 1

        return self.state.to_dict()
