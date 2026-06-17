"""
Agent OS — 算力抽象层：资源管理与调度
=====================================
统一算力接口，支持本地/远程/Docker/云
"""

import asyncio
import logging
import os
import platform
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("agent-os.compute.resource_manager")


class ComputeProviderType(Enum):
    """算力提供商类型"""
    LOCAL = auto()
    REMOTE_SSH = auto()
    DOCKER = auto()
    KUBERNETES = auto()
    CLOUD_VM = auto()
    EDGE = auto()


class ResourceUnit(Enum):
    """资源单位"""
    CPU_CORE = auto()
    GPU_CORE = auto()
    MEMORY_MB = auto()
    DISK_MB = auto()
    TOKEN_1K = auto()


@dataclass
class ComputeResources:
    """计算资源描述"""
    cpu_cores: float = 0
    gpu_count: int = 0
    gpu_memory_mb: int = 0
    memory_mb: int = 0
    disk_mb: int = 0
    network_bandwidth_mbps: float = 0
    gpu_type: str = ""
    cpu_arch: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_cores": self.cpu_cores,
            "gpu_count": self.gpu_count,
            "gpu_memory_mb": self.gpu_memory_mb,
            "memory_mb": self.memory_mb,
            "disk_mb": self.disk_mb,
            "network_bandwidth_mbps": self.network_bandwidth_mbps,
            "gpu_type": self.gpu_type,
            "cpu_arch": self.cpu_arch,
        }


@dataclass
class ResourceReservation:
    """资源预留"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_id: str = ""
    provider_id: str = ""
    resources: ComputeResources = field(default_factory=ComputeResources)
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    status: str = "active"  # active, released, expired


@dataclass
class ComputeProviderInfo:
    """算力提供商信息"""
    id: str
    name: str
    type: ComputeProviderType
    resources: ComputeResources
    available: bool = True
    load: float = 0.0  # 0-1
    latency_ms: float = 0.0
    cost_per_hour: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=time.time)


class ComputeProvider(ABC):
    """算力提供商抽象基类"""

    @abstractmethod
    async def initialize(self) -> bool:
        ...

    @abstractmethod
    async def get_resources(self) -> ComputeResources:
        ...

    @abstractmethod
    async def execute(self, command: str, timeout: float = 300) -> Tuple[int, str, str]:
        """执行命令，返回 (exit_code, stdout, stderr)"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...

    async def shutdown(self):
        pass


class LocalProvider(ComputeProvider):
    """本地算力提供商"""

    def __init__(self):
        self._info = ComputeProviderInfo(
            id="local",
            name=f"local-{platform.node()}",
            type=ComputeProviderType.LOCAL,
            resources=ComputeResources(),
        )

    async def initialize(self) -> bool:
        self._info.resources = await self.get_resources()
        logger.info(f"本地算力初始化: {self._info.resources.to_dict()}")
        return True

    async def get_resources(self) -> ComputeResources:
        import psutil
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        gpu_count = 0
        gpu_mem = 0
        gpu_type = ""
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=count,memory.total,name",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    parts = line.split(", ")
                    if len(parts) >= 3:
                        gpu_count += 1
                        gpu_mem += int(parts[1])
                        gpu_type = parts[2]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return ComputeResources(
            cpu_cores=psutil.cpu_count(),
            gpu_count=gpu_count,
            gpu_memory_mb=gpu_mem,
            memory_mb=mem.total // (1024 * 1024),
            disk_mb=disk.free // (1024 * 1024),
            cpu_arch=platform.machine(),
            gpu_type=gpu_type,
        )

    async def execute(self, command: str, timeout: float = 300) -> Tuple[int, str, str]:
        import subprocess
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Timeout"
        except Exception as e:
            return -1, "", str(e)

    async def health_check(self) -> bool:
        try:
            resources = await self.get_resources()
            return resources.memory_mb > 100
        except Exception:
            return False


