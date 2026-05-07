"""被控端 Agent - 截屏 + 键鼠控制"""
import asyncio
import json
import logging
import socket
import time
from typing import Optional
import uuid

import websockets
from mss import mss
from PIL import Image
import io

from capture import ScreenCapturer
from input import InputController
from config import AgentConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('agent')


class RemoteAgent:
    """远程控制被控端"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.device_id = config.device_id or str(uuid.uuid4())[:8]
        self.device_name = config.device_name or socket.gethostname()
        self.server_url = config.server_url
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.capturer = ScreenCapturer()
        self.input_ctrl = InputController()
        self.connected = False
        self.session_id: Optional[str] = None
        self.is_controlled = False
        
        # 截屏参数
        self.quality = 75
        self.fps = 15
        self.max_width = 1920
        
    async def connect(self):
        """连接到信令服务器"""
        try:
            logger.info(f"正在连接服务器: {self.server_url}")
            self.ws = await websockets.connect(
                self.server_url,
                ping_interval=20,
                ping_timeout=10
            )
            self.connected = True
            logger.info(f"✅ 已连接服务器")
            
            # 注册设备
            await self.register()
            
            # 开始接收控制指令
            await self.listen()
            
        except Exception as e:
            logger.error(f"连接失败: {e}")
            self.connected = False
            raise
    
    async def register(self):
        """向服务器注册设备"""
        msg = {
            "type": "register",
            "device_id": self.device_id,
            "device_name": self.device_name,
            "platform": self._get_platform(),
            "resolution": self.capturer.get_resolution()
        }
        await self.ws.send(json.dumps(msg))
        logger.info(f"📝 设备已注册: {self.device_name} ({self.device_id})")
    
    async def listen(self):
        """监听控制指令"""
        logger.info("👂 开始监听控制指令...")
        
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    if msg_type == "control_start":
                        await self._handle_control_start(data)
                    elif msg_type == "control_stop":
                        await self._handle_control_stop()
                    elif msg_type == "input":
                        await self._handle_input(data)
                    elif msg_type == "screenshot_request":
                        await self._handle_screenshot_request(data)
                    elif msg_type == "ping":
                        await self.ws.send(json.dumps({"type": "pong"}))
                    elif msg_type == "session_end":
                        await self._handle_control_stop()
                        
                except json.JSONDecodeError:
                    logger.warning(f"无效消息: {message[:100]}")
                except Exception as e:
                    logger.error(f"处理消息出错: {e}")
                    
        except websockets.ConnectionClosed:
            logger.warning("连接已关闭")
            self.connected = False
        except Exception as e:
            logger.error(f"监听异常: {e}")
            self.connected = False
    
    async def _handle_control_start(self, data: dict):
        """开始被控制"""
        self.session_id = data.get("session_id")
        self.is_controlled = True
        self.quality = data.get("quality", 75)
        self.fps = data.get("fps", 15)
        logger.info(f"🎮 开始被控制 (session: {self.session_id})")
        
        # 启动截屏推流
        asyncio.create_task(self._stream_screenshots())
    
    async def _handle_control_stop(self):
        """停止被控制"""
        self.is_controlled = False
        self.session_id = None
        logger.info("⏹️ 控制已结束")
    
    async def _handle_input(self, data: dict):
        """处理输入事件"""
        action = data.get("action")
        
        if action == "mouse_move":
            self.input_ctrl.mouse_move(data["x"], data["y"])
        elif action == "mouse_click":
            self.input_ctrl.mouse_click(data["x"], data["y"], data.get("button", "left"))
        elif action == "mouse_scroll":
            self.input_ctrl.mouse_scroll(data["delta"])
        elif action == "key_press":
            self.input_ctrl.key_press(data["key"])
        elif action == "key_release":
            self.input_ctrl.key_release(data["key"])
        elif action == "type":
            self.input_ctrl.type_text(data["text"])
    
    async def _handle_screenshot_request(self, data: dict):
        """处理截屏请求"""
        screenshot = await self._capture_screen()
        if screenshot:
            msg = {
                "type": "screenshot",
                "data": screenshot,
                "session_id": data.get("session_id"),
                "timestamp": time.time()
            }
            await self.ws.send(json.dumps(msg))
    
    async def _stream_screenshots(self):
        """持续截屏并推流"""
        interval = 1.0 / self.fps
        
        while self.is_controlled:
            try:
                start = time.time()
                screenshot = await self._capture_screen()
                
                if screenshot:
                    msg = {
                        "type": "screenshot",
                        "data": screenshot,
                        "session_id": self.session_id,
                        "timestamp": time.time()
                    }
                    await self.ws.send(json.dumps(msg))
                
                # 控制帧率
                elapsed = time.time() - start
                if elapsed < interval:
                    await asyncio.sleep(interval - elapsed)
                    
            except Exception as e:
                logger.error(f"截屏推流错误: {e}")
                await asyncio.sleep(1)
    
    async def _capture_screen(self) -> Optional[str]:
        """截屏并编码为 base64"""
        try:
            img = self.capturer.capture(max_width=self.max_width)
            if img is None:
                return None
            
            # 编码为 JPEG
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=self.quality, optimize=True)
            import base64
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            logger.error(f"截屏失败: {e}")
            return None
    
    def _get_platform(self) -> str:
        """获取平台信息"""
        import platform
        return f"{platform.system()} {platform.release()}"
    
    async def close(self):
        """关闭连接"""
        self.is_controlled = False
        if self.ws:
            await self.ws.close()
        logger.info("🔌 已断开连接")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='RemoteEye Agent')
    parser.add_argument('--server', default='ws://localhost:8000/ws/agent', help='信令服务器地址')
    parser.add_argument('--device-name', default=None, help='设备名称')
    parser.add_argument('--device-id', default=None, help='设备ID')
    parser.add_argument('--quality', type=int, default=75, help='截屏质量 (1-100)')
    parser.add_argument('--fps', type=int, default=15, help='截帧率')
    args = parser.parse_args()
    
    config = AgentConfig(
        server_url=args.server,
        device_name=args.device_name,
        device_id=args.device_id,
        quality=args.quality,
        fps=args.fps
    )
    
    agent = RemoteAgent(config)
    
    try:
        await agent.connect()
    except KeyboardInterrupt:
        logger.info("收到退出信号")
    finally:
        await agent.close()


if __name__ == '__main__':
    asyncio.run(main())
