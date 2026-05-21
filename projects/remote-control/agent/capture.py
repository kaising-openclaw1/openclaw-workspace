"""屏幕捕获模块 - 高性能截屏 + 多显示器支持"""
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
            logger.info(f"✅ mss 初始化成功，显示器数: {len(self._sct.monitors) - 1}")
        except Exception as e:
            logger.error(f"mss 初始化失败: {e}")
            raise
    
    def switch_monitor(self, monitor_idx: int):
        """切换到指定显示器"""
        if monitor_idx < len(self._sct.monitors):
            self.monitor = monitor_idx
            res = self.get_resolution()
            logger.info(f"🖥️ 切换到显示器 {monitor_idx}: {res}")
        else:
            logger.warning(f"显示器 {monitor_idx} 不存在，可用: 0-{len(self._sct.monitors)-1}")
    
    def capture(self, max_width: int = 1920) -> Optional[Image.Image]:
        """捕获屏幕并返回 PIL Image"""
        try:
            if self.monitor >= len(self._sct.monitors):
                self.monitor = 0  # 回退到主显示器
            
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
        """获取当前显示器分辨率"""
        try:
            if self.monitor >= len(self._sct.monitors):
                return "unknown"
            monitor = self._sct.monitors[self.monitor]
            return f"{monitor['width']}x{monitor['height']}"
        except Exception:
            return "unknown"
    
    def list_monitors(self) -> list:
        """列出所有显示器"""
        try:
            monitors = []
            for i, m in enumerate(self._sct.monitors):
                if i == 0:
                    continue  # 跳过全显示器合并
                monitors.append({
                    "index": i,
                    "width": m['width'],
                    "height": m['height'],
                    "label": f"显示器 {i}: {m['width']}x{m['height']}"
                })
            return monitors
        except Exception:
            return []
