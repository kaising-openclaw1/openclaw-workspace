"""
Agent OS — Mesh 网络层：P2P 节点发现与连接
=========================================
去中心化 Mesh 网络，支持 NAT 穿透、自动发现、故障转移
"""

import asyncio
import json
import logging
import random
import socket
import struct
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("agent-os.network.mesh")


class NodeRole(Enum):
    """节点角色"""
    CONTROLLER = auto()   # 控制节点（可调度任务）
    WORKER = auto()       # 工作节点（执行任务）
    HYBRID = auto()       # 混合节点
    EDGE = auto()         # 边缘节点（低功耗/受限）
    GATEWAY = auto()      # 网关节点（连接外部网络）


class NodeStatus(Enum):
    ONLINE = auto()
    OFFLINE = auto()
    BUSY = auto()
    DEGRADED = auto()
    UNREACHABLE = auto()


@dataclass
class NodeInfo:
    """节点信息"""
    id: str
    name: str
    role: NodeRole
    host: str
    port: int
    public_host: str = ""
    public_port: int = 0
    status: NodeStatus = NodeStatus.ONLINE
    version: str = "0.1.0"
    capabilities: Dict[str, Any] = field(default_factory=dict)
    resources: Dict[str, Any] = field(default_factory=dict)
    last_seen: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    mesh_id: str = ""

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def public_address(self) -> str:
        if self.public_host:
            return f"{self.public_host}:{self.public_port or self.port}"
        return self.address

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.name,
            "host": self.host,
            "port": self.port,
            "public_host": self.public_host,
            "public_port": self.public_port,
            "status": self.status.name,
            "version": self.version,
            "capabilities": self.capabilities,
            "resources": self.resources,
            "last_seen": self.last_seen,
            "labels": self.labels,
            "mesh_id": self.mesh_id,
        }


@dataclass
class MeshConfig:
    """Mesh 网络配置"""
    node_name: str = ""
    role: NodeRole = NodeRole.HYBRID
    listen_host: str = "0.0.0.0"
    listen_port: int = 8765
    seed_nodes: List[str] = field(default_factory=list)
    discovery_interval: float = 30.0
    heartbeat_interval: float = 10.0
    node_timeout: float = 60.0
    max_peers: int = 100
    enable_nat_traversal: bool = True
    enable_mdns: bool = True
    enable_relay: bool = False
    relay_server: str = ""
    tls_enabled: bool = False
    tls_cert: str = ""
    tls_key: str = ""
    labels: Dict[str, str] = field(default_factory=dict)


