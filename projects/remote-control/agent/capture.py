"""屏幕捕获模块 - 高性能截屏"""
import logging
from typing import Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)


class ScreenCapturer:
    """屏幕捕获器"""
    
    def __init__(self, monitor: int = 0):
        self.monitor = monitor
        self._sct = None
        self._init()
    
    def _init(self):
        """初始化 mss"""
        try:
            from mss import mss
            self._sct = mss()
            logger.info(f"✅ mss 初始化成功")
        except Exception as e:
            logger.error(f"mss 初始化失败: {e}")
            raise
    
    def capture(self, max_width: int = 1920) -> Optional[Image.Image]:
        """捕获屏幕并返回 PIL Image"""
        try:
            monitor = self._sct.monitors[self.monitor]
            sct_img = self._sct.grab(monitor)
            
            # 转换为 PIL Image
            img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
            
            # 缩放（如果超过最大宽度）
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)
            
            return img
        except Exception as e:
            logger.error(f"截屏失败: {e}")
            return None
    
    def get_resolution(self) -> str:
        """获取当前分辨率"""
        try:
            monitor = self._sct.monitors[self.monitor]
            return f"{monitor['width']}x{monitor['height']}"
        except Exception:
            return "unknown"
    
    def list_monitors(self) -> list:
        """列出所有显示器"""
        try:
            return [
                f"Monitor {i}: {m['width']}x{m['height']}"
                for i, m in enumerate(self._sct.monitors)
                if i > 0  # 跳过全显示器合并
            ]
        except Exception:
            return []
