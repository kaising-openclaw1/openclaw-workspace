"""
Agent OS — 验证系统 (L0 + L0.5)
=================================
ChatGPT × Gemini 融合共识：
  L0（强制，<1ms）：Schema validation（Pydantic model_validate）
  L0.5（强制，<10ms）：Structural consistency（引用检查、ID 验证）
  不做 Consensus Gate（MVP 阶段）
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("agent-os.engine.validator")


# ═══════════════════════════════════════════════════════════════
# 验证结果类型
# ═══════════════════════════════════════════════════════════════

@dataclass
class ValidationResult:
    passed: bool
    level: str  # "L0" | "L0.5"
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "level": self.level,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# ═══════════════════════════════════════════════════════════════
# L0: Schema Validation (~60 LOC)
# ═══════════════════════════════════════════════════════════════

class SchemaValidator:
    """
    L0 Schema Validation
    基于 JSON Schema 的结构验证，纯规则引擎，零 LLM 调用
    """

    def __init__(self):
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def register_schema(self, name: str, schema: Dict[str, Any]):
        """注册一个 JSON Schema"""
        self._schemas[name] = schema

    def validate(self, data: Any, schema_name: str) -> ValidationResult:
        """
        验证数据是否符合注册的 schema
        轻量实现：不依赖第三方 JSON Schema 库，支持核心类型检查
        """
        schema = self._schemas.get(schema_name)
        if not schema:
            return ValidationResult(
                passed=False,
                level="L0",
                errors=[f"Unknown schema: {schema_name}"],
            )

        errors: List[str] = []
        warnings: List[str] = []

        # 类型检查
        expected_type = schema.get("type")
        if expected_type == "object":
            if not isinstance(data, dict):
                return ValidationResult(
                    passed=False, level="L0",
                    errors=[f"Expected object, got {type(data).__name__}"],
                )
            # 必填字段检查
            required = schema.get("required", [])
            for field_name in required:
                if field_name not in data:
                    errors.append(f"Missing required field: {field_name}")

            # 属性类型检查
            properties = schema.get("properties", {})
            for field_name, field_schema in properties.items():
                if field_name in data:
                    field_errors = self._check_type(
                        data[field_name], field_schema, f"properties.{field_name}"
                    )
                    errors.extend(field_errors)

        elif expected_type == "array":
            if not isinstance(data, list):
                return ValidationResult(
                    passed=False, level="L0",
                    errors=[f"Expected array, got {type(data).__name__}"],
                )
            items_schema = schema.get("items", {})
            for i, item in enumerate(data):
                item_errors = self._check_type(item, items_schema, f"items[{i}]")
                errors.extend(item_errors)

        elif expected_type == "string":
            if not isinstance(data, str):
                errors.append(f"Expected string, got {type(data).__name__}")

        elif expected_type == "integer":
            if not isinstance(data, int):
                errors.append(f"Expected integer, got {type(data).__name__}")

        elif expected_type == "number":
            if not isinstance(data, (int, float)):
                errors.append(f"Expected number, got {type(data).__name__}")

        elif expected_type == "boolean":
            if not isinstance(data, bool):
                errors.append(f"Expected boolean, got {type(data).__name__}")

        return ValidationResult(
            passed=len(errors) == 0,
            level="L0",
            errors=errors,
            warnings=warnings,
        )

    def _check_type(self, value: Any, schema: Dict[str, Any], path: str) -> List[str]:
        """递归检查类型"""
        errors: List[str] = []
        expected = schema.get("type")

        if expected == "object":
            if not isinstance(value, dict):
                return [f"{path}: Expected object, got {type(value).__name__}"]
            required = schema.get("required", [])
            for f in required:
                if f not in value:
                    errors.append(f"{path}: Missing required field: {f}")
            props = schema.get("properties", {})
            for f, fs in props.items():
                if f in value:
                    errors.extend(self._check_type(value[f], fs, f"{path}.{f}"))

        elif expected == "array":
            if not isinstance(value, list):
                return [f"{path}: Expected array, got {type(value).__name__}"]
            items = schema.get("items", {})
            for i, item in enumerate(value):
                errors.extend(self._check_type(item, items, f"{path}[{i}]"))

        elif expected == "string":
            if not isinstance(value, str):
                errors.append(f"{path}: Expected string, got {type(value).__name__}")

        elif expected == "integer":
            if not isinstance(value, int):
                errors.append(f"{path}: Expected integer, got {type(value).__name__}")

        elif expected == "number":
            if not isinstance(value, (int, float)):
                errors.append(f"{path}: Expected number, got {type(value).__name__}")

        elif expected == "boolean":
            if not isinstance(value, bool):
                errors.append(f"{path}: Expected boolean, got {type(value).__name__}")

        return errors


# ═══════════════════════════════════════════════════════════════
# L0.5: Structural Consistency (~50 LOC)
# ═══════════════════════════════════════════════════════════════

class StructuralValidator:
    """
    L0.5 Structural Consistency
    引用检查、ID 验证、依赖完整性
    纯规则引擎，零 LLM 调用，<10ms
    """

    def __init__(self):
        self._known_ids: Set[str] = set()
        self._known_files: Set[str] = set()
        self._known_tasks: Set[str] = set()

    def register_id(self, id_: str):
        self._known_ids.add(id_)

    def register_file(self, path: str):
        self._known_files.add(path)

    def register_task(self, task_id: str):
        self._known_tasks.add(task_id)

    def validate_references(
        self,
        refs: List[str],
        ref_type: str = "id",
    ) -> ValidationResult:
        """
        验证引用列表中的所有引用是否有效
        ref_type: "id" | "file" | "task"
        """
        errors: List[str] = []
        warnings: List[str] = []

        known_set = {
            "id": self._known_ids,
            "file": self._known_files,
            "task": self._known_tasks,
        }.get(ref_type, self._known_ids)

        for ref in refs:
            if ref not in known_set:
                errors.append(f"Invalid {ref_type} reference: {ref}")

        return ValidationResult(
            passed=len(errors) == 0,
            level="L0.5",
            errors=errors,
            warnings=warnings,
        )

    def validate_dependency_graph(
        self,
        tasks: List[Dict[str, Any]],
    ) -> ValidationResult:
        """
        验证任务依赖图的完整性
        - 所有 depends_on 引用的 task_id 必须存在
        - 无循环依赖
        """
        errors: List[str] = []
        task_ids = {t.get("id") for t in tasks}

        for task in tasks:
            deps = task.get("depends_on", [])
            for dep in deps:
                if dep not in task_ids:
                    errors.append(
                        f"Task '{task.get('id')}' depends on unknown task '{dep}'"
                    )

        # 循环依赖检测（简单 DFS）
        if not errors:
            adj = {t.get("id"): t.get("depends_on", []) for t in tasks}
            visited: Set[str] = set()
            rec_stack: Set[str] = set()

            def dfs(node: str) -> bool:
                visited.add(node)
                rec_stack.add(node)
                for neighbor in adj.get(node, []):
                    if neighbor not in visited:
                        if dfs(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        errors.append(f"Circular dependency detected: {node} -> {neighbor}")
                        return True
                rec_stack.discard(node)
                return False

            for node in adj:
                if node not in visited:
                    dfs(node)

        return ValidationResult(
            passed=len(errors) == 0,
            level="L0.5",
            errors=errors,
        )


# ═══════════════════════════════════════════════════════════════
# 组合验证器
# ═══════════════════════════════════════════════════════════════

class Validator:
    """
    组合验证器：L0 + L0.5
    这是 ChatGPT × Gemini 融合共识的验证方案
    """

    def __init__(self):
        self.schema = SchemaValidator()
        self.structural = StructuralValidator()

    def validate_output(
        self,
        data: Any,
        schema_name: str,
        refs: Optional[List[str]] = None,
    ) -> Tuple[ValidationResult, ValidationResult]:
        """对输出做 L0 + L0.5 验证"""
        l0_result = self.schema.validate(data, schema_name)
        l05_result = ValidationResult(passed=True, level="L0.5")

        if refs:
            l05_result = self.structural.validate_references(refs)

        return l0_result, l05_result

    def all_pass(self, l0: ValidationResult, l05: ValidationResult) -> bool:
        """L0 和 L0.5 都通过"""
        return l0.passed and l05.passed
