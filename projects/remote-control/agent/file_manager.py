"""文件传输模块 - 远程文件浏览/上传/下载"""
import os
import base64
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 允许访问的根目录（安全限制）
ALLOWED_ROOTS = [
    str(Path.home()),
    "/tmp",
]


def is_path_allowed(path: str) -> bool:
    """检查路径是否在允许范围内"""
    try:
        resolved = Path(path).resolve()
        return any(str(resolved).startswith(str(Path(root).resolve())) for root in ALLOWED_ROOTS)
    except Exception:
        return False


class FileManager:
    """远程文件管理器"""
    
    def __init__(self, root: Optional[str] = None):
        self.root = root or str(Path.home())
        if not is_path_allowed(self.root):
            self.root = str(Path.home())
            logger.warning(f"根目录不在允许范围内，回退到: {self.root}")
        logger.info(f"📁 文件管理器初始化: {self.root}")
    
    def list_directory(self, path: Optional[str] = None) -> dict:
        """列出目录内容"""
        target = Path(path) if path else Path(self.root)
        target = target.resolve()
        
        if not is_path_allowed(str(target)):
            return {"error": "路径不在允许范围内", "path": str(target)}
        
        if not target.exists():
            return {"error": "路径不存在", "path": str(target)}
        
        if not target.is_dir():
            return {"error": "不是目录", "path": str(target)}
        
        items = []
        try:
            for item in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                try:
                    stat = item.stat()
                    items.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size if item.is_file() else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "path": str(item)
                    })
                except PermissionError:
                    items.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": None,
                        "modified": "无权限",
                        "path": str(item),
                        "permission_denied": True
                    })
        except PermissionError:
            return {"error": "无权限访问", "path": str(target)}
        
        return {
            "path": str(target),
            "parent": str(target.parent) if str(target) != self.root else None,
            "items": items,
            "total": len(items)
        }
    
    def download_file(self, path: str, chunk_size: int = 65536) -> dict:
        """下载文件（分块读取）"""
        target = Path(path).resolve()
        
        if not is_path_allowed(str(target)):
            return {"error": "路径不在允许范围内"}
        
        if not target.is_file():
            return {"error": "不是文件"}
        
        try:
            file_size = target.stat().st_size
            with open(target, "rb") as f:
                content = f.read(chunk_size)
            
            return {
                "name": target.name,
                "size": file_size,
                "data": base64.b64encode(content).decode('utf-8'),
                "chunk_size": chunk_size,
                "offset": chunk_size,
                "done": file_size <= chunk_size
            }
        except PermissionError:
            return {"error": "无权限读取文件"}
        except Exception as e:
            return {"error": str(e)}
    
    def download_chunk(self, path: str, offset: int, chunk_size: int = 65536) -> dict:
        """下载文件的下一个块"""
        target = Path(path).resolve()
        
        try:
            with open(target, "rb") as f:
                f.seek(offset)
                content = f.read(chunk_size)
            
            new_offset = offset + len(content)
            file_size = target.stat().st_size
            
            return {
                "data": base64.b64encode(content).decode('utf-8'),
                "offset": new_offset,
                "done": new_offset >= file_size
            }
        except Exception as e:
            return {"error": str(e)}
    
    def upload_file(self, path: str, data: str, append: bool = False) -> dict:
        """上传文件块"""
        target = Path(path).resolve()
        
        if not is_path_allowed(str(target)):
            return {"error": "路径不在允许范围内"}
        
        try:
            mode = "ab" if append else "wb"
            content = base64.b64decode(data)
            with open(target, mode) as f:
                f.write(content)
            return {"success": True, "written": len(content)}
        except PermissionError:
            return {"error": "无权限写入"}
        except Exception as e:
            return {"error": str(e)}
    
    def create_directory(self, path: str) -> dict:
        """创建目录"""
        target = Path(path).resolve()
        
        if not is_path_allowed(str(target)):
            return {"error": "路径不在允许范围内"}
        
        try:
            target.mkdir(parents=True, exist_ok=True)
            return {"success": True, "path": str(target)}
        except PermissionError:
            return {"error": "无权限创建"}
        except Exception as e:
            return {"error": str(e)}
    
    def delete_item(self, path: str) -> dict:
        """删除文件或目录"""
        target = Path(path).resolve()
        
        if not is_path_allowed(str(target)):
            return {"error": "路径不在允许范围内"}
        
        try:
            if target.is_file():
                target.unlink()
                return {"success": True, "action": "deleted_file"}
            elif target.is_dir():
                import shutil
                shutil.rmtree(target)
                return {"success": True, "action": "deleted_directory"}
            return {"error": "路径不存在"}
        except PermissionError:
            return {"error": "无权限删除"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_file_info(self, path: str) -> dict:
        """获取文件信息"""
        target = Path(path).resolve()
        
        if not is_path_allowed(str(target)):
            return {"error": "路径不在允许范围内"}
        
        if not target.exists():
            return {"error": "路径不存在"}
        
        stat = target.stat()
        return {
            "name": target.name,
            "type": "directory" if target.is_dir() else "file",
            "size": stat.st_size if target.is_file() else None,
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M"),
            "path": str(target)
        }