class ResourceManager:
    """
    资源管理器

    职责：
    - 管理多个算力提供商
    - 资源发现与监控
    - 智能调度（负载均衡）
    - 资源预留与释放
    """

    def __init__(self):
        self._providers: Dict[str, ComputeProvider] = {}
        self._provider_info: Dict[str, ComputeProviderInfo] = {}
        self._reservations: Dict[str, ResourceReservation] = {}
        self._event_bus = None
        self._lock = asyncio.Lock()
        self._monitor_task: Optional[asyncio.Task] = None

    async def register_provider(self, provider: ComputeProvider) -> str:
        """注册算力提供商"""
        async with self._lock:
            success = await provider.initialize()
            if not success:
                raise RuntimeError(f"提供商初始化失败: {provider}")

            info = await self._get_provider_info(provider)
            self._providers[info.id] = provider
            self._provider_info[info.id] = info

            logger.info(f"算力提供商已注册: {info.name} ({info.type.name})")
            if self._event_bus:
                await self._event_bus.emit(
                    "compute.provider_registered",
                    payload={"provider_id": info.id, "resources": info.resources.to_dict()},
                )
            return info.id

    async def unregister_provider(self, provider_id: str):
        """注销算力提供商"""
        async with self._lock:
            provider = self._providers.pop(provider_id, None)
            self._provider_info.pop(provider_id, None)
            if provider:
                await provider.shutdown()
                logger.info(f"算力提供商已注销: {provider_id}")

    async def _get_provider_info(self, provider: ComputeProvider) -> ComputeProviderInfo:
        """获取提供商信息"""
        if isinstance(provider, LocalProvider):
            resources = await provider.get_resources()
            return ComputeProviderInfo(
                id="local",
                name=f"local-{platform.node()}",
                type=ComputeProviderType.LOCAL,
                resources=resources,
            )
        return ComputeProviderInfo(
            id=uuid.uuid4().hex[:8],
            name="unknown",
            type=ComputeProviderType.LOCAL,
            resources=ComputeResources(),
        )

    async def get_available_resources(self) -> Dict[str, ComputeResources]:
        """获取所有可用资源"""
        result = {}
        for pid, info in self._provider_info.items():
            if info.available:
                result[pid] = info.resources
        return result

    async def select_provider(
        self,
        required: ComputeResources,
        prefer_gpu: bool = False,
        max_cost: float = float("inf"),
    ) -> Optional[str]:
        """选择最优提供商"""
        candidates = []

        for pid, info in self._provider_info.items():
            if not info.available:
                continue

            res = info.resources
            # 检查资源是否满足
            if res.cpu_cores < required.cpu_cores:
                continue
            if res.memory_mb < required.memory_mb:
                continue
            if prefer_gpu and res.gpu_count < required.gpu_count:
                continue
            if info.cost_per_hour > max_cost:
                continue

            # 评分：负载越低越好，资源越多越好
            score = (1 - info.load) * 0.5 + min(res.cpu_cores / 32, 1) * 0.3 + \
                    min(res.memory_mb / 32768, 1) * 0.2
            candidates.append((score, pid))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    async def reserve_resources(
        self, task_id: str, resources: ComputeResources, duration: float = 3600
    ) -> Optional[ResourceReservation]:
        """预留资源"""
        provider_id = await self.select_provider(resources)
        if not provider_id:
            return None

        reservation = ResourceReservation(
            task_id=task_id,
            provider_id=provider_id,
            resources=resources,
            expires_at=time.time() + duration,
        )
        self._reservations[reservation.id] = reservation

        if self._event_bus:
            await self._event_bus.emit(
                "compute.resources_reserved",
                payload={
                    "reservation_id": reservation.id,
                    "provider_id": provider_id,
                    "resources": resources.to_dict(),
                },
            )

        return reservation

    async def release_resources(self, reservation_id: str):
        """释放资源"""
        reservation = self._reservations.pop(reservation_id, None)
        if reservation:
            reservation.status = "released"
            logger.info(f"资源已释放: {reservation_id}")

    async def get_provider(self, provider_id: str) -> Optional[ComputeProvider]:
        return self._providers.get(provider_id)

    async def get_all_providers(self) -> Dict[str, ComputeProviderInfo]:
        return dict(self._provider_info)

    async def start_monitoring(self, interval: float = 30.0):
        """启动资源监控"""
        async def _monitor():
            while True:
                await asyncio.sleep(interval)
                for pid, provider in list(self._providers.items()):
                    try:
                        healthy = await provider.health_check()
                        if pid in self._provider_info:
                            self._provider_info[pid].available = healthy
                            self._provider_info[pid].last_heartbeat = time.time()
                    except Exception as e:
                        logger.warning(f"健康检查失败 [{pid}]: {e}")
                        if pid in self._provider_info:
                            self._provider_info[pid].available = False

        self._monitor_task = asyncio.create_task(_monitor())

    async def stop_monitoring(self):
        if self._monitor_task:
            self._monitor_task.cancel()

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus
