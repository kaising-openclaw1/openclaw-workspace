"""
Agent OS — Artifact Store
=========================
存储、检索、版本管理任务执行产物
ChatGPT × Gemini 融合共识：~200-300 LOC 轻量实现
"""

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent-os.engine.artifact_store")


@dataclass
class Artifact:
    """执行产物"""
    id: str
    task_id: str
    name: str
    content: Any
    mime_type: str = "application/json"
    version: int = 1
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "name": self.name,
            "mime_type": self.mime_type,
            "version": self.version,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class ArtifactStore:
    """
    轻量 Artifact Store
    内存存储 + 可选文件持久化
    """

    def __init__(self, persist_dir: Optional[str] = None):
        self._artifacts: Dict[str, Artifact] = {}
        self._task_artifacts: Dict[str, List[str]] = {}  # task_id -> [artifact_id]
        self._persist_dir = persist_dir
        if persist_dir:
            os.makedirs(persist_dir, exist_ok=True)

    def save(self, artifact: Artifact) -> str:
        """保存产物"""
        self._artifacts[artifact.id] = artifact
        if artifact.task_id not in self._task_artifacts:
            self._task_artifacts[artifact.task_id] = []
        self._task_artifacts[artifact.task_id].append(artifact.id)

        # 文件持久化
        if self._persist_dir:
            self._persist(artifact)

        return artifact.id

    def get(self, artifact_id: str) -> Optional[Artifact]:
        """获取产物"""
        return self._artifacts.get(artifact_id)

    def get_by_task(self, task_id: str) -> List[Artifact]:
        """获取某个任务的所有产物"""
        artifact_ids = self._task_artifacts.get(task_id, [])
        return [self._artifacts[a_id] for a_id in artifact_ids if a_id in self._artifacts]

    def update(self, artifact_id: str, content: Any) -> Optional[Artifact]:
        """更新产物（版本递增）"""
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return None
        artifact.content = content
        artifact.version += 1
        artifact.created_at = time.time()

        if self._persist_dir:
            self._persist(artifact)

        return artifact

    def delete(self, artifact_id: str) -> bool:
        """删除产物"""
        artifact = self._artifacts.pop(artifact_id, None)
        if artifact:
            task_list = self._task_artifacts.get(artifact.task_id, [])
            if artifact_id in task_list:
                task_list.remove(artifact_id)
            # 删除持久化文件
            if self._persist_dir:
                fpath = os.path.join(self._persist_dir, f"{artifact_id}.json")
                if os.path.exists(fpath):
                    os.remove(fpath)
            return True
        return False

    def list_all(self) -> List[Artifact]:
        """列出所有产物"""
        return list(self._artifacts.values())

    def cleanup_old(self, max_age_seconds: int = 86400 * 30) -> int:
        """清理过期产物（默认 30 天）"""
        now = time.time()
        to_delete = [
            a_id for a_id, a in self._artifacts.items()
            if now - a.created_at > max_age_seconds
        ]
        for a_id in to_delete:
            self.delete(a_id)
        return len(to_delete)

    def _persist(self, artifact: Artifact):
        """持久化到文件"""
        fpath = os.path.join(self._persist_dir, f"{artifact.id}.json")
        try:
            with open(fpath, "w") as f:
                json.dump({
                    "id": artifact.id,
                    "task_id": artifact.task_id,
                    "name": artifact.name,
                    "content": artifact.content,
                    "mime_type": artifact.mime_type,
                    "version": artifact.version,
                    "created_at": artifact.created_at,
                    "metadata": artifact.metadata,
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist artifact {artifact.id}: {e}")

    def create_artifact(
        self,
        task_id: str,
        name: str,
        content: Any,
        mime_type: str = "application/json",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Artifact:
        """便捷创建产物"""
        return Artifact(
            id=uuid.uuid4().hex[:12],
            task_id=task_id,
            name=name,
            content=content,
            mime_type=mime_type,
            metadata=metadata or {},
        )
