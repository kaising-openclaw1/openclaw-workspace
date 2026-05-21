"""端到端加密模块 - AES-256-GCM 加密通信"""
import logging
import os
import base64
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    logger.warning("cryptography 未安装，加密功能不可用")


class E2ECrypto:
    """端到端加密 - AES-256-GCM
    
    使用共享密钥对 WebSocket 消息进行加密，
    防止中间人窃听远程控制数据。
    """
    
    def __init__(self, shared_secret: Optional[bytes] = None):
        if not HAS_CRYPTO:
            self.enabled = False
            logger.warning("⚠️ E2E 加密不可用（缺少 cryptography 库）")
            return
        
        self.enabled = True
        if shared_secret is None:
            shared_secret = os.urandom(32)
        
        # 从共享密钥派生出加密密钥
        self._encryption_key = self._derive_key(shared_secret, b"remote-eye-encryption")
        # 派生出 MAC 密钥
        self._mac_key = self._derive_key(shared_secret, b"remote-eye-mac")
        
        logger.info("🔐 E2E 加密已启用 (AES-256-GCM)")
    
    def _derive_key(self, secret: bytes, info: bytes) -> bytes:
        """使用 HKDF 从共享密钥派生子密钥"""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=info
        )
        return hkdf.derive(secret)
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """加密数据
        
        返回: nonce + ciphertext (nonce 是 12 字节)
        """
        if not self.enabled:
            return plaintext
        
        aesgcm = AESGCM(self._encryption_key)
        nonce = os.urandom(12)  # GCM 推荐 12 字节 nonce
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext
    
    def decrypt(self, encrypted: bytes) -> bytes:
        """解密数据
        
        输入: nonce (12 bytes) + ciphertext
        """
        if not self.enabled:
            return encrypted
        
        if len(encrypted) < 12:
            raise ValueError("加密数据太短")
        
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        
        aesgcm = AESGCM(self._encryption_key)
        return aesgcm.decrypt(nonce, ciphertext, None)
    
    def encrypt_json(self, data: dict) -> bytes:
        """加密 JSON 数据"""
        import json
        plaintext = json.dumps(data, separators=(',', ':')).encode('utf-8')
        return self.encrypt(plaintext)
    
    def decrypt_json(self, encrypted: bytes) -> dict:
        """解密 JSON 数据"""
        import json
        plaintext = self.decrypt(encrypted)
        return json.loads(plaintext.decode('utf-8'))
    
    def get_shared_secret(self) -> bytes:
        """获取共享密钥（用于传输给对方）"""
        # 从加密密钥重新生成共享密钥（实际应用中应使用密钥交换协议）
        return self._derive_key(self._encryption_key, b"remote-eye-shared")
    
    @staticmethod
    def generate_shared_secret() -> bytes:
        """生成新的共享密钥"""
        return os.urandom(32)


class KeyExchange:
    """简易密钥交换 - Diffie-Hellman 风格
    
    实际生产环境应使用完整的 DH 密钥交换或 TLS 握手。
    这里使用预共享密钥 + nonce 的简化方案。
    """
    
    @staticmethod
    def create_session_key(pin: str, device_id: str) -> bytes:
        """从 PIN 码和设备 ID 创建会话密钥"""
        import hashlib
        material = f"{pin}:{device_id}".encode('utf-8')
        return hashlib.sha256(material).digest()
    
    @staticmethod
    def verify_pin(stored_hash: bytes, provided_pin: str, device_id: str) -> bool:
        """验证 PIN 码"""
        computed = KeyExchange.create_session_key(provided_pin, device_id)
        return computed == stored_hash
