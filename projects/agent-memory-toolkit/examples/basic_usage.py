"""Basic usage examples for Agent Memory Toolkit."""

from agent_memory import AgentMemory


def main():
    # 初始化
    memory = AgentMemory(workspace="/tmp/demo-project")

    # 清空旧数据（仅用于演示）
    memory.cleanup(days=0)

    # === 保存记忆 ===
    print("=== 保存记忆 ===")

    memory.save(
        "decision",
        "使用 PostgreSQL 替代 MySQL，因为需要更好的 JSON 支持和 CTE 查询",
        tags="database,architecture",
        priority=3,
    )
    memory.save(
        "decision",
        "采用 JWT + Redis 做认证，替代传统的 Session 方案",
        tags="auth,security",
        priority=3,
    )
    memory.save(
        "code_change",
        "将用户认证逻辑从 views.py 拆分为独立的 auth_service.py",
        tags="refactoring,auth",
    )
    memory.save(
        "lesson",
        "DB 连接必须在 finally 块中关闭，否则高并发下会导致连接泄漏（已踩坑）",
        tags="database,best-practice",
        priority=2,
    )
    memory.save(
        "lesson",
        "Redis 连接池大小必须根据并发数调整，默认值在压测时会超时",
        tags="redis,performance",
        priority=2,
    )
    memory.save(
        "context",
        "支付 API 要求 HMAC-SHA256 签名，请求头需包含 X-Timestamp 和 X-Nonce",
        tags="payment,api",
        priority=2,
    )
    memory.save(
        "todo",
        "添加 API 速率限制（建议 100 req/min）",
        tags="api,security",
        priority=1,
    )
    memory.save(
        "preference",
        "代码格式化使用 black，行宽 88，不使用分号",
        tags="style,python",
    )

    print("已保存 8 条记忆\n")

    # === 搜索 ===
    print("=== 搜索 'database' ===")
    results = memory.search("database")
    for r in results:
        print(f"  [{r.entry_type}] {r.content[:60]}...")

    print("\n=== 搜索 'auth' ===")
    results = memory.search("auth")
    for r in results:
        print(f"  [{r.entry_type}] {r.content[:60]}...")

    # === 按类型查询 ===
    print("\n=== 所有教训 ===")
    lessons = memory.list_all(entry_type="lesson")
    for l in lessons:
        print(f"  [{l.priority}⭐] {l.content[:60]}...")

    # === 统计 ===
    print("\n=== 统计 ===")
    stats = memory.stats()
    print(f"总数: {stats['total']}")
    print(f"按类型: {stats['by_type']}")
    print(f"数据库大小: {stats['db_size_mb']} MB")

    # === 导出 ===
    print("\n=== 导出 Markdown ===")
    md = memory.export_markdown()
    print(md[:500] + "...\n")

    # === 清理 ===
    print("=== 清理 ===")
    count = memory.cleanup(days=30)
    print(f"清理了 {count} 条旧记录")


if __name__ == "__main__":
    main()
