"""安全模块 - 设备认证/访问控制/加密"""
import hashlib
import secrets
import logging
from typing import Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_DIR = Path.home() / ".remoteeye"
PIN_FILE = CONFIG_DIR / "pin.json"
SESSION_LOG = CONFIG_DIR / "sessions.log"


def ensure_config_dir():
    """确保配置目录存在"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


class SecurityManager:
    """安全管理器"""
    
    def __init__(self):
        ensure_config_dir()
        self.pins = self._load_pins()
        self.active_sessions = {}
        self.session_history = []
        logger.info(f"🔒 安全模块初始化: {len(self.pins)} 个访问码")
    
    def _load_pins(self) -> dict:
        """加载访问码"""
        if PIN_FILE.exists():
            try:
                with open(PIN_FILE) as f:
                    data = json.load(f)
                return data.get("pins", {})
            except Exception:
                pass
        return {}
    
    def _save_pins(self):
        """保存访问码"""
        with open(PIN_FILE, "w") as f:
            json.dump({"pins": self.pins}, f, indent=2)
        PIN_FILE.chmod(0o600)  # 仅所有者可读写
    
    def set_pin(self, pin: str, permanent: bool = True):
        """设置访问码"""
        if not pin or len(pin) < 4:
            raise ValueError("访问码至少 4 位")
        
        self.pins[pin] = {
            "permanent": permanent,
            "created_at": datetime.now().isoformat(),
            "used_count": 0
        }
        self._save_pins()
        logger.info(f"🔑 访问码已设置: {'*' * len(pin)}")
    
    def verify_pin(self, pin: str) -> bool:
        """验证访问码"""
        if pin in self.pins:
            self.pins[pin]["used_count"] += 1
            self._save_pins()
            return True
        return False
    
    def generate_temp_pin(self, expires_minutes: int = 30) -> str:
        """生成临时访问码"""
        pin = secrets.token_hex(3).upper()  # 6 位
        self.pins[pin] = {
            "permanent": False,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=expires_minutes)).isoformat(),
            "used_count": 0
        }
        self._save_pins()
        return pin
    
    def create_session(self, session_id: str, device_id: str, pin_used: str, controller_ip: str) -> dict:
        """记录控制会话"""
        session = {
            "session_id": session_id,
            "device_id": device_id,
            "pin_used": "*" * len(pin_used),
            "controller_ip": controller_ip,
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "duration": None
        }
        self.active_sessions[session_id] = session
        self.session_history.append(session)
        self._log_session(session)
        return session
    
    def end_session(self, session_id: str):
        """结束控制会话"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            started = datetime.fromisoformat(session["started_at"])
            duration = (datetime.now() - started).total_seconds()
            session["ended_at"] = datetime.now().isoformat()
            session["duration"] = round(duration, 1)
            del self.active_sessions[session_id]
            logger.info(f"🔒 会话结束: {session_id} (持续 {duration:.0f} 秒)")
    
    def _log_session(self, session: dict):
        """写入会话日志"""
        try:
            with open(SESSION_LOG, "a") as f:
                f.write(json.dumps(session, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"写入会话日志失败: {e}")
    
    def get_session_history(self, limit: int = 20) -> list:
        """获取会话历史"""
        return self.session_history[-limit:]
    
    def list_pins(self) -> list:
        """列出所有访问码（隐藏实际值）"""
        return [
            {
                "pin": "*" * len(k),
                "permanent": v["permanent"],
                "created_at": v["created_at"],
                "used_count": v["used_count"],
                "expires_at": v.get("expires_at")
            }
            for k, v in self.pins.items()
        ]


class CryptoHelper:
    """简易加密辅助"""
    
    @staticmethod
    def hash_token(token: str) -> str:
        """SHA-256 哈希"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    @staticmethod
    def generate_token() -> str:
        """生成安全令牌"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def xor_encrypt(data: bytes, key: bytes) -> bytes:
        """简易 XOR 加密（用于低开销场景）"""
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
