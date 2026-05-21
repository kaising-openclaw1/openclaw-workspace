"""文件工具集"""

import os


def read_file(path: str, max_chars: int = 10000) -> str:
    """读取文件内容"""
    if not os.path.exists(path):
        return f"文件不存在: {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read(max_chars)
    return content


def write_file(path: str, content: str) -> str:
    """写入文件"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"已写入 {len(content)} 字符到 {path}"


def list_directory(path: str = ".") -> str:
    """列出目录内容"""
    if not os.path.exists(path):
        return f"目录不存在: {path}"
    items = os.listdir(path)
    lines = []
    for item in sorted(items):
        full = os.path.join(path, item)
        prefix = "📁 " if os.path.isdir(full) else "📄 "
        lines.append(f"{prefix}{item}")
    return "\n".join(lines)


def diff_files(file1: str, file2: str) -> str:
    """对比两个文件"""
    import difflib
    try:
        with open(file1) as f1, open(file2) as f2:
            diff = list(difflib.unified_diff(
                f1.readlines(), f2.readlines(),
                fromfile=file1, tofile=file2,
                lineterm=""
            ))
        return "".join(diff[:100]) if diff else "两个文件内容相同"
    except FileNotFoundError as e:
        return str(e)
