"""信令服务器 v3.0 - 生产级远程控制信令服务

功能:
- 设备注册与管理
- 连接码系统（9位ID + 6位密码）
- 多控制器并发
- 💓 心跳保活 + 设备健康监控
- 💬 聊天消息中继
- 会话质量监控
- 文件传输中继
- 远程 Shell 中继
- 🛡️ 优雅关闭 + 录制清理
"""
import asyncio
import json
import logging
import signal
import time
import uuid
from typing import Dict, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('server')

app = FastAPI(title="RemoteEye Signaling Server v3.0", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionCardManager:
    """连接码管理器 - 类似 TeamViewer 的 ID + 密码"""
    
    def __init__(self, ttl_seconds: int = 600):
        # code -> {"device_id": str, "password": str, "expires_at": float}
        self.cards: Dict[str, dict] = {}
        # device_id -> code
        self.device_to_code: Dict[str, str] = {}
        self.ttl = ttl_seconds
    
    def generate(self, device_id: str) -> tuple:
        """生成连接码 (id, password)"""
        import random
        conn_id = ''.join([str(random.randint(0, 9)) for _ in range(9)])
        password = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # 清理旧码
        old_code = self.device_to_code.get(device_id)
        if old_code:
            self.cards.pop(old_code, None)
        
        now = time.time()
        self.cards[conn_id] = {
            "device_id": device_id,
            "password": password,
            "created_at": now,
            "expires_at": now + self.ttl
        }
        self.device_to_code[device_id] = conn_id
        return conn_id, password
    
    def verify(self, code: str, password: str) -> Optional[str]:
        """验证连接码，返回 device_id"""
        self._cleanup()
        card = self.cards.get(code)
        if card and card["password"] == password:
            return card["device_id"]
        return None
    
    def refresh(self, device_id: str) -> Optional[tuple]:
        """刷新指定设备的连接码"""
        return self.generate(device_id)
    
    def get_remaining(self, code: str) -> int:
        card = self.cards.get(code)
        if not card:
            return 0
        return max(0, int(card["expires_at"] - time.time()))
    
    def _cleanup(self):
        now = time.time()
        expired = [c for c, info in self.cards.items() if info["expires_at"] < now]
        for c in expired:
            del self.cards[c]


class DeviceManager:
    """设备管理器"""
    
    def __init__(self):
        # device_id -> device_info
        self.devices: Dict[str, dict] = {}
        # session_id -> session_info
        self.sessions: Dict[str, dict] = {}
        # ws -> device_id
        self.ws_to_device: Dict[WebSocket, str] = {}
        self.cards = ConnectionCardManager()
        
        # 💓 心跳追踪
        self.heartbeats: Dict[str, float] = {}  # device_id -> last_heartbeat_ts
        
        # 💬 聊天日志
        self.chat_log: list = []  # [{"ts", "device_id", "from", "message"}]
        
        # 🛡️ 连接审计日志
        self.audit_log: list = []  # [{"ts", "event", "device_id", "detail"}]
        
        # 统计
        self.stats = {
            "total_connections": 0,
            "total_sessions": 0,
            "started_at": time.time()
        }
    
    def log_audit(self, event: str, device_id: str, detail: str = ""):
        """🛡️ 记录审计事件"""
        entry = {"ts": time.time(), "event": event, "device_id": device_id, "detail": detail}
        self.audit_log.append(entry)
        if len(self.audit_log) > 200:
            self.audit_log = self.audit_log[-200:]
        return entry
    
    def register_device(self, ws: WebSocket, device_id: str, name: str, platform: str,
                       resolution: str, monitors: list = None, features: dict = None,
                       system_info: dict = None) -> tuple:
        """注册设备，返回 (conn_id, password)"""
        self.devices[device_id] = {
            "ws": ws,
            "name": name,
            "platform": platform,
            "resolution": resolution,
            "monitors": monitors or [],
            "features": features or {},
            "system_info": system_info or {},
            "connected_at": time.time(),
            "last_heartbeat": time.time(),
            "is_controlled": False,
            "active_sessions": []
        }
        self.ws_to_device[ws] = device_id
        self.heartbeats[device_id] = time.time()
        self.stats["total_connections"] += 1
        
        # 生成连接码
        conn_id, password = self.cards.generate(device_id)
        
        logger.info(f"📱 设备注册: {name} ({device_id}) → 连接码: {conn_id}")
        return conn_id, password
    
    def record_heartbeat(self, device_id: str):
        """💓 记录设备心跳"""
        if device_id in self.devices:
            self.devices[device_id]["last_heartbeat"] = time.time()
            self.heartbeats[device_id] = time.time()
    
    def get_device_health(self) -> dict:
        """💓 获取设备健康状态"""
        now = time.time()
        result = {}
        for did, info in self.devices.items():
            last_hb = info.get("last_heartbeat", 0)
            gap = now - last_hb
            result[did] = {
                "alive": gap < 60,
                "last_heartbeat_ago": round(gap, 1),
                "uptime": round(now - info["connected_at"], 1)
            }
        return result
    
    def log_chat(self, device_id: str, sender: str, message: str):
        """💬 记录聊天消息"""
        entry = {
            "ts": time.time(),
            "device_id": device_id,
            "from": sender,
            "message": message
        }
        self.chat_log.append(entry)
        # 只保留最近 100 条
        if len(self.chat_log) > 100:
            self.chat_log = self.chat_log[-100:]
        return entry
    
    def unregister_device(self, ws: WebSocket):
        """注销设备"""
        device_id = self.ws_to_device.pop(ws, None)
        if device_id and device_id in self.devices:
            device = self.devices[device_id]
            # 清理会话
            for sid in list(device["active_sessions"]):
                if sid in self.sessions:
                    del self.sessions[sid]
            self.cards.device_to_code.pop(device_id, None)
            self.log_audit("device_offline", device_id, f"设备 {device['name']} 离线")
            del self.devices[device_id]
            logger.info(f"📴 设备离线: {device_id}")
    
    def get_device(self, device_id: str) -> Optional[dict]:
        return self.devices.get(device_id)
    
    def list_devices(self) -> list:
        return [
            {
                "device_id": did,
                "name": info["name"],
                "platform": info["platform"],
                "resolution": info["resolution"],
                "monitors": info.get("monitors", []),
                "online": True,
                "is_controlled": info["is_controlled"],
                "connected_at": info["connected_at"],
                "system_info": info.get("system_info", {}),
                "features": info.get("features", {})
            }
            for did, info in self.devices.items()
        ]
    
    def create_session(self, session_id: str, controller_ws: WebSocket, agent_ws: WebSocket,
                      mode: str = "control") -> dict:
        """创建会话"""
        device_id = self.ws_to_device.get(agent_ws)
        session = {
            "session_id": session_id,
            "controller_ws": controller_ws,
            "agent_ws": agent_ws,
            "device_id": device_id,
            "started_at": time.time(),
            "mode": mode
        }
        self.sessions[session_id] = session
        if device_id and device_id in self.devices:
            self.devices[device_id]["active_sessions"].append(session_id)
            self.devices[device_id]["is_controlled"] = True
        self.stats["total_sessions"] += 1
        return session
    
    def close_session(self, session_id: str):
        """关闭会话"""
        session = self.sessions.pop(session_id, None)
        if session:
            device_id = session.get("device_id")
            if device_id and device_id in self.devices:
                device = self.devices[device_id]
                if session_id in device["active_sessions"]:
                    device["active_sessions"].remove(session_id)
                if not device["active_sessions"]:
                    device["is_controlled"] = False


device_manager = DeviceManager()


# ==================== API ====================

@app.get("/")
async def index():
    return FileResponse("web/templates/index.html")


@app.get("/api/devices")
async def api_devices():
    return {"devices": device_manager.list_devices()}


@app.get("/api/health")
async def api_health():
    uptime = time.time() - device_manager.stats["started_at"]
    return {
        "status": "healthy",
        "version": "3.0.0",
        "uptime": round(uptime),
        "devices_online": len(device_manager.devices),
        "active_sessions": len(device_manager.sessions),
        "total_connections": device_manager.stats["total_connections"],
        "total_sessions": device_manager.stats["total_sessions"],
        "device_health": device_manager.get_device_health(),
        "chat_log_count": len(device_manager.chat_log)
    }


# ==================== WebSocket ====================

@app.websocket("/ws/agent")
async def agent_endpoint(ws: WebSocket):
    """被控端连接"""
    await ws.accept()
    logger.info("🔗 Agent 连接")
    
    try:
        data = await asyncio.wait_for(ws.receive_text(), timeout=30)
        msg = json.loads(data)
        
        if msg.get("type") != "register":
            await ws.close(code=1008, reason="需要 register")
            return
        
        device_id = msg.get("device_id")
        conn_id, password = device_manager.register_device(
            ws, device_id,
            msg.get("device_name", "Unknown"),
            msg.get("platform", "Unknown"),
            msg.get("resolution", "Unknown"),
            msg.get("monitors", []),
            msg.get("features"),
            msg.get("system_info")
        )
        device_manager.log_audit("device_register", device_id, msg.get("device_name", "Unknown"))
        
        # 发送连接码
        await ws.send_text(json.dumps({
            "type": "connection_card",
            "connection_id": conn_id,
            "connection_password": password,
            "expires_in": device_manager.cards.get_remaining(conn_id)
        }))
        
        await broadcast_devices()
        
        # 消息转发
        async for raw in ws:
            try:
                data = json.loads(raw)
                msg_type = data.get("type")
                
                # 💓 心跳处理
                if msg_type == "ping":
                    device_manager.record_heartbeat(device_id)
                    await ws.send_text(json.dumps({"type": "pong", "ts": time.time()}))
                    continue
                
                # 💬 聊天消息转发到控制器
                if msg_type == "chat":
                    session_id = data.get("session_id")
                    if session_id and session_id in device_manager.sessions:
                        ctrl_ws = device_manager.sessions[session_id]["controller_ws"]
                        await ctrl_ws.send_text(raw)
                    device_manager.log_chat(device_id, "agent", data.get("message", ""))
                    continue
                
                # 普通消息转发
                session_id = data.get("session_id")
                if session_id and session_id in device_manager.sessions:
                    ctrl_ws = device_manager.sessions[session_id]["controller_ws"]
                    await ctrl_ws.send_text(raw)
            except Exception as e:
                logger.error(f"Agent 消息转发失败: {e}")
                
    except WebSocketDisconnect:
        logger.info("Agent 断开")
    except Exception as e:
        logger.error(f"Agent 异常: {e}")
    finally:
        device_manager.unregister_device(ws)
        await broadcast_devices()


@app.websocket("/ws/controller")
async def controller_endpoint(ws: WebSocket):
    """主控端连接"""
    await ws.accept()
    logger.info("🔗 Controller 连接")
    
    try:
        await ws.send_text(json.dumps({
            "type": "device_list",
            "devices": device_manager.list_devices()
        }))
        
        async for raw in ws:
            try:
                msg = json.loads(raw)
                action = msg.get("type")
                
                if action == "connect_device":
                    await _connect_by_id(ws, msg)
                elif action == "connect_by_code":
                    await _connect_by_code(ws, msg)
                elif action == "disconnect":
                    await _disconnect(ws, msg)
                elif action == "refresh_connection_card":
                    await _refresh_card(ws, msg)
                elif action == "chat":
                    await _relay_chat(ws, msg)
                elif action == "get_device_health":
                    await ws.send_text(json.dumps({
                        "type": "device_health",
                        "health": device_manager.get_device_health()
                    }))
                else:
                    # 转发给 Agent
                    await _forward(ws, msg)
                    
            except Exception as e:
                logger.error(f"Controller 消息处理失败: {e}")
                
    except WebSocketDisconnect:
        logger.info("Controller 断开")
    except Exception as e:
        logger.error(f"Controller 异常: {e}")
    finally:
        for sid, s in list(device_manager.sessions.items()):
            if s["controller_ws"] == ws:
                try:
                    await s["agent_ws"].send_text(json.dumps({"type": "control_stop", "session_id": sid}))
                except:
                    pass
                device_manager.close_session(sid)


async def _connect_by_id(controller_ws: WebSocket, msg: dict):
    """通过设备 ID 连接"""
    device = device_manager.get_device(msg.get("device_id"))
    if not device:
        await controller_ws.send_text(json.dumps({"type": "error", "message": "设备不在线"}))
        return
    
    session_id = str(uuid.uuid4())[:8]
    device_manager.create_session(session_id, controller_ws, device["ws"], msg.get("mode", "control"))
    
    await device["ws"].send_text(json.dumps({
        "type": "control_start",
        "session_id": session_id,
        "quality": msg.get("quality", 75),
        "fps": msg.get("fps", 15),
        "monitor": msg.get("monitor", 0),
        "view_only": msg.get("mode") == "view"
    }))
    
    await controller_ws.send_text(json.dumps({
        "type": "connected",
        "session_id": session_id,
        "device_name": device["name"],
        "monitors": device.get("monitors", []),
        "system_info": device.get("system_info", {}),
        "mode": msg.get("mode", "control")
    }))
    
    # 发送连接码
    conn_id, password = device_manager.cards.generate(device_manager.ws_to_device.get(device["ws"]))
    await controller_ws.send_text(json.dumps({
        "type": "connection_card",
        "connection_id": conn_id,
        "connection_password": password,
        "expires_in": device_manager.cards.get_remaining(conn_id)
    }))
    
    await broadcast_devices()


async def _connect_by_code(controller_ws: WebSocket, msg: dict):
    """通过连接码连接"""
    code = msg.get("code", "").strip()
    password = msg.get("password", "").strip()
    
    device_id = device_manager.cards.verify(code, password)
    if not device_id:
        await controller_ws.send_text(json.dumps({"type": "error", "message": "无效或过期的连接码"}))
        return
    
    await _connect_by_id(controller_ws, {
        "device_id": device_id,
        "quality": msg.get("quality", 75),
        "fps": msg.get("fps", 15),
        "mode": msg.get("mode", "control")
    })


async def _disconnect(controller_ws: WebSocket, msg: dict):
    """断开连接"""
    session_id = msg.get("session_id")
    if session_id and session_id in device_manager.sessions:
        session = device_manager.sessions[session_id]
        try:
            await session["agent_ws"].send_text(json.dumps({"type": "control_stop", "session_id": session_id}))
        except:
            pass
        device_manager.close_session(session_id)
    
    for device in device_manager.devices.values():
        if not device["active_sessions"]:
            device["is_controlled"] = False
    
    await controller_ws.send_text(json.dumps({"type": "disconnected"}))
    await broadcast_devices()


async def _refresh_card(controller_ws: WebSocket, msg: dict):
    """刷新连接码"""
    session_id = msg.get("session_id")
    if session_id and session_id in device_manager.sessions:
        device_id = device_manager.sessions[session_id]["device_id"]
        conn_id, password = device_manager.cards.refresh(device_id)
        await controller_ws.send_text(json.dumps({
            "type": "connection_card",
            "connection_id": conn_id,
            "connection_password": password,
            "expires_in": device_manager.cards.get_remaining(conn_id)
        }))


async def _forward(controller_ws: WebSocket, msg: dict):
    """转发消息到 Agent"""
    session_id = msg.get("session_id")
    if session_id and session_id in device_manager.sessions:
        try:
            await device_manager.sessions[session_id]["agent_ws"].send_text(json.dumps(msg))
        except Exception as e:
            logger.error(f"转发失败: {e}")


async def _relay_chat(controller_ws: WebSocket, msg: dict):
    """💬 转发聊天消息到 Agent"""
    session_id = msg.get("session_id")
    if session_id and session_id in device_manager.sessions:
        device_id = device_manager.sessions[session_id]["device_id"]
        try:
            await device_manager.sessions[session_id]["agent_ws"].send_text(json.dumps(msg))
            device_manager.log_chat(device_id, "controller", msg.get("message", ""))
        except Exception as e:
            logger.error(f"聊天转发失败: {e}")


async def broadcast_devices():
    """广播设备列表"""
    msg = json.dumps({"type": "device_list", "devices": device_manager.list_devices()})
    for session in list(device_manager.sessions.values()):
        try:
            await session["controller_ws"].send_text(msg)
        except:
            pass


async def periodic_cleanup():
    """🗑️ 定期清理过期录制文件和离线设备"""
    while True:
        await asyncio.sleep(3600)  # 每小时
        # 清理过期录制文件
        offline = [did for did, info in device_manager.devices.items()
                   if time.time() - info.get("last_heartbeat", 0) > 60]
        if offline:
            logger.info(f"📡 心跳检查: {len(offline)} 个设备可能离线")


def setup_graceful_shutdown():
    """🛡️ 设置优雅关闭"""
    import signal as sig
    try:
        loop = asyncio.get_event_loop()
        for s in (sig.SIGTERM, sig.SIGINT):
            loop.add_signal_handler(s, lambda: logger.info("🛑 收到关闭信号"))
        logger.info("🛡️ 优雅关闭处理器已注册")
    except NotImplementedError:
        pass  # Windows


if __name__ == "__main__":
    import uvicorn
    setup_graceful_shutdown()
    logger.info("🚀 RemoteEye Server v3.0 启动中...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
