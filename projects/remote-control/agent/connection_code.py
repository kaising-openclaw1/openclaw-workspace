"""连接码系统 - 类似 TeamViewer 的 9 位数字连接码"""
import logging
import random
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ConnectionCodeManager:
    """连接码管理器"""
    
    def __init__(self):
        # code -> {"device_id": str, "device_name": str, "created_at": datetime, "expires_at": datetime}
        self.active_codes: Dict[str, dict] = {}
        self.code_length = 9
        self.code_ttl_minutes = 10
        logger.info(f"🔢 连接码系统初始化 (长度={self.code_length}, 有效期={self.code_ttl_minutes}分钟)")
    
    def generate_code(self, device_id: str, device_name: str) -> str:
        """为设备生成连接码"""
        # 清理过期码
        self._cleanup_expired()
        
        # 如果该设备已有有效码，返回旧码
        for code, info in self.active_codes.items():
            if info["device_id"] == device_id:
                return code
        
        # 生成新码
        while True:
            code = ''.join([str(random.randint(0, 9)) for _ in range(self.code_length)])
            if code not in self.active_codes:
                break
        
        now = datetime.now()
        self.active_codes[code] = {
            "device_id": device_id,
            "device_name": device_name,
            "created_at": now,
            "expires_at": now + timedelta(minutes=self.code_ttl_minutes),
            "used": False
        }
        
        logger.info(f"🔢 连接码生成: {code} → {device_name}")
        return code
    
    def resolve_code(self, code: str) -> Optional[dict]:
        """解析连接码，返回设备信息"""
        self._cleanup_expired()
        
        info = self.active_codes.get(code)
        if info:
            info["used"] = True
            return {
                "device_id": info["device_id"],
                "device_name": info["device_name"]
            }
        return None
    
    def invalidate_code(self, code: str):
        """使连接码失效"""
        if code in self.active_codes:
            del self.active_codes[code]
            logger.info(f"🔢 连接码已失效: {code}")
    
    def get_remaining_time(self, code: str) -> Optional[int]:
        """获取连接码剩余时间（秒）"""
        info = self.active_codes.get(code)
        if not info:
            return None
        remaining = (info["expires_at"] - datetime.now()).total_seconds()
        return max(0, int(remaining))
    
    def _cleanup_expired(self):
        """清理过期连接码"""
        now = datetime.now()
        expired = [c for c, info in self.active_codes.items() if info["expires_at"] < now]
        for code in expired:
            del self.active_codes[code]
            logger.debug(f"🔢 连接码过期: {code}")