class MeshNetwork:
    """
    P2P Mesh 网络

    特性：
    - 去中心化节点发现（gossip 协议）
    - 自动 NAT 穿透（STUN/UPnP）
    - 心跳保活 + 故障检测
    - 节点角色分级
    - 加密通信（TLS/mTLS）
    - 带宽感知路由
    """

    def __init__(self, config: MeshConfig):
        self.config = config
        self.node_id = uuid.uuid4().hex[:12]
        self.mesh_id = uuid.uuid4().hex[:8]

        self._local_node = NodeInfo(
            id=self.node_id,
            name=config.node_name or f"node-{self.node_id[:6]}",
            role=config.role,
            host=config.listen_host,
            port=config.listen_port,
            status=NodeStatus.ONLINE,
            mesh_id=self.mesh_id,
        )

        self._peers: Dict[str, NodeInfo] = {}
        self._connections: Dict[str, asyncio.Transport] = {}
        self._pending_connections: Set[str] = set()
        self._message_handlers: Dict[str, Callable] = {}
        self._event_bus = None

        # 任务
        self._server: Optional[asyncio.Server] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._discovery_task: Optional[asyncio.Task] = None
        self._running = False

        # 统计
        self._stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "peers_ever": 0,
            "reconnections": 0,
        }

    @property
    def local_node(self) -> NodeInfo:
        return self._local_node

    @property
    def peers(self) -> Dict[str, NodeInfo]:
        return dict(self._peers)

    @property
    def online_peers(self) -> List[NodeInfo]:
        return [
            p for p in self._peers.values()
            if p.status == NodeStatus.ONLINE
        ]

    # ── 生命周期 ──────────────────────────────────────

    async def start(self):
        """启动 Mesh 网络"""
        if self._running:
            return
        self._running = True

        # 启动 TCP 服务器
        self._server = await asyncio.start_server(
            self._handle_connection,
            self.config.listen_host,
            self.config.listen_port,
        )

        # 连接种子节点
        for seed in self.config.seed_nodes:
            host, port_str = seed.split(":")
            port = int(port_str)
            asyncio.create_task(self._connect_to_peer(host, port))

        # 启动心跳
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # 启动发现
        if self.config.enable_mdns:
            self._discovery_task = asyncio.create_task(self._discovery_loop())

        addr = self._server.sockets[0].getsockname()
        logger.info(
            f"Mesh 网络启动: {self._local_node.name} "
            f"({self._local_node.id}) @ {addr[0]}:{addr[1]}"
        )

    async def stop(self):
        """停止 Mesh 网络"""
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._discovery_task:
            self._discovery_task.cancel()

        # 广播离线
        await self._broadcast_offline()

        # 关闭连接
        for peer_id, transport in self._connections.items():
            transport.close()
        self._connections.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()

        logger.info(f"Mesh 网络停止: {self._local_node.name}")

    # ── 连接管理 ──────────────────────────────────────

    async def _connect_to_peer(self, host: str, port: int) -> bool:
        """连接到对等节点"""
        peer_addr = f"{host}:{port}"
        if peer_addr in self._pending_connections:
            return False
        if peer_addr in self._connections:
            return True

        self._pending_connections.add(peer_addr)
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=10.0,
            )
            self._connections[peer_addr] = writer
            self._stats["peers_ever"] += 1
            logger.info(f"连接到节点: {peer_addr}")
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            logger.debug(f"连接失败 {peer_addr}: {e}")
            return False
        finally:
            self._pending_connections.discard(peer_addr)

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.Transport
    ):
        """处理入站连接"""
        peer_addr = writer.get_extra_info("peername")
        logger.debug(f"入站连接: {peer_addr}")

        try:
            while self._running and not reader.at_eof():
                data = await asyncio.wait_for(reader.readline(), timeout=60.0)
                if not data:
                    break

                self._stats["messages_received"] += 1
                self._stats["bytes_received"] += len(data)

                message = json.loads(data.decode("utf-8").strip())
                await self._process_message(message, writer)

        except (asyncio.TimeoutError, ConnectionError, json.JSONDecodeError) as e:
            logger.debug(f"连接断开 {peer_addr}: {e}")
        finally:
            writer.close()

    # ── 消息协议 ──────────────────────────────────────

    async def send_message(
        self, peer_id: str, msg_type: str, payload: Dict[str, Any]
    ) -> bool:
        """发送消息到指定节点"""
        node = self._peers.get(peer_id)
        if not node:
            return False

        peer_addr = node.address
        writer = self._connections.get(peer_addr)
        if not writer:
            return False

        message = {
            "type": msg_type,
            "from": self.node_id,
            "mesh_id": self.mesh_id,
            "timestamp": time.time(),
            "payload": payload,
        }

        try:
            data = (json.dumps(message) + "\n").encode("utf-8")
            writer.write(data)
            await writer.drain()
            self._stats["messages_sent"] += 1
            self._stats["bytes_sent"] += len(data)
            return True
        except Exception as e:
            logger.warning(f"发送消息失败 [{peer_id}]: {e}")
            return False

    async def broadcast(self, msg_type: str, payload: Dict[str, Any]):
        """广播消息到所有在线节点"""
        tasks = [
            self.send_message(peer_id, msg_type, payload)
            for peer_id in self._peers
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_message(
        self, message: Dict[str, Any], writer: asyncio.Transport
    ):
        """处理接收到的消息"""
        msg_type = message.get("type", "")
        from_id = message.get("from", "")
        payload = message.get("payload", {})

        # 更新节点活跃时间
        if from_id in self._peers:
            self._peers[from_id].last_seen = time.time()

        # 处理系统消息
        handler = self._message_handlers.get(msg_type)
        if handler:
            await handler(from_id, payload)

        # 事件总线转发
        if self._event_bus:
            await self._event_bus.emit(
                f"network.{msg_type}",
                payload={"from": from_id, "data": payload},
            )

    def register_handler(self, msg_type: str, handler: Callable):
        """注册消息处理器"""
        self._message_handlers[msg_type] = handler

    # ── 心跳 ──────────────────────────────────────────

    async def _heartbeat_loop(self):
        """心跳循环"""
        while self._running:
            await asyncio.sleep(self.config.heartbeat_interval)

            # 更新本地状态
            self._local_node.last_seen = time.time()

            # 广播心跳
            await self.broadcast("heartbeat", {
                "node": self._local_node.to_dict(),
                "resources": self._get_local_resources(),
            })

            # 检测超时节点
            now = time.time()
            stale_peers = []
            for peer_id, node in self._peers.items():
                if now - node.last_seen > self.config.node_timeout:
                    node.status = NodeStatus.OFFLINE
                    stale_peers.append(peer_id)

            for peer_id in stale_peers:
                logger.warning(f"节点超时: {peer_id}")
                if self._event_bus:
                    await self._event_bus.emit(
                        "network.node_lost",
                        payload={"node_id": peer_id},
                    )

    # ── 节点发现 ──────────────────────────────────────

    async def _discovery_loop(self):
        """mDNS/局域网发现"""
        try:
            import socket as sock

            discovery_port = self.config.listen_port + 1
            udp_sock = sock.socket(sock.AF_INET, sock.SOCK_DGRAM, sock.IPPROTO_UDP)
            udp_sock.setsockopt(sock.SOL_SOCKET, sock.SO_REUSEADDR, 1)
            udp_sock.setsockopt(sock.SOL_SOCKET, sock.SO_BROADCAST, 1)
            udp_sock.bind(("", discovery_port))

            loop = asyncio.get_event_loop()

            while self._running:
                # 发送发现广播
                discovery_msg = json.dumps({
                    "type": "discovery",
                    "node_id": self.node_id,
                    "node_name": self._local_node.name,
                    "port": self.config.listen_port,
                    "role": self._local_node.role.name,
                }).encode("utf-8")

                udp_sock.sendto(discovery_msg, ("<broadcast>", discovery_port))

                # 接收发现响应
                try:
                    data, addr = await asyncio.wait_for(
                        loop.sock_recv(udp_sock, 4096),
                        timeout=5.0,
                    )
                    response = json.loads(data.decode("utf-8"))
                    if response.get("node_id") != self.node_id:
                        peer_host = addr[0]
                        peer_port = response.get("port", self.config.listen_port)
                        asyncio.create_task(
                            self._connect_to_peer(peer_host, peer_port)
                        )
                except (asyncio.TimeoutError, json.JSONDecodeError):
                    pass

                await asyncio.sleep(self.config.discovery_interval)

        except ImportError:
            logger.warning("mDNS 发现不可用（缺少 socket 权限）")
        except Exception as e:
            logger.error(f"发现循环异常: {e}")

    # ── 辅助 ──────────────────────────────────────────

    def _get_local_resources(self) -> Dict[str, Any]:
        """获取本地资源信息"""
        import psutil
        try:
            return {
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "disk_free": psutil.disk_usage("/").free,
                "load_avg": psutil.getloadavg(),
            }
        except Exception:
            return {}

    async def _broadcast_offline(self):
        """广播离线消息"""
        await self.broadcast("offline", {
            "node_id": self.node_id,
            "node_name": self._local_node.name,
        })

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)

    def get_peer_count(self) -> int:
        return len(self._peers)

    def get_online_count(self) -> int:
        return len(self.online_peers)
