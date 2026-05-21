"""Tests for Agent Memory Toolkit."""

import os
import tempfile
import time
from agent_memory.core import AgentMemory, MemoryEntry


def _make_memory(tmpdir):
    db = os.path.join(tmpdir, "test.db")
    return AgentMemory(workspace=tmpdir, db_path=db)


def test_save_and_get():
    with tempfile.TemporaryDirectory() as d:
        m = _make_memory(d)
        entry = m.save("decision", "Use PostgreSQL for main database", tags="db")
        assert entry.id is not None
        assert entry.entry_type == "decision"
        assert entry.content == "Use PostgreSQL for main database"

        fetched = m.get(entry.id)
        assert fetched is not None
        assert fetched.content == entry.content


def test_duplicate_handling():
    with tempfile.TemporaryDirectory() as d:
        m = _make_memory(d)
        e1 = m.save("decision", "Use Redis for caching")
        e2 = m.save("decision", "Use Redis for caching")
        assert e1.id == e2.id
        assert m.count() == 1


def test_search():
    with tempfile.TemporaryDirectory() as d:
        m = _make_memory(d)
        m.save("decision", "Use PostgreSQL for database")
        m.save("lesson", "Close DB connections in finally block")
        m.save("context", "Payment API needs HMAC signature")

        results = m.search("database")
        assert len(results) == 1
        assert results[0].entry_type == "decision"

        results = m.search("DB")
        assert len(results) == 2  # "database" + "DB connections"


def test_search_by_type():
    with tempfile.TemporaryDirectory() as d:
        m = _make_memory(d)
        m.save("decision", "Use PostgreSQL")
        m.save("lesson", "PostgreSQL needs tuning")

        results = m.search("PostgreSQL", entry_type="decision")
        assert len(results) == 1
        assert results[0].entry_type == "decision"


def test_list_all():
    with tempfile.TemporaryDirectory() as d:
        m = _make_memory(d)
        for i in range(15):
            m.save("todo", f"Task {i}")

        results = m.list_all(limit=5)
        assert len(results) == 5


def test_delete():
    with tempfile.TemporaryDirectory() as d:
        m = _make_memory(d)
        entry = m.save("context", "Test context")
        assert m.delete(entry.id)
        assert m.get(entry.id) is None
        assert not m.delete(99999)


def test_cleanup():
    with tempfile.TemporaryDirectory() as d:
        m = _make_memory(d)
        m.save("decision", "Old decision")
        # Manually backdate one entry
        import sqlite3
        with sqlite3.connect(m.db_path) as conn:
            conn.execute(
                "UPDATE memories SET timestamp = ?",
                (time.time() - 60 * 86400,)  # 60 days ago
            )

        count = m.cleanup(days=30)
        assert count == 1
        assert m.count() == 0


def test_export_markdown():
    with tempfile.TemporaryDirectory() as d:
        m = _make_memory(d)
        m.save("decision", "Use PostgreSQL", priority=3)
        m.save("lesson", "Always close connections", priority=2)

        md = m.export_markdown()
        assert "PostgreSQL" in md
        assert "Always close connections" in md
        assert "🔴" in md  # priority 3 icon


def test_stats():
    with tempfile.TemporaryDirectory() as d:
        m = _make_memory(d)
        m.save("decision", "A")
        m.save("lesson", "B")
        m.save("todo", "C")

        stats = m.stats()
        assert stats["total"] == 3
        assert stats["by_type"]["decision"] == 1
        assert stats["by_type"]["lesson"] == 1
        assert stats["by_type"]["todo"] == 1
        assert stats["db_size_mb"] > 0


def test_invalid_type():
    with tempfile.TemporaryDirectory() as d:
        m = _make_memory(d)
        try:
            m.save("invalid_type", "test")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


def test_priority_ordering():
    with tempfile.TemporaryDirectory() as d:
        m = _make_memory(d)
        m.save("todo", "Low priority task", priority=1)
        m.save("todo", "Critical task", priority=3)
        m.save("todo", "Normal task", priority=1)

        results = m.list_all(entry_type="todo")
        assert results[0].priority == 3  # Critical first
        assert results[0].content == "Critical task"


if __name__ == "__main__":
    import sys
    tests = [
        test_save_and_get, test_duplicate_handling, test_search,
        test_search_by_type, test_list_all, test_delete,
        test_cleanup, test_export_markdown, test_stats,
        test_invalid_type, test_priority_ordering,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"✅ {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"❌ {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
