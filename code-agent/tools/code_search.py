"""代码搜索工具"""

import os
import re
import fnmatch
from typing import List, Tuple


def search_code(pattern: str, path: str = ".") -> str:
    """在项目中搜索代码（关键词搜索，支持 glob）"""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"错误：路径不存在 {path}"

    results = []
    ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox", "build", "dist", ".next"}

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for fname in files:
            if not fnmatch.fnmatch(fname, pattern) and pattern not in fname:
                continue
            fpath = os.path.join(root, fname)
            try:
                size = os.path.getsize(fpath)
                if size > 1024 * 1024:  # skip files > 1MB
                    continue
                results.append(fpath)
            except (OSError, PermissionError):
                continue

    if not results:
        return f"未找到匹配 '{pattern}' 的文件"

    lines = [f"🔍 找到 {len(results)} 个匹配文件:"]
    for r in results[:50]:
        lines.append(f"  {r}")
    if len(results) > 50:
        lines.append(f"  ... 还有 {len(results) - 50} 个")

    return "\n".join(lines)


def grep(pattern: str, path: str = ".", max_results: int = 30) -> str:
    """正则搜索文件内容"""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"错误：路径不存在 {path}"

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"错误：正则表达式无效 - {e}"

    results = []
    ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox", "build", "dist", ".next"}
    text_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".md", ".txt", ".json", ".yaml", ".yml",
                       ".html", ".css", ".scss", ".vue", ".svelte", ".go", ".rs", ".java", ".c", ".h",
                       ".cpp", ".hpp", ".rb", ".php", ".sh", ".bash", ".zsh", ".toml", ".cfg", ".ini",
                       ".env", ".sql", ".graphql", ".proto", ".xml", ".svg"}

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in text_extensions:
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            rel = os.path.relpath(fpath, path)
                            results.append(f"{rel}:{i}: {line.rstrip()[:120]}")
                            if len(results) >= max_results:
                                break
            except (OSError, PermissionError):
                continue
            if len(results) >= max_results:
                break
        if len(results) >= max_results:
            break

    if not results:
        return f"未找到匹配 '{pattern}' 的内容"

    lines = [f"🔍 找到 {len(results)} 处匹配:"]
    lines.extend(results)
    return "\n".join(lines)


def analyze_project(path: str = ".") -> str:
    """分析项目结构"""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"错误：路径不存在 {path}"

    ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox", "build", "dist", ".next", ".mypy_cache", ".pytest_cache"}
    text_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".md", ".txt", ".json", ".yaml", ".yml",
                       ".html", ".css", ".scss", ".vue", ".svelte", ".go", ".rs", ".java", ".c", ".h",
                       ".cpp", ".hpp", ".rb", ".php", ".sh", ".bash", ".toml", ".cfg", ".ini",
                       ".env", ".sql", ".graphql", ".proto", ".xml"}

    stats = {}
    total_files = 0
    total_lines = 0
    dir_count = 0
    file_count = 0

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        dir_count += 1
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            fpath = os.path.join(root, fname)
            try:
                size = os.path.getsize(fpath)
                file_count += 1
                if ext in text_extensions:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        line_count = sum(1 for _ in f)
                    total_lines += line_count
                    stats[ext] = stats.get(ext, 0) + 1
                else:
                    stats[ext] = stats.get(ext, 0) + 1
                total_files += 1
            except (OSError, PermissionError):
                continue

    lines = [f"📊 项目分析: {os.path.abspath(path)}"]
    lines.append(f"")
    lines.append(f"   目录数: {dir_count}")
    lines.append(f"   文件数: {file_count}")
    lines.append(f"   代码行数: {total_lines}")
    lines.append(f"")
    lines.append(f"   文件类型分布:")

    for ext, count in sorted(stats.items(), key=lambda x: -x[1])[:15]:
        ext_name = ext if ext else "(no ext)"
        lines.append(f"     {ext_name:8s} × {count}")

    # 项目树（简化版）
    lines.append(f"")
    lines.append(f"   项目结构:")
    lines.append(f"     {os.path.basename(path)}/")
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        level = root.replace(path, "").count(os.sep)
        indent = "     " + "  " * level
        if level > 4:
            continue
        lines.append(f"{indent}{os.path.basename(root)}/")
        sub_indent = "     " + "  " * (level + 1)
        for fname in sorted(files)[:8]:
            lines.append(f"{sub_indent}{fname}")
        if len(files) > 8:
            lines.append(f"{sub_indent}... ({len(files)} 个文件)")

    return "\n".join(lines)
