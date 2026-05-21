"""
Agent Memory Toolkit - Persistent memory for AI coding agents
Core memory engine with SQLite backend.
"""

import os
import sqlite3
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class MemoryEntry:
    id: Optional[int] = None
    entry_type: str = ""  # decision, code_change, lesson, context, todo, preference
    content: str = ""
    tags: str = ""  # comma-separated tags
    priority: int = 1  # 1=normal, 2=important, 3=critical
    timestamp: float = 0.0
    workspace: str = ""
    metadata: str = "{}"  # JSON string for extensible metadata

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


class AgentMemory:
    """Core memory engine for AI coding agents."""

    MEMORY_TYPES = ("decision", "code_change", "lesson", "context", "todo", "preference")
    DB_VERSION = 1

    def __init__(self, workspace: str = ".", db_path: Optional[str] = None):
        self.workspace = os.path.abspath(workspace)
        if db_path is None:
            memory_dir = os.path.join(self.workspace, ".agent-memory")
            os.makedirs(memory_dir, exist_ok=True)
            db_path = os.path.join(memory_dir, "memory.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT DEFAULT '',
                    priority INTEGER DEFAULT 1,
                    timestamp REAL NOT NULL,
                    workspace TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    content_hash TEXT NOT NULL UNIQUE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_type ON memories(entry_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tags ON memories(tags)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_priority ON memories(priority DESC)
            """)
            # Version tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                )
            """)
            cur = conn.execute("SELECT version FROM schema_version LIMIT 1")
            row = cur.fetchone()
            if not row:
                conn.execute("INSERT INTO schema_version (version) VALUES (?)", (self.DB_VERSION,))

    @staticmethod
    def _hash(content: str, workspace: str) -> str:
        return hashlib.sha256(f"{workspace}:{content}".encode()).hexdigest()[:16]

    def save(self, entry_type: str, content: str, tags: str = "",
             priority: int = 1, metadata: Optional[dict] = None) -> MemoryEntry:
        """Save a memory entry. Returns the saved entry with ID."""
        if entry_type not in self.MEMORY_TYPES:
            raise ValueError(f"Unknown entry_type '{entry_type}'. Must be one of: {self.MEMORY_TYPES}")

        entry = MemoryEntry(
            entry_type=entry_type,
            content=content,
            tags=tags,
            priority=priority,
            timestamp=time.time(),
            workspace=self.workspace,
            metadata=json.dumps(metadata or {}, ensure_ascii=False),
        )
        entry.content_hash = self._hash(content, self.workspace)

        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute(
                    """INSERT INTO memories
                       (entry_type, content, tags, priority, timestamp, workspace, metadata, content_hash)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (entry.entry_type, entry.content, entry.tags, entry.priority,
                     entry.timestamp, entry.workspace, entry.metadata, entry.content_hash)
                )
                entry.id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            except sqlite3.IntegrityError:
                # Duplicate - update existing
                conn.execute(
                    """UPDATE memories SET timestamp = ?, priority = ?, tags = ?, metadata = ?
                       WHERE content_hash = ?""",
                    (entry.timestamp, entry.priority, entry.tags, entry.metadata, entry.content_hash)
                )
                row = conn.execute(
                    "SELECT id FROM memories WHERE content_hash = ?",
                    (entry.content_hash,)
                ).fetchone()
                entry.id = row[0]

        return entry

    def get(self, entry_id: int) -> Optional[MemoryEntry]:
        """Get a single memory entry by ID."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (entry_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_entry(row)

    def search(self, query: str, entry_type: Optional[str] = None,
               limit: int = 20) -> list[MemoryEntry]:
        """Search memories by keyword matching content and tags."""
        conditions = []
        params = []

        if entry_type:
            conditions.append("entry_type = ?")
            params.append(entry_type)

        # Full-text search via LIKE (zero external deps)
        terms = query.lower().split()
        for term in terms:
            conditions.append("(LOWER(content) LIKE ? OR LOWER(tags) LIKE ?)")
            params.extend([f"%{term}%", f"%{term}%"])

        where = " AND ".join(conditions) if conditions else "1=1"

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                f"""SELECT * FROM memories WHERE {where}
                    ORDER BY priority DESC, timestamp DESC
                    LIMIT ?""",
                params + [limit]
            ).fetchall()

        return [self._row_to_entry(r) for r in rows]

    def list_all(self, entry_type: Optional[str] = None,
                 limit: int = 50, offset: int = 0) -> list[MemoryEntry]:
        """List all memories, optionally filtered by type."""
        conditions = []
        params = []

        if entry_type:
            conditions.append("entry_type = ?")
            params.append(entry_type)

        where = " AND ".join(conditions) if conditions else "1=1"

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                f"""SELECT * FROM memories WHERE {where}
                    ORDER BY priority DESC, timestamp DESC
                    LIMIT ? OFFSET ?""",
                params + [limit, offset]
            ).fetchall()

        return [self._row_to_entry(r) for r in rows]

    def delete(self, entry_id: int) -> bool:
        """Delete a memory entry by ID. Returns True if deleted."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memories WHERE id = ?", (entry_id,))
            return conn.total_changes > 0

    def count(self, entry_type: Optional[str] = None) -> int:
        """Count total memories."""
        with sqlite3.connect(self.db_path) as conn:
            if entry_type:
                row = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE entry_type = ?",
                    (entry_type,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM memories").fetchone()
            return row[0]

    def cleanup(self, days: int = 30, entry_type: Optional[str] = None) -> int:
        """Delete old entries. Returns count of deleted entries."""
        cutoff = time.time() - (days * 86400)
        conditions = ["timestamp < ?"]
        params = [cutoff]

        if entry_type:
            conditions.append("entry_type = ?")
            params.append(entry_type)

        where = " AND ".join(conditions)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"DELETE FROM memories WHERE {where}", params)
            return conn.total_changes

    def export_markdown(self, entry_type: Optional[str] = None) -> str:
        """Export memories as a markdown summary."""
        entries = self.list_all(entry_type=entry_type, limit=1000)
        if not entries:
            return "# Agent Memory\n\nNo entries found."

        lines = ["# Agent Memory Report", f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                 f"Workspace: {self.workspace}", f"Total entries: {len(entries)}\n"]

        by_type = {}
        for e in entries:
            by_type.setdefault(e.entry_type, []).append(e)

        type_labels = {
            "decision": "🎯 Decisions",
            "code_change": "💻 Code Changes",
            "lesson": "📚 Lessons Learned",
            "context": "📋 Context",
            "todo": "📝 To-Do",
            "preference": "⚙️ Preferences",
        }

        for t in self.MEMORY_TYPES:
            if t not in by_type:
                continue
            lines.append(f"\n## {type_labels.get(t, t)}\n")
            for e in sorted(by_type[t], key=lambda x: x.priority, reverse=True):
                priority_icon = {3: "🔴", 2: "🟡", 1: "⚪"}.get(e.priority, "⚪")
                dt = datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d")
                lines.append(f"- {priority_icon} [{dt}] {e.content}")
                if e.tags:
                    lines.append(f"  _Tags: {e.tags}_")

        return "\n".join(lines)

    def stats(self) -> dict:
        """Get memory statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

            type_counts = {}
            for row in conn.execute(
                "SELECT entry_type, COUNT(*) FROM memories GROUP BY entry_type"
            ):
                type_counts[row[0]] = row[1]

            priority_counts = {}
            for row in conn.execute(
                "SELECT priority, COUNT(*) FROM memories GROUP BY priority"
            ):
                priority_counts[str(row[0])] = row[1]

            if total > 0:
                oldest = conn.execute(
                    "SELECT timestamp FROM memories ORDER BY timestamp ASC LIMIT 1"
                ).fetchone()[0]
                newest = conn.execute(
                    "SELECT timestamp FROM memories ORDER BY timestamp DESC LIMIT 1"
                ).fetchone()[0]
            else:
                oldest = newest = None

        return {
            "total": total,
            "by_type": type_counts,
            "by_priority": priority_counts,
            "oldest": datetime.fromtimestamp(oldest).isoformat() if oldest else None,
            "newest": datetime.fromtimestamp(newest).isoformat() if newest else None,
            "db_size_mb": round(os.path.getsize(self.db_path) / 1024 / 1024, 2) if os.path.exists(self.db_path) else 0,
        }

    @staticmethod
    def _row_to_entry(row) -> MemoryEntry:
        return MemoryEntry(
            id=row[0], entry_type=row[1], content=row[2], tags=row[3],
            priority=row[4], timestamp=row[5], workspace=row[6],
            metadata=row[7],
        )
