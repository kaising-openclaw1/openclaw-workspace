"""回归测试追踪器"""

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class TestRun:
    """一次测试运行的快照"""
    timestamp: str
    agent_version: str
    model_name: str
    results: list
    summary: dict


class RegressionTracker:
    """回归测试追踪器"""
    
    def __init__(self, history_path: str = "data/test_history"):
        self.history_path = Path(history_path)
        self.history_path.mkdir(parents=True, exist_ok=True)
        self.runs: list[TestRun] = self._load_history()
    
    def _load_history(self) -> list:
        runs = []
        for f in sorted(self.history_path.glob("run_*.json")):
            with open(f) as fh:
                data = json.load(fh)
                runs.append(TestRun(**data))
        return runs
    
    def save_run(self, run: TestRun) -> None:
        filename = f"run_{run.timestamp.replace(':', '-').replace(' ', '_')}.json"
        filepath = self.history_path / filename
        with open(filepath, "w") as f:
            json.dump({
                "timestamp": run.timestamp,
                "agent_version": run.agent_version,
                "model_name": run.model_name,
                "results": run.results,
                "summary": run.summary,
            }, f, ensure_ascii=False, indent=2)
        self.runs.append(run)
    
    def compare_runs(self, baseline_id: int, current_id: int) -> dict:
        """比较两次测试运行"""
        baseline = self.runs[baseline_id]
        current = self.runs[current_id]
        
        baseline_pass_rate = baseline.summary.get("pass_rate", "0%")
        current_pass_rate = current.summary.get("pass_rate", "0%")
        baseline_score = baseline.summary.get("avg_score", "0/10")
        current_score = current.summary.get("avg_score", "0/10")
        
        regression_cases = []
        for b_res in baseline.results:
            c_res = next(
                (r for r in current.results if r.get("case_id") == b_res.get("case_id")),
                None
            )
            if c_res:
                b_score = b_res.get("score", 0)
                c_score = c_res.get("score", 0)
                if b_score > c_score + 1:
                    regression_cases.append({
                        "case_id": b_res.get("case_id"),
                        "before": b_score,
                        "after": c_score,
                        "delta": c_score - b_score,
                    })
        
        return {
            "baseline": {
                "version": baseline.agent_version,
                "model": baseline.model_name,
                "pass_rate": baseline_pass_rate,
                "avg_score": baseline_score,
            },
            "current": {
                "version": current.agent_version,
                "model": current.model_name,
                "pass_rate": current_pass_rate,
                "avg_score": current_score,
            },
            "regressions": regression_cases,
            "regression_count": len(regression_cases),
        }
