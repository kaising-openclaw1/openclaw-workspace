"""会话管理 — 保存和恢复对话历史"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional


SESSION_DIR = os.path.expanduser("~/.code-agent/sessions")


def ensure_dir():
    os.makedirs(SESSION_DIR, exist_ok=True)


def save_session(messages: List[Dict], name: Optional[str] = None) -> str:
    """保存会话到文件"""
    ensure_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = name or f"session_{timestamp}"
    path = os.path.join(SESSION_DIR, f"{fname}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump({"messages": messages, "saved_at": timestamp}, f, ensure_ascii=False, indent=2)

    return path


def load_session(name: str) -> Optional[List[Dict]]:
    """加载会话"""
    path = os.path.join(SESSION_DIR, f"{name}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("messages", [])


def list_sessions() -> List[str]:
    """列出所有会话"""
    ensure_dir()
    sessions = []
    for f in sorted(os.listdir(SESSION_DIR), reverse=True):
        if f.endswith(".json"):
            sessions.append(f.replace(".json", ""))
    return sessions
