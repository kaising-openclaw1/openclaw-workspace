"""会话录制模块 - 录制远程会话，支持回放"""
import logging
import json
import time
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime
import base64

logger = logging.getLogger(__name__)


class SessionRecorder:
    """会话录制器 - 录制截屏帧和输入事件，可回放"""
    
    def __init__(self, record_dir: Optional[str] = None, max_age_days: int = 30, max_size_mb: int = 5000):
        self.record_dir = Path(record_dir) if record_dir else Path.home() / ".remoteeye" / "recordings"
        self.record_dir.mkdir(parents=True, exist_ok=True)
        self.is_recording = False
        self._current_session: Optional[Dict] = None
        self._file_handle = None
        self._frame_count = 0
        self.max_age_days = max_age_days
        self.max_size_mb = max_size_mb
        logger.info(f"🎬 会话录制初始化: {self.record_dir} (保留{max_age_days}天, 最大{max_size_mb}MB)")
    
    def start(self, session_id: str, device_name: str, width: int, height: int):
        """开始录制"""
        if self.is_recording:
            self.stop()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{device_name}_{session_id}_{timestamp}.reml"
        filepath = self.record_dir / filename
        
        self._file_handle = open(filepath, "w", encoding="utf-8")
        self._current_session = {
            "session_id": session_id,
            "device_name": device_name,
            "started_at": time.time(),
            "width": width,
            "height": height,
            "filename": filename
        }
        self._frame_count = 0
        self.is_recording = True
        
        # 写入头部
        self._write_event("header", self._current_session)
        logger.info(f"🎬 开始录制: {filename}")
    
    def record_frame(self, frame_data, quality: int = 75):
        """录制截屏帧"""
        if not self.is_recording:
            return
        
        self._frame_count += 1
        self._write_event("frame", {
            "timestamp": time.time(),
            "frame": self._frame_count,
            "quality": quality,
            "data": frame_data
        })
    
    def record_input(self, action: str, data: dict):
        """录制输入事件"""
        if not self.is_recording:
            return
        
        self._write_event("input", {
            "timestamp": time.time(),
            "action": action,
            **data
        })
    
    def stop(self):
        """停止录制"""
        if not self.is_recording:
            return
        
        if self._current_session:
            self._current_session["ended_at"] = time.time()
            self._current_session["duration"] = self._current_session["ended_at"] - self._current_session["started_at"]
            self._current_session["total_frames"] = self._frame_count
            self._write_event("footer", self._current_session)
        
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
        
        duration = self._current_session.get("duration", 0) if self._current_session else 0
        logger.info(f"⏹️ 录制完成: {self._frame_count} 帧, {duration:.1f}秒")
        
        self.is_recording = False
        self._current_session = None
    
    def _write_event(self, event_type: str, data: dict):
        """写入事件"""
        if not self._file_handle:
            return
        
        record = {
            "t": event_type,
            "ts": time.time(),
            **data
        }
        self._file_handle.write(json.dumps(record) + "\n")
    
    def list_recordings(self, limit: int = 20) -> list:
        """列出录制文件"""
        recordings = []
        for f in sorted(self.record_dir.glob("*.reml"), key=lambda x: x.stat().st_mtime, reverse=True):
            stat = f.stat()
            info = self._read_recording_info(f)
            recordings.append({
                "filename": f.name,
                "size_mb": round(stat.st_size / (1024 * 1024), 1),
                "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "path": str(f),
                **info
            })
        return recordings[:limit]
    
    def _read_recording_info(self, filepath: Path) -> dict:
        """读取录制文件信息"""
        try:
            with open(filepath) as f:
                first_line = f.readline()
                header = json.loads(first_line)
                return {
                    "device_name": header.get("device_name", ""),
                    "session_id": header.get("session_id", "")
                }
        except:
            return {}
    
    def playback(self, filename: str) -> List[dict]:
        """回放录制文件"""
        filepath = self.record_dir / filename
        if not filepath.exists():
            return []
        
        events = []
        with open(filepath) as f:
            for line in f:
                try:
                    events.append(json.loads(line))
                except:
                    pass
        return events
    
    def cleanup(self):
        """🗑️ 清理过期/超大的录制文件 — 防止磁盘泄漏"""
        import shutil
        now = time.time()
        max_age = self.max_age_days * 86400
        total_size = 0
        
        # 收集所有录制文件，按时间排序
        recordings = sorted(
            self.record_dir.glob("*.reml"),
            key=lambda x: x.stat().st_mtime
        )
        
        # 第一遍：删除过期文件
        expired = 0
        for f in recordings:
            age = now - f.stat().st_mtime
            if age > max_age:
                f.unlink()
                expired += 1
                logger.info(f"🗑️ 删除过期录制: {f.name} ({age/86400:.0f}天)")
        
        # 第二遍：如果总大小仍然超限，从最旧的文件开始删除
        recordings = list(self.record_dir.glob("*.reml"))
        total_size = sum(f.stat().st_size for f in recordings)
        max_bytes = self.max_size_mb * 1024 * 1024
        
        deleted = 0
        if total_size > max_bytes:
            for f in sorted(recordings, key=lambda x: x.stat().st_mtime):
                f.unlink()
                deleted += 1
                total_size = sum(f.stat().st_size for f in self.record_dir.glob("*.reml"))
                if total_size <= max_bytes:
                    break
        
        if expired or deleted:
            logger.info(f"🗑️ 录制清理完成: {expired}个过期, {deleted}个超限")
        
        return {"expired": expired, "deleted": deleted, "remaining": len(list(self.record_dir.glob("*.reml")))}
    
    def get_disk_usage(self) -> dict:
        """获取录制目录磁盘使用情况"""
        recordings = list(self.record_dir.glob("*.reml"))
        total_size = sum(f.stat().st_size for f in recordings)
        return {
            "file_count": len(recordings),
            "total_size_mb": round(total_size / (1024 * 1024), 1),
            "max_size_mb": self.max_size_mb,
            "oldest": min((f.stat().st_mtime for f in recordings), default=0)
        }
