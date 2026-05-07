"""键鼠输入控制模块"""
import logging
from pynput import mouse, keyboard

logger = logging.getLogger(__name__)


class InputController:
    """键盘和鼠标输入控制器"""
    
    def __init__(self):
        self.mouse_ctrl = mouse.Controller()
        self.keyboard_ctrl = keyboard.Controller()
        logger.info("✅ 键鼠控制器初始化成功")
    
    def mouse_move(self, x: int, y: int):
        """移动鼠标到指定位置"""
        try:
            self.mouse_ctrl.position = (x, y)
        except Exception as e:
            logger.error(f"鼠标移动失败: {e}")
    
    def mouse_click(self, x: int, y: int, button: str = "left"):
        """在指定位置点击鼠标"""
        try:
            self.mouse_ctrl.position = (x, y)
            
            if button == "left":
                btn = mouse.Button.left
            elif button == "right":
                btn = mouse.Button.right
            else:
                btn = mouse.Button.middle
            
            self.mouse_ctrl.click(btn, 1)
        except Exception as e:
            logger.error(f"鼠标点击失败: {e}")
    
    def mouse_scroll(self, delta: int):
        """滚动鼠标滚轮"""
        try:
            self.mouse_ctrl.scroll(0, delta)
        except Exception as e:
            logger.error(f"鼠标滚动失败: {e}")
    
    def key_press(self, key: str):
        """按下键盘按键"""
        try:
            k = self._parse_key(key)
            self.keyboard_ctrl.press(k)
        except Exception as e:
            logger.error(f"按键按下失败: {e}")
    
    def key_release(self, key: str):
        """释放键盘按键"""
        try:
            k = self._parse_key(key)
            self.keyboard_ctrl.release(k)
        except Exception as e:
            logger.error(f"按键释放失败: {e}")
    
    def type_text(self, text: str):
        """输入文本"""
        try:
            self.keyboard_ctrl.type(text)
        except Exception as e:
            logger.error(f"文本输入失败: {e}")
    
    def _parse_key(self, key: str):
        """解析按键字符串为 pynput 按键对象"""
        # 特殊按键映射
        special_keys = {
            "enter": keyboard.Key.enter,
            "tab": keyboard.Key.tab,
            "backspace": keyboard.Key.backspace,
            "delete": keyboard.Key.delete,
            "escape": keyboard.Key.esc,
            "esc": keyboard.Key.esc,
            "space": keyboard.Key.space,
            "shift": keyboard.Key.shift,
            "ctrl": keyboard.Key.ctrl,
            "alt": keyboard.Key.alt,
            "cmd": keyboard.Key.cmd,
            "up": keyboard.Key.up,
            "down": keyboard.Key.down,
            "left": keyboard.Key.left,
            "right": keyboard.Key.right,
            "home": keyboard.Key.home,
            "end": keyboard.Key.end,
            "page_up": keyboard.Key.page_up,
            "page_down": keyboard.Key.page_down,
            "caps_lock": keyboard.Key.caps_lock,
            "f1": keyboard.Key.f1,
            "f2": keyboard.Key.f2,
            "f3": keyboard.Key.f3,
            "f4": keyboard.Key.f4,
            "f5": keyboard.Key.f5,
            "f6": keyboard.Key.f6,
            "f7": keyboard.Key.f7,
            "f8": keyboard.Key.f8,
            "f9": keyboard.Key.f9,
            "f10": keyboard.Key.f10,
            "f11": keyboard.Key.f11,
            "f12": keyboard.Key.f12,
        }
        
        key_lower = key.lower()
        if key_lower in special_keys:
            return special_keys[key_lower]
        
        # 普通字符
        return key
