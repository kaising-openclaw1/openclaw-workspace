"""Golden Dataset 管理器 — AI Agent 测试用例集"""

from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class TestCase:
    """单个测试用例"""
    id: str
    input: str                    # 输入内容
    expected_output: str          # 期望输出（语义描述）
    category: str                 # 分类：问答/工具调用/推理/对话
    difficulty: str = "medium"    # 难度：easy/medium/hard
    tools_available: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    evaluation_criteria: list = field(default_factory=list)


class GoldenDataset:
    """Golden Dataset 管理器"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.cases: dict[str, TestCase] = {}
    
    def add_case(self, case: TestCase) -> None:
        self.cases[case.id] = case
    
    def add_cases(self, cases: list[TestCase]) -> None:
        for case in cases:
            self.add_case(case)
    
    def get_by_category(self, category: str) -> list[TestCase]:
        return [c for c in self.cases.values() if c.category == category]
    
    def get_by_difficulty(self, difficulty: str) -> list[TestCase]:
        return [c for c in self.cases.values() if c.difficulty == difficulty]
    
    @property
    def total(self) -> int:
        return len(self.cases)
    
    def save(self, path: str) -> None:
        data = {
            "name": self.name,
            "cases": {
                cid: {
                    "input": c.input,
                    "expected_output": c.expected_output,
                    "category": c.category,
                    "difficulty": c.difficulty,
                    "tools_available": c.tools_available,
                    "metadata": c.metadata,
                    "evaluation_criteria": c.evaluation_criteria,
                }
                for cid, c in self.cases.items()
            }
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Golden Dataset 已保存：{path}（{self.total} 个用例）")
    
    @classmethod
    def load(cls, path: str) -> "GoldenDataset":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ds = cls(name=data["name"])
        for cid, cdata in data["cases"].items():
            ds.add_case(TestCase(
                id=cid,
                input=cdata["input"],
                expected_output=cdata["expected_output"],
                category=cdata["category"],
                difficulty=cdata.get("difficulty", "medium"),
                tools_available=cdata.get("tools_available", []),
                metadata=cdata.get("metadata", {}),
                evaluation_criteria=cdata.get("evaluation_criteria", []),
            ))
        print(f"Golden Dataset 已加载：{ds.total} 个用例")
        return ds
