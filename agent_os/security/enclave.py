"""
Agent OS — 安全层：安全飞地
===========================
代码加密存储、运行时解密、访问控制、审计追踪
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

from .crypto import CryptoEngine, KeyManager, EncryptedPayload, generate_secure_token

logger = logging.getLogger("agent-os.security.enclave")


class AccessLevel(Enum):
    """访问级别"""
    DENIED = 0
    READ = 1
    WRITE = 2
    EXECUTE = 3
    ADMIN = 4


class AuditAction(Enum):
    """审计动作"""
    FILE_READ = auto()
    FILE_WRITE = auto()
    FILE_DELETE = auto()
    FILE_ENCRYPT = auto()
    FILE_DECRYPT = auto()
    CODE_EXECUTE = auto()
    ACCESS_GRANTED = auto()
    ACCESS_DENIED = auto()
    KEY_ROTATION = auto()
    CONFIG_CHANGE = auto()
    AGENT_SPAWN = auto()
    NETWORK_CONNECT = auto()


@dataclass
class AuditEntry:
    """审计条目"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    action: AuditAction = AuditAction.FILE_READ
    actor: str = ""
    resource: str = ""
    result: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "action": self.action.name,
            "actor": self.actor,
            "resource": self.resource,
            "result": self.result,
            "details": self.details,
            "trace_id": self.trace_id,
        }


@dataclass
class AccessPolicy:
    """访问策略"""
    subject: str           # 用户/Agent ID
    resource_pattern: str  # 资源路径模式（支持 glob）
    level: AccessLevel
    conditions: Dict[str, Any] = field(default_factory=dict)
    expires_at: float = 0.0  # 0 = 永不过期


