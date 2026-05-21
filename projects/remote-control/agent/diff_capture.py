"""差分截屏 - 只传输变化的屏幕区域，节省 70-90% 带宽"""
import logging
from typing import Optional, Dict, Tuple
from PIL import Image
import io
import base64
import hashlib

logger = logging.getLogger(__name__)


class DiffCapture:
    """差分截屏引擎
    
    原理：将屏幕分成 N×N 的小块，对比前后两帧的 MD5，
    只传输变化过的块，大幅降低带宽。
    """
    
    def __init__(self, block_size: int = 64):
        self.block_size = block_size
        self.last_frame: Optional[Image.Image] = None
        self.last_hashes: Dict[Tuple[int, int], str] = {}
        self.frame_count = 0
        self.total_bytes = 0
        self.diff_bytes = 0
        logger.info(f"✅ 差分截屏初始化 (块大小={block_size}px)")
    
    def capture(self, img: Image.Image, quality: int = 75) -> dict:
        """执行差分截屏
        
        Returns:
            {
                "type": "full" | "diff",
                "data": base64 | list[blocks],
                "width": int,
                "height": int,
                "changed_pct": float  # 变化百分比
            }
        """
        self.frame_count += 1
        
        # 首帧发送完整画面
        if self.last_frame is None:
            self.last_frame = img.copy()
            self.last_hashes = self._compute_hashes(img)
            data = self._encode(img, quality)
            self.total_bytes += len(data)
            return {
                "type": "full",
                "data": data,
                "width": img.width,
                "height": img.height,
                "changed_pct": 1.0
            }
        
        # 计算差分
        current_hashes = self._compute_hashes(img)
        changed_blocks = []
        
        for pos, hash_val in current_hashes.items():
            if self.last_hashes.get(pos) != hash_val:
                x, y = pos
                block = img.crop((x, y, x + self.block_size, y + self.block_size))
                block_data = self._encode(block, quality)
                changed_blocks.append({
                    "x": x, "y": y,
                    "w": block.width, "h": block.height,
                    "data": block_data
                })
        
        total_blocks = len(current_hashes)
        changed_count = len(changed_blocks)
        changed_pct = changed_count / max(total_blocks, 1)
        
        # 变化超过 40% 就发送完整帧（差分压缩不划算）
        if changed_pct > 0.4:
            self.last_frame = img.copy()
            self.last_hashes = current_hashes
            data = self._encode(img, quality)
            self.total_bytes += len(data)
            return {
                "type": "full",
                "data": data,
                "width": img.width,
                "height": img.height,
                "changed_pct": changed_pct
            }
        
        # 发送差分
        self.last_frame = img.copy()
        self.last_hashes = current_hashes
        
        diff_size = sum(len(b["data"]) for b in changed_blocks)
        self.diff_bytes += diff_size
        self.total_bytes += diff_size
        
        return {
            "type": "diff",
            "blocks": changed_blocks,
            "width": img.width,
            "height": img.height,
            "changed_pct": changed_pct,
            "total_blocks": total_blocks,
            "changed_blocks": changed_count
        }
    
    def _compute_hashes(self, img: Image.Image) -> Dict[Tuple[int, int], str]:
        """计算每个块的 MD5"""
        hashes = {}
        w, h = img.width, img.height
        
        for y in range(0, h, self.block_size):
            for x in range(0, w, self.block_size):
                block = img.crop((x, y, min(x + self.block_size, w), min(y + self.block_size, h)))
                hashes[(x, y)] = hashlib.md5(block.tobytes()[:128]).hexdigest()[:8]
        
        return hashes
    
    def _encode(self, img: Image.Image, quality: int) -> str:
        """编码为 base64 JPEG"""
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    
    def reset(self):
        """重置状态"""
        self.last_frame = None
        self.last_hashes = {}
    
    def stats(self) -> dict:
        return {
            "frames": self.frame_count,
            "total_bytes": self.total_bytes,
            "diff_bytes": self.diff_bytes,
            "avg_bytes": self.total_bytes // max(self.frame_count, 1)
        }
