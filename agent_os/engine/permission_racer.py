"""
Agent OS — 3 层权限竞速系统
============================
受 Claude Code 4 路竞速启发，简化为 3 层：
  Route 1: 策略引擎（Policy Engine）— 全局/项目/会话策略
  Route 2: 风险分类器（Risk Classifier）— 基于工具类型+参数的风险评分
  Route 3: 用户确认（User Confirm）— 终端提示/推送通知

竞速规则：
  任何 Route 返回 deny → DENY
  所有 Route 返回 allow → ALLOW
  混合 → CONFIRM
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("agent-os.engine.permission_racer")


class Permission(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"


class RiskLevel(str, Enum):
    READ = "read"      # 读操作，低风险
    WRITE = "write"    # 写操作，中风险
    EXEC = "exec"      # 执行操作，高风险
    AGENT = "agent"    # Agent 自主操作，最高风险


@dataclass
class PermissionRequest:
    """权限请求"""
    tool_name: str
    arguments: Dict[str, Any]
    risk_level: RiskLevel = RiskLevel.READ
    resource_path: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "risk_level": self.risk_level.value,
            "resource_path": self.resource_path,
        }


@dataclass
class PermissionResult:
    """权限结果"""
    permission: Permission
    route: str  # "policy" | "risk" | "user"
    reason: str = ""


# ═══════════════════════════════════════════════════════════════
# Route 1: 策略引擎
# ═══════════════════════════════════════════════════════════════

class PolicyEngine:
    """
    策略引擎
    支持全局策略、项目策略、会话策略
    策略格式：YAML 风格的规则列表
    """

    def __init__(self):
        self._policies: List[Dict[str, Any]] = []

    def add_policy(self, policy: Dict[str, Any]):
        """添加策略规则"""
        self._policies.append(policy)

    def evaluate(self, request: PermissionRequest) -> PermissionResult:
        """评估权限请求"""
        for policy in self._policies:
            # 工具名匹配
            tool_match = policy.get("tool")
            if tool_match and tool_match != request.tool_name:
                continue

            # 资源路径匹配
            path_match = policy.get("path")
            if path_match and request.resource_path:
                if not request.resource_path.startswith(path_match):
                    continue

            # 风险级别匹配
            risk_match = policy.get("risk_level")
            if risk_match and risk_match != request.risk_level.value:
                continue

            # 命中策略
            action = policy.get("action", "allow")
            if action == "deny":
                return PermissionResult(
                    permission=Permission.DENY,
                    route="policy",
                    reason=policy.get("reason", "Denied by policy"),
                )
            elif action == "allow":
                return PermissionResult(
                    permission=Permission.ALLOW,
                    route="policy",
                    reason="Allowed by policy",
                )

        # 无匹配策略 → 默认 allow（由其他 route 决定）
        return PermissionResult(
            permission=Permission.ALLOW,
            route="policy",
            reason="No matching policy",
        )


# ═══════════════════════════════════════════════════════════════
# Route 2: 风险分类器
# ═══════════════════════════════════════════════════════════════

class RiskClassifier:
    """
    风险分类器
    基于工具类型 + 参数的风险评分
    纯规则引擎（不是 ML），保证确定性
    """

    def __init__(self):
        self._rules: List[Dict[str, Any]] = []

    def add_rule(self, rule: Dict[str, Any]):
        """添加风险规则"""
        self._rules.append(rule)

    def classify(self, request: PermissionRequest) -> PermissionResult:
        """分类风险并返回权限建议"""
        # 默认风险级别
        risk_map = {
            RiskLevel.READ: Permission.ALLOW,
            RiskLevel.WRITE: Permission.CONFIRM,
            RiskLevel.EXEC: Permission.CONFIRM,
            RiskLevel.AGENT: Permission.DENY,
        }

        result = risk_map.get(request.risk_level, Permission.CONFIRM)

        # 应用规则覆盖
        for rule in self._rules:
            if rule.get("tool") and rule["tool"] != request.tool_name:
                continue
            if rule.get("param"):
                param_value = request.arguments.get(rule["param"])
                if param_value is None:
                    continue
                if rule.get("pattern") and isinstance(param_value, str):
                    if rule["pattern"] not in param_value:
                        continue

            override = rule.get("result")
            if override:
                result = Permission(override)
                break

        return PermissionResult(
            permission=result,
            route="risk",
            reason=f"Risk level: {request.risk_level.value}",
        )


# ═══════════════════════════════════════════════════════════════
# Route 3: 用户确认（占位）
# ═══════════════════════════════════════════════════════════════

class UserConfirm:
    """
    用户确认
    同步模式：终端提示
    异步模式：推送通知
    超时默认：deny（安全优先）
    """

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._confirm_handler: Optional[Callable] = None

    def set_handler(self, handler: Callable):
        """设置确认回调"""
        self._confirm_handler = handler

    async def confirm(self, request: PermissionRequest) -> PermissionResult:
        """请求用户确认"""
        if self._confirm_handler:
            try:
                result = await self._confirm_handler(request)
                if result:
                    return PermissionResult(Permission.ALLOW, "user", "User approved")
                return PermissionResult(Permission.DENY, "user", "User denied")
            except Exception:
                return PermissionResult(Permission.DENY, "user", "User confirm error")
        # 无 handler → 超时 deny
        return PermissionResult(Permission.DENY, "user", "No confirm handler (timeout)")


# ═══════════════════════════════════════════════════════════════
# 权限竞速器
# ═══════════════════════════════════════════════════════════════

class PermissionRacer:
    """
    3 层权限竞速系统
    竞速规则：
      任何 Route 返回 deny → DENY
      所有 Route 返回 allow → ALLOW
      混合 → CONFIRM
    """

    def __init__(self):
        self.policy = PolicyEngine()
        self.risk = RiskClassifier()
        self.user = UserConfirm()

    async def check(self, request: PermissionRequest) -> PermissionResult:
        """执行权限检查"""
        # Route 1: 策略引擎（同步）
        policy_result = self.policy.evaluate(request)
        if policy_result.permission == Permission.DENY:
            return policy_result

        # Route 2: 风险分类器（同步）
        risk_result = self.risk.classify(request)
        if risk_result.permission == Permission.DENY:
            return risk_result

        # Route 3: 用户确认（异步，仅在需要时）
        if risk_result.permission == Permission.CONFIRM:
            user_result = await self.user.confirm(request)
            return user_result

        # 全部 allow
        return PermissionResult(Permission.ALLOW, "all", "All routes allow")
