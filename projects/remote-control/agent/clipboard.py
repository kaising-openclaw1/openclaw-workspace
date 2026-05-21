"""剪贴板同步模块 - 双向剪贴板共享"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ClipboardSync:
    """剪贴板同步控制器"""
    
    def __init__(self):
        self._last_synced = None
        self._pyperclip = None
        self._init()
    
    def _init(self):
        """初始化剪贴板模块"""
        try:
            import pyperclip
            self._pyperclip = pyperclip
            logger.info("✅ 剪贴板模块初始化成功")
        except ImportError:
            logger.warning("pyperclip 未安装，尝试备用方案")
            self._init_fallback()
    
    def _init_fallback(self):
        """备用剪贴板方案（平台特定）"""
        import platform
        system = platform.system()
        
        if system == "Linux":
            try:
                import subprocess
                self._get_cmd = ["xclip", "-selection", "clipboard", "-o"]
                self._set_cmd = ["xclip", "-selection", "clipboard", "-i"]
                self._mode = "xclip"
                logger.info("✅ 使用 xclip 作为剪贴板后端")
            except Exception:
                try:
                    self._get_cmd = ["xsel", "--clipboard", "--output"]
                    self._set_cmd = ["xsel", "--clipboard", "--input"]
                    self._mode = "xsel"
                    logger.info("✅ 使用 xsel 作为剪贴板后端")
                except Exception:
                    self._mode = None
                    logger.warning("无可用剪贴板后端")
        elif system == "Darwin":
            import subprocess
            self._mode = "subprocess"
            logger.info("✅ 使用 pbcopy/pbpaste 作为剪贴板后端")
        else:
            self._mode = None
            logger.warning(f"不支持的剪贴板后端: {system}")
    
    def get_text(self) -> Optional[str]:
        """获取剪贴板文本"""
        try:
            if self._pyperclip:
                return self._pyperclip.paste()
            elif self._mode in ("xclip", "xsel"):
                import subprocess
                result = subprocess.run(
                    self._get_cmd,
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                return result.stdout
            elif self._mode == "subprocess":
                import subprocess
                result = subprocess.run(
                    ["pbpaste"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                return result.stdout
        except Exception as e:
            logger.debug(f"获取剪贴板失败: {e}")
        return None
    
    def set_text(self, text: str) -> bool:
        """设置剪贴板文本"""
        try:
            if self._pyperclip:
                self._pyperclip.copy(text)
                return True
            elif self._mode in ("xclip", "xsel"):
                import subprocess
                subprocess.run(
                    self._set_cmd,
                    input=text,
                    text=True,
                    timeout=2
                )
                return True
            elif self._mode == "subprocess":
                import subprocess
                subprocess.run(
                    ["pbcopy"],
                    input=text,
                    text=True,
                    timeout=2
                )
                return True
        except Exception as e:
            logger.debug(f"设置剪贴板失败: {e}")
        return False
    
    def has_changed(self) -> Optional[str]:
        """检查剪贴板是否变化，返回新内容或 None"""
        current = self.get_text()
        if current and current != self._last_synced:
            self._last_synced = current
            return current
        return None
    
    def sync_from_remote(self, text: str):
        """从远程同步剪贴板"""
        self._last_synced = text
        self.set_text(text)
        logger.info(f"📋 剪贴板已同步 ({len(text)} 字符)")