class SecurityEnclave:
    """
    安全飞地

    核心职责：
    1. 代码加密存储（AES-256-GCM）
    2. 运行时按需解密
    3. 细粒度访问控制（RBAC）
    4. 全量审计追踪
    5. 密钥生命周期管理
    """

    def __init__(self, data_dir: str = ""):
        self._data_dir = data_dir or os.path.expanduser("~/.agent-os/enclave")
        os.makedirs(self._data_dir, exist_ok=True)
        os.makedirs(os.path.join(self._data_dir, "encrypted"), exist_ok=True)
        os.makedirs(os.path.join(self._data_dir, "audit"), exist_ok=True)
        os.makedirs(os.path.join(self._data_dir, "keys"), exist_ok=True)

        self._key_manager = KeyManager()
        self._crypto = CryptoEngine(self._key_manager)
        self._policies: List[AccessPolicy] = []
        self._audit_buffer: List[AuditEntry] = []
        self._audit_max_buffer = 100
        self._audit_file = os.path.join(self._data_dir, "audit", "audit.log")
        self._event_bus = None
        self._lock = None

        # 加载持久化策略
        self._load_policies()

    @property
    def crypto(self) -> CryptoEngine:
        return self._crypto

    @property
    def key_manager(self) -> KeyManager:
        return self._key_manager

    async def _ensure_lock(self):
        if self._lock is None:
            self._lock = asyncio.Lock()

    # ── 文件加密/解密 ─────────────────────────────────

    async def encrypt_source(
        self,
        source_path: str,
        context: str = "source_code",
        delete_original: bool = False,
    ) -> str:
        """加密源码文件"""
        enc_path = self._crypto.encrypt_file(
            source_path,
            context=context,
            output_path=os.path.join(
                self._data_dir, "encrypted",
                os.path.basename(source_path) + ".enc"
            ),
        )

        if delete_original:
            os.remove(source_path)

        await self._audit(
            AuditAction.FILE_ENCRYPT,
            actor="system",
            resource=source_path,
            details={"encrypted_path": enc_path},
        )

        return enc_path

    async def decrypt_source(
        self,
        enc_path: str,
        output_path: Optional[str] = None,
        actor: str = "system",
    ) -> Optional[str]:
        """解密源码到临时目录"""
        # 权限检查
        if not self._check_access(actor, enc_path, AccessLevel.READ):
            await self._audit(
                AuditAction.ACCESS_DENIED,
                actor=actor,
                resource=enc_path,
                details={"reason": "access_denied"},
            )
            logger.warning(f"访问被拒绝: {actor} → {enc_path}")
            return None

        try:
            out_path = self._crypto.decrypt_file(
                enc_path,
                context="source_code",
                output_path=output_path,
            )

            await self._audit(
                AuditAction.FILE_DECRYPT,
                actor=actor,
                resource=enc_path,
                details={"output": out_path},
            )

            return out_path
        except Exception as e:
            logger.error(f"解密失败: {enc_path}: {e}")
            return None

    async def decrypt_to_memory(
        self,
        enc_path: str,
        actor: str = "system",
    ) -> Optional[bytes]:
        """解密到内存（不写磁盘）"""
        if not self._check_access(actor, enc_path, AccessLevel.READ):
            await self._audit(
                AuditAction.ACCESS_DENIED,
                actor=actor,
                resource=enc_path,
            )
            return None

        try:
            with open(enc_path) as f:
                data = json.load(f)
            payload = EncryptedPayload.from_dict(data)
            plaintext = self._crypto.decrypt(payload, "source_code")

            await self._audit(
                AuditAction.FILE_DECRYPT,
                actor=actor,
                resource=enc_path,
                details={"mode": "memory"},
            )

            return plaintext
        except Exception as e:
            logger.error(f"内存解密失败: {e}")
            return None

    # ── 访问控制 ──────────────────────────────────────

    def add_policy(self, policy: AccessPolicy):
        """添加访问策略"""
        self._policies.append(policy)
        self._save_policies()
        logger.info(f"策略已添加: {policy.subject} → {policy.resource_pattern} ({policy.level.name})")

    def remove_policy(self, subject: str, resource_pattern: str) -> bool:
        """移除访问策略"""
        original = len(self._policies)
        self._policies = [
            p for p in self._policies
            if not (p.subject == subject and p.resource_pattern == resource_pattern)
        ]
        if len(self._policies) < original:
            self._save_policies()
            return True
        return False

    def _check_access(
        self, subject: str, resource: str, required_level: AccessLevel
    ) -> bool:
        """检查访问权限"""
        for policy in self._policies:
            if policy.subject != subject and policy.subject != "*":
                continue
            if not self._match_pattern(policy.resource_pattern, resource):
                continue
            if policy.expires_at > 0 and time.time() > policy.expires_at:
                continue
            if policy.level.value >= required_level.value:
                return True
        return False

    @staticmethod
    def _match_pattern(pattern: str, resource: str) -> bool:
        """简单的 glob 模式匹配"""
        if pattern == "*":
            return True
        if pattern.endswith("/*"):
            return resource.startswith(pattern[:-1])
        if pattern.endswith("/**"):
            return resource.startswith(pattern[:-3])
        return pattern == resource

    # ── 审计日志 ──────────────────────────────────────

    async def _audit(
        self,
        action: AuditAction,
        actor: str = "",
        resource: str = "",
        details: Dict[str, Any] = None,
    ):
        """记录审计事件"""
        entry = AuditEntry(
            action=action,
            actor=actor,
            resource=resource,
            result="success",
            details=details or {},
        )
        self._audit_buffer.append(entry)

        # 批量写入
        if len(self._audit_buffer) >= self._audit_max_buffer:
            await self._flush_audit()

        # 事件总线通知
        if self._event_bus:
            await self._event_bus.emit(
                "security.audit",
                payload=entry.to_dict(),
            )

    async def _flush_audit(self):
        """将审计缓冲区写入磁盘"""
        if not self._audit_buffer:
            return

        with open(self._audit_file, "a") as f:
            for entry in self._audit_buffer:
                f.write(json.dumps(entry.to_dict()) + "\n")

        self._audit_buffer.clear()

    async def query_audit(
        self,
        limit: int = 100,
        action: Optional[AuditAction] = None,
        actor: Optional[str] = None,
        since: float = 0.0,
    ) -> List[AuditEntry]:
        """查询审计日志"""
        entries = []
        try:
            with open(self._audit_file) as f:
                for line in f:
                    data = json.loads(line.strip())
                    entry = AuditEntry(
                        id=data["id"],
                        timestamp=data["timestamp"],
                        action=AuditAction[data["action"]],
                        actor=data["actor"],
                        resource=data["resource"],
                        result=data["result"],
                        details=data.get("details", {}),
                        trace_id=data.get("trace_id", ""),
                    )

                    if action and entry.action != action:
                        continue
                    if actor and entry.actor != actor:
                        continue
                    if since and entry.timestamp < since:
                        continue

                    entries.append(entry)
                    if len(entries) >= limit:
                        break
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        return entries

    # ── 持久化 ────────────────────────────────────────

    def _save_policies(self):
        """保存策略到磁盘"""
        path = os.path.join(self._data_dir, "policies.json")
        data = [
            {
                "subject": p.subject,
                "resource_pattern": p.resource_pattern,
                "level": p.level.name,
                "conditions": p.conditions,
                "expires_at": p.expires_at,
            }
            for p in self._policies
        ]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_policies(self):
        """从磁盘加载策略"""
        path = os.path.join(self._data_dir, "policies.json")
        try:
            with open(path) as f:
                data = json.load(f)
            for item in data:
                self._policies.append(AccessPolicy(
                    subject=item["subject"],
                    resource_pattern=item["resource_pattern"],
                    level=AccessLevel[item["level"]],
                    conditions=item.get("conditions", {}),
                    expires_at=item.get("expires_at", 0.0),
                ))
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus

    async def shutdown(self):
        """安全关闭"""
        await self._flush_audit()
        self._key_manager.clear_cache()
        logger.info("安全飞地已关闭")
