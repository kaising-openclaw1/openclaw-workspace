"""信令服务器 - FastAPI + WebSocket"""
import asyncio
import json
import logging
import time
from typing import Dict, Optional, Set
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('server')

app = FastAPI(title="RemoteEye Signaling Server", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设备管理器
class DeviceManager:
    """管理在线设备和 WebSocket 连接"""
    
    def __init__(self):
        # device_id -> {"ws": WebSocket, "name": str, "platform": str, "connected_at": float}
        self.devices: Dict[str, dict] = {}
        # session_id -> {"controller_ws": WebSocket, "agent_ws": WebSocket, "started_at": float}
        self.sessions: Dict[str, dict] = {}
        # WebSocket -> device_id 反向映射
        self.ws_to_device: Dict[WebSocket, str] = {}
    
    def register_device(self, ws: WebSocket, device_id: str, name: str, platform: str, resolution: str):
        """注册设备"""
        self.devices[device_id] = {
            "ws": ws,
            "name": name,
            "platform": platform,
            "resolution": resolution,
            "connected_at": time.time(),
            "is_controlled": False
        }
        self.ws_to_device[ws] = device_id
        logger.info(f"📱 设备注册: {name} ({device_id})")
    
    def unregister_device(self, ws: WebSocket):
        """注销设备"""
        device_id = self.ws_to_device.pop(ws, None)
        if device_id and device_id in self.devices:
            del self.devices[device_id]
            logger.info(f"📴 设备离线: {device_id}")
    
    def get_device(self, device_id: str) -> Optional[dict]:
        """获取设备信息"""
        return self.devices.get(device_id)
    
    def list_devices(self) -> list:
        """列出所有在线设备"""
        return [
            {
                "device_id": did,
                "name": info["name"],
                "platform": info["platform"],
                "resolution": info["resolution"],
                "online": True,
                "is_controlled": info["is_controlled"],
                "connected_at": info["connected_at"]
            }
            for did, info in self.devices.items()
        ]
    
    def create_session(self, session_id: str, controller_ws: WebSocket, agent_ws: WebSocket):
        """创建控制会话"""
        self.sessions[session_id] = {
            "controller_ws": controller_ws,
            "agent_ws": agent_ws,
            "started_at": time.time()
        }
        logger.info(f"🎮 会话创建: {session_id}")
    
    def close_session(self, session_id: str):
        """关闭控制会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"⏹️ 会话关闭: {session_id}")


device_manager = DeviceManager()


# ==================== API 路由 ====================

@app.get("/")
async def index():
    """Web 主控端主页"""
    return FileResponse("web/templates/index.html")


@app.get("/api/devices")
async def list_devices():
    """列出所有在线设备"""
    return {"devices": device_manager.list_devices()}


@app.get("/api/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "devices_online": len(device_manager.devices),
        "active_sessions": len(device_manager.sessions)
    }


# ==================== WebSocket 路由 ====================

@app.websocket("/ws/agent")
async def agent_endpoint(ws: WebSocket):
    """被控端 Agent 连接入口"""
    await ws.accept()
    logger.info("🔗 Agent WebSocket 已连接")
    
    try:
        # 等待注册消息
        data = await asyncio.wait_for(ws.receive_text(), timeout=30)
        msg = json.loads(data)
        
        if msg.get("type") != "register":
            await ws.close(code=1008, reason="需要发送 register 消息")
            return
        
        device_id = msg.get("device_id")
        device_name = msg.get("device_name", "Unknown")
        platform = msg.get("platform", "Unknown")
        resolution = msg.get("resolution", "Unknown")
        
        device_manager.register_device(ws, device_id, device_name, platform, resolution)
        
        # 转发给所有等待的控制器
        await broadcast_device_update()
        
        # 监听 Agent 消息
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            
            # 将消息转发给对应的控制器
            for session in device_manager.sessions.values():
                if session["agent_ws"] == ws:
                    try:
                        await session["controller_ws"].send_text(data)
                    except Exception as e:
                        logger.error(f"转发失败: {e}")
                        
    except WebSocketDisconnect:
        logger.info("Agent 断开连接")
    except Exception as e:
        logger.error(f"Agent 连接异常: {e}")
    finally:
        device_manager.unregister_device(ws)
        await broadcast_device_update()


@app.websocket("/ws/controller")
async def controller_endpoint(ws: WebSocket):
    """主控端 Controller 连接入口"""
    await ws.accept()
    logger.info("🔗 Controller WebSocket 已连接")
    
    try:
        # 先发送设备列表
        devices = device_manager.list_devices()
        await ws.send_text(json.dumps({
            "type": "device_list",
            "devices": devices
        }))
        
        # 监听控制器消息
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            action = msg.get("type")
            
            if action == "connect_device":
                # 请求连接设备
                device_id = msg.get("device_id")
                device = device_manager.get_device(device_id)
                
                if not device:
                    await ws.send_text(json.dumps({
                        "type": "error",
                        "message": f"设备 {device_id} 不在线"
                    }))
                    continue
                
                # 创建会话
                import uuid
                session_id = str(uuid.uuid4())[:8]
                
                await device["ws"].send_text(json.dumps({
                    "type": "control_start",
                    "session_id": session_id,
                    "quality": msg.get("quality", 75),
                    "fps": msg.get("fps", 15)
                }))
                
                device["is_controlled"] = True
                
                device_manager.create_session(session_id, ws, device["ws"])
                
                await ws.send_text(json.dumps({
                    "type": "connected",
                    "session_id": session_id,
                    "device_name": device["name"]
                }))
                
                await broadcast_device_update()
                
            elif action == "disconnect":
                session_id = msg.get("session_id")
                if session_id:
                    session = device_manager.sessions.get(session_id)
                    if session:
                        await session["agent_ws"].send_text(json.dumps({
                            "type": "control_stop"
                        }))
                        device_manager.close_session(session_id)
                
                # 更新设备状态
                for device in device_manager.devices.values():
                    device["is_controlled"] = False
                
                await ws.send_text(json.dumps({"type": "disconnected"}))
                await broadcast_device_update()
                
            elif action == "input":
                # 转发输入事件到 Agent
                session_id = msg.get("session_id")
                if session_id and session_id in device_manager.sessions:
                    agent_ws = device_manager.sessions[session_id]["agent_ws"]
                    try:
                        await agent_ws.send_text(data)
                    except Exception as e:
                        logger.error(f"转发输入事件失败: {e}")
                        
    except WebSocketDisconnect:
        logger.info("Controller 断开连接")
    except Exception as e:
        logger.error(f"Controller 连接异常: {e}")
    finally:
        # 清理会话
        for session_id, session in list(device_manager.sessions.items()):
            if session["controller_ws"] == ws:
                device_manager.close_session(session_id)


async def broadcast_device_update():
    """向所有控制器广播设备列表更新"""
    devices = device_manager.list_devices()
    msg = json.dumps({"type": "device_list", "devices": devices})
    
    to_remove = []
    for session in device_manager.sessions.values():
        try:
            await session["controller_ws"].send_text(msg)
        except Exception:
            to_remove.append(session)
    
    # 清理断开的控制器
    for session in to_remove:
        device_manager.close_session(next(
            sid for sid, s in device_manager.sessions.items() if s == session
        ))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
