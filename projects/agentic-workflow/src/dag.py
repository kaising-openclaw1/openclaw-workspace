"""DAG 任务调度器 - 有向无环图编排"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from collections import deque


class DAG:
    """有向无环图任务调度"""

    def __init__(self) -> None:
        self._nodes: Dict[str, dict] = {}
        self._edges: Dict[str, List[str]] = {}
        self._reverse_edges: Dict[str, List[str]] = {}

    def add_node(self, node_id: str, agent: str = "", task: str = "", **kwargs: Any) -> None:
        """添加节点"""
        self._nodes[node_id] = {"agent": agent, "task": task, **kwargs}
        self._edges.setdefault(node_id, [])
        self._reverse_edges.setdefault(node_id, [])

    def add_edge(self, from_id: str, to_id: str) -> None:
        """添加有向边"""
        self._edges.setdefault(from_id, []).append(to_id)
        self._reverse_edges.setdefault(to_id, []).append(from_id)

    def topological_sort(self) -> List[str]:
        """拓扑排序"""
        in_degree = {node: len(self._reverse_edges.get(node, [])) for node in self._nodes}
        queue = deque([n for n, d in in_degree.items() if d == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in self._edges.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self._nodes):
            raise ValueError("DAG contains a cycle!")
        return result

    def get_parallel_groups(self) -> List[List[str]]:
        """获取可以并行执行的节点组"""
        in_degree = {node: len(self._reverse_edges.get(node, [])) for node in self._nodes}
        groups = []

        remaining = set(self._nodes.keys())
        while remaining:
            # 找入度为 0 的节点
            group = [n for n in remaining if in_degree.get(n, 0) == 0]
            if not group:
                raise ValueError("DAG contains a cycle!")
            groups.append(group)
            for node in group:
                remaining.discard(node)
                for neighbor in self._edges.get(node, []):
                    in_degree[neighbor] = in_degree.get(neighbor, 1) - 1

        return groups

    @property
    def nodes(self) -> Dict[str, dict]:
        return self._nodes
