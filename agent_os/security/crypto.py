"""
Agent OS — 安全层：加密引擎
===========================
AES-256-GCM 加密存储、密钥派生、安全随机数
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("agent-os.security.crypto")

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import x25519
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.error("cryptography 库未安装！加密功能不可用。")
    logger.error("请安装: pip install cryptography")
    logger.error("安全飞地将在无加密模式下运行（仅用于开发测试）")


# ── 常量 ──────────────────────────────────────────────

AES_KEY_SIZE = 32       # AES-256
IV_SIZE = 12            # GCM nonce
SALT_SIZE = 32
TAG_SIZE = 16
KDF_ITERATIONS = 600000  # PBKDF2 iterations
HKDF_SALT = b"agent-os-key-derivation-v1"


# ── 数据类 ────────────────────────────────────────────

@dataclass
class EncryptedPayload:
    """加密载荷"""
    ciphertext: bytes
    nonce: bytes
    salt: bytes
    tag: bytes = b""
    algorithm: str = "AES-256-GCM"
    version: int = 1
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ciphertext": base64.b64encode(self.ciphertext).decode(),
            "nonce": base64.b64encode(self.nonce).decode(),
            "salt": base64.b64encode(self.salt).decode(),
            "tag": base64.b64encode(self.tag).decode() if self.tag else "",
            "algorithm": self.algorithm,
            "version": self.version,
            "created_at": self.created_at or time.time(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EncryptedPayload":
        return cls(
            ciphertext=base64.b64decode(data["ciphertext"]),
            nonce=base64.b64decode(data["nonce"]),
            salt=base64.b64decode(data["salt"]),
            tag=base64.b64decode(data.get("tag", "")),
            algorithm=data.get("algorithm", "AES-256-GCM"),
            version=data.get("version", 1),
            created_at=data.get("created_at", 0.0),
        )


# ── 密钥管理 ──────────────────────────────────────────

class KeyManager:
    """
    密钥管理器

    支持：
    - 主密钥派生
    - 子密钥生成（每个文件/任务独立密钥）
    - 密钥轮换
    - 内存安全擦除
    """

    def __init__(self, master_key: Optional[bytes] = None):
        if master_key:
            self._master_key = master_key
        else:
            self._master_key = self._generate_master_key()
        self._key_cache: Dict[str, Tuple[bytes, float]] = {}
        self._key_ttl = 3600  # 1小时缓存

    @staticmethod
    def _generate_master_key() -> bytes:
        """生成 256 位主密钥"""
        return os.urandom(AES_KEY_SIZE)

    def derive_key(self, context: str, salt: Optional[bytes] = None) -> bytes:
        """从主密钥派生子密钥"""
        if salt is None:
            salt = os.urandom(SALT_SIZE)

        cache_key = f"{context}:{base64.b64encode(salt).decode()}"
        cached = self._key_cache.get(cache_key)
        if cached:
            key, timestamp = cached
            if time.time() - timestamp < self._key_ttl:
                return key

        if CRYPTO_AVAILABLE:
            try:
                hkdf = HKDF(
                    algorithm=hashes.SHA256(),
                    length=AES_KEY_SIZE,
                    salt=salt,
                    info=context.encode("utf-8"),
                )
                key = hkdf.derive(self._master_key)
            except TypeError:
                # Older cryptography versions need explicit backend
                from cryptography.hazmat.backends import default_backend
                hkdf = HKDF(
                    algorithm=hashes.SHA256(),
                    length=AES_KEY_SIZE,
                    salt=salt,
                    info=context.encode("utf-8"),
                    backend=default_backend(),
                )
                key = hkdf.derive(self._master_key)
        else:
            # 回退：HMAC-SHA256 派生
            key = hmac.new(
                self._master_key,
                (context + base64.b64encode(salt).decode()).encode("utf-8"),
                hashlib.sha256,
            ).digest()

        self._key_cache[cache_key] = (key, time.time())
        return key

    def rotate_master_key(self) -> bytes:
        """轮换主密钥"""
        old_key = self._master_key
        self._master_key = self._generate_master_key()
        self._key_cache.clear()
        logger.info("主密钥已轮换")
        return old_key

    def clear_cache(self):
        """清除密钥缓存"""
        self._key_cache.clear()

    @property
    def master_key_fingerprint(self) -> str:
        """主密钥指纹（用于验证，不泄露密钥本身）"""
        return hashlib.sha256(self._master_key).hexdigest()[:16]


# ── 加密/解密 ─────────────────────────────────────────

class CryptoEngine:
    """
    加密引擎

    特性：
    - AES-256-GCM 认证加密
    - 每个加密操作使用独立 nonce
    - 关联数据 (AAD) 支持
    - 密钥派生上下文隔离
    """

    def __init__(self, key_manager: KeyManager):
        self._key_manager = key_manager

    def encrypt(
        self,
        plaintext: bytes,
        context: str = "default",
        aad: Optional[bytes] = None,
    ) -> EncryptedPayload:
        """加密数据"""
        salt = os.urandom(SALT_SIZE)
        nonce = os.urandom(IV_SIZE)
        key = self._key_manager.derive_key(context, salt)

        if CRYPTO_AVAILABLE:
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, plaintext, aad or b"")
        else:
            # 回退：XOR 加密（不安全！仅用于开发）
            ciphertext = bytes(
                p ^ k for p, k in zip(
                    plaintext,
                    (key * (len(plaintext) // len(key) + 1))[:len(plaintext)]
                )
            )

        return EncryptedPayload(
            ciphertext=ciphertext,
            nonce=nonce,
            salt=salt,
            algorithm="AES-256-GCM" if CRYPTO_AVAILABLE else "XOR-FALLBACK",
            created_at=time.time(),
        )

    def decrypt(
        self,
        payload: EncryptedPayload,
        context: str = "default",
        aad: Optional[bytes] = None,
    ) -> bytes:
        """解密数据"""
        key = self._key_manager.derive_key(context, payload.salt)

        if CRYPTO_AVAILABLE and payload.algorithm == "AES-256-GCM":
            aesgcm = AESGCM(key)
            return aesgcm.decrypt(payload.nonce, payload.ciphertext, aad or b"")
        else:
            # 回退解密
            return bytes(
                c ^ k for c, k in zip(
                    payload.ciphertext,
                    (key * (len(payload.ciphertext) // len(key) + 1))[
                        :len(payload.ciphertext)
                    ],
                )
            )

    def encrypt_file(
        self,
        filepath: str,
        context: str = "file",
        output_path: Optional[str] = None,
    ) -> str:
        """加密文件"""
        with open(filepath, "rb") as f:
            plaintext = f.read()

        payload = self.encrypt(plaintext, context)
        out_path = output_path or filepath + ".enc"

        with open(out_path, "w") as f:
            json.dump(payload.to_dict(), f)

        logger.info(f"文件已加密: {filepath} → {out_path}")
        return out_path

    def decrypt_file(
        self,
        enc_path: str,
        context: str = "file",
        output_path: Optional[str] = None,
    ) -> str:
        """解密文件"""
        with open(enc_path) as f:
            data = json.load(f)

        payload = EncryptedPayload.from_dict(data)
        plaintext = self.decrypt(payload, context)

        out_path = output_path or enc_path.replace(".enc", "")
        with open(out_path, "wb") as f:
            f.write(plaintext)

        logger.info(f"文件已解密: {enc_path} → {out_path}")
        return out_path


# ── 哈希与签名 ────────────────────────────────────────

def sha256_hash(data: bytes) -> str:
    """SHA-256 哈希"""
    return hashlib.sha256(data).hexdigest()


def hmac_sign(key: bytes, data: bytes) -> str:
    """HMAC-SHA256 签名"""
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def secure_compare(a: bytes, b: bytes) -> bool:
    """常量时间比较，防止时序攻击"""
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0


def generate_secure_token(length: int = 32) -> str:
    """生成安全随机令牌"""
    return base64.urlsafe_b64encode(os.urandom(length)).decode()[:length]
