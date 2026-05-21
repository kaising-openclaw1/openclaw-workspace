"""连接卡系统 - 类似 TeamViewer/向日葵的 ID + 密码模式"""
import logging
import random
import time
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ConnectionCard:
    """连接卡管理器 - 9位数字ID + 6位动态密码"""
    
    def __init__(self, ttl_minutes: int = 10):
        # code -> {"device_id": str, "device_name": str, "password": str, "expires_at": float}
        self.active_cards: Dict[str, dict] = {}
        self.ttl_minutes = ttl_minutes
        self._cleanup_task = None
        logger.info(f"🔢 连接卡系统初始化 (有效期={ttl_minutes}分钟)")
    
    def generate(self, device_id: str, device_name: str) -> tuple:
        """
        生成连接卡
        返回: (connection_id, password)
        """
        self._cleanup_expired()
        
        # 9位数字 ID
        conn_id = ''.join([str(random.randint(0, 9)) for _ in range(9)])
        # 6位数字密码
        password = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        self.active_cards[conn_id] = {
            "device_id": device_id,
            "device_name": device_name,
            "password": password,
            "created_at": time.time(),
            "expires_at": time.time() + (self.ttl_minutes * 60)
        }
        
        logger.info(f"🔢 连接卡: {conn_id} / {password} → {device_name}")
        return conn_id, password
    
    def verify(self, conn_id: str, password: str) -> Optional[str]:
        """验证连接卡，返回 device_id"""
        self._cleanup_expired()
        
        card = self.active_cards.get(conn_id)
        if card and card["password"] == password:
            return card["device_id"]
        return None
    
    def refresh(self, device_id: str) -> Optional[tuple]:
        """刷新连接卡"""
        # 清除该设备的旧卡
        for code in list(self.active_cards.keys()):
            if self.active_cards[code]["device_id"] == device_id:
                del self.active_cards[code]
        
        # 生成新卡
        device_name = None
        for card in self.active_cards.values():
            if card["device_id"] == device_id:
                device_name = card["device_name"]
                break
        
        if device_name:
            return self.generate(device_id, device_name)
        return None
    
    def get_remaining_time(self, conn_id: str) -> int:
        """获取剩余时间（秒）"""
        card = self.active_cards.get(conn_id)
        if not card:
            return 0
        return max(0, int(card["expires_at"] - time.time()))
    
    def _cleanup_expired(self):
        """清理过期连接卡"""
        now = time.time()
        expired = [c for c, info in self.active_cards.items() if info["expires_at"] < now]
        for code in expired:
            del self.active_cards[code]
