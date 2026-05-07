"""Agent 配置管理"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentConfig:
    """被控端配置"""
    server_url: str = "ws://localhost:8000/ws/agent"
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    quality: int = 75  # 截屏质量 1-100
    fps: int = 15  # 截帧率
    max_width: int = 1920  # 最大宽度（缩放）
    reconnect_interval: int = 5  # 重连间隔（秒）
    heartbeat_interval: int = 30  # 心跳间隔（秒）
    
    def validate(self):
        """验证配置"""
        if not self.server_url.startswith("ws://") and not self.server_url.startswith("wss://"):
            raise ValueError(f"无效的服务器地址: {self.server_url}")
        if not 1 <= self.quality <= 100:
            raise ValueError(f"质量必须在 1-100 之间: {self.quality}")
        if not 1 <= self.fps <= 60:
            raise ValueError(f"帧率必须在 1-60 之间: {self.fps}")
