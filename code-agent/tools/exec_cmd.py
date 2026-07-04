"""命令执行工具"""

import os
import subprocess
import shlex
from typing import Optional


def run_command(command: str, timeout: int = 60, workdir: Optional[str] = None) -> str:
    """执行 shell 命令并返回输出"""
    cwd = os.path.expanduser(workdir) if workdir else os.getcwd()

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

        output = []
        if result.stdout:
            output.append(result.stdout.rstrip()[:5000])
        if result.stderr:
            output.append(f"[stderr]\n{result.stderr.rstrip()[:2000]}")
        if result.returncode != 0:
            output.insert(0, f"⚠️ 退出码: {result.returncode}")

        return "\n".join(output) if output else "(无输出)"

    except subprocess.TimeoutExpired:
        return f"⏱️ 命令超时 ({timeout}s)"
    except FileNotFoundError as e:
        return f"错误: {e}"
    except Exception as e:
        return f"执行错误: {e}"
