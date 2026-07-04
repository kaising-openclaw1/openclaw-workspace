"""文件操作工具"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple


def read_file(path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> str:
    """读取文件内容"""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"错误：文件不存在 {path}"
    if not os.path.isfile(path):
        return f"错误：路径不是文件 {path}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        return f"错误：无法以文本方式读取 {path}（可能是二进制文件）"

    total = len(lines)
    if offset is not None:
        start = max(0, offset - 1)
        lines = lines[start:]
    if limit is not None:
        lines = lines[:limit]

    content = "".join(lines)
    if offset is not None:
        # 添加行号
        numbered = []
        for i, line in enumerate(lines, start=(offset or 1)):
            numbered.append(f"{i:6d} | {line}")
        content = "".join(numbered)

    info = f"文件: {path} ({total} 行, {os.path.getsize(path)} bytes)"
    if total > (limit or 99999):
        info += f" [显示 {len(lines)}/{total} 行]"
    return f"{info}\n{'-'*60}\n{content}"


def write_file(path: str, content: str) -> str:
    """写入文件（覆盖）"""
    path = os.path.expanduser(path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"✅ 已写入 {path} ({len(content)} 字符)"


def edit_file(path: str, old_text: str, new_text: str) -> str:
    """精确替换文件中的文本"""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"错误：文件不存在 {path}"

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if old_text not in content:
        return f"错误：未找到要替换的文本\n\n期望找到:\n{old_text[:200]}"

    count = content.count(old_text)
    if count > 1:
        return f"错误：找到 {count} 处匹配，请提供更精确的原文"

    new_content = content.replace(old_text, new_text, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return f"✅ 已编辑 {path} (替换 1 处)"


def list_files(path: str = ".") -> str:
    """列出目录内容"""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"错误：目录不存在 {path}"

    result = []
    result.append(f"📁 {os.path.abspath(path)}/")
    result.append("")

    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return f"错误：无权限访问 {path}"

    dirs = []
    files = []
    for entry in entries:
        full = os.path.join(path, entry)
        if entry.startswith("."):
            continue
        if os.path.isdir(full):
            dirs.append(f"📁 {entry}/")
        else:
            size = os.path.getsize(full)
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size/1024/1024:.1f} MB"
            files.append(f"📄 {entry} ({size_str})")

    result.extend(dirs)
    result.extend(files)
    return "\n".join(result)
