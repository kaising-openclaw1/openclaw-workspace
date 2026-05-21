"""审计日志系统 - 完整的执行轨迹"""

from __future__ import annotations
import json
import time
from typing import Any, List


class WorkflowLogger:
    """工作流审计日志"""

    def __init__(self, workflow_name: str) -> None:
        self.workflow_name = workflow_name
        self._log: List[dict] = []

    def log_workflow_start(self, name: str, agent_count: int) -> None:
        self._log.append({
            "ts": time.time(),
            "event": "workflow_start",
            "name": name,
            "agents": agent_count,
        })

    def log_workflow_complete(self, name: str, elapsed: float, step_count: int) -> None:
        self._log.append({
            "ts": time.time(),
            "event": "workflow_complete",
            "name": name,
            "elapsed": round(elapsed, 2),
            "steps": step_count,
        })

    def log_start(self, agent: str, task: str) -> None:
        self._log.append({
            "ts": time.time(),
            "event": "step_start",
            "agent": agent,
            "task": task,
        })

    def log_complete(self, agent: str, task: str, elapsed: float, result_len: int) -> None:
        self._log.append({
            "ts": time.time(),
            "event": "step_complete",
            "agent": agent,
            "task": task,
            "elapsed": round(elapsed, 2),
            "result_len": result_len,
        })

    def log_skip(self, agent: str, task: str, condition: str) -> None:
        self._log.append({
            "ts": time.time(),
            "event": "step_skip",
            "agent": agent,
            "task": task,
            "condition": condition,
        })

    def log_error(self, agent: str, error: str) -> None:
        self._log.append({
            "ts": time.time(),
            "event": "error",
            "agent": agent,
            "error": error,
        })

    def get_log(self) -> List[dict]:
        """获取日志"""
        return self._log

    def summary(self) -> str:
        """生成摘要"""
        lines = [f"Workflow: {self.workflow_name}", "=" * 40]
        for entry in self._log:
            event = entry["event"]
            if event == "workflow_start":
                lines.append(f"▶ 开始工作流: {entry['name']} ({entry['agents']} agents)")
            elif event == "workflow_complete":
                lines.append(f"✓ 完成: {entry['elapsed']}s, {entry['steps']} steps")
            elif event == "step_start":
                lines.append(f"  → [{entry['agent']}] {entry['task'][:60]}...")
            elif event == "step_complete":
                lines.append(f"  ✓ [{entry['agent']}] {entry['elapsed']}s")
            elif event == "step_skip":
                lines.append(f"  ⊘ [{entry['agent']}] skipped ({entry['condition']})")
            elif event == "error":
                lines.append(f"  ✗ [{entry['agent']}] {entry['error']}")
        return "\n".join(lines)
