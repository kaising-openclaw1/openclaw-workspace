"""CLI for Agent Memory Toolkit."""

import argparse
import sys
import os
from .core import AgentMemory


def main():
    parser = argparse.ArgumentParser(
        description="Agent Memory Toolkit - Persistent memory for AI coding agents"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # save
    save_parser = subparsers.add_parser("save", help="Save a memory entry")
    save_parser.add_argument("entry_type", choices=AgentMemory.MEMORY_TYPES)
    save_parser.add_argument("content", help="Memory content")
    save_parser.add_argument("--tags", default="", help="Comma-separated tags")
    save_parser.add_argument("--priority", type=int, default=1, choices=[1, 2, 3])

    # search
    search_parser = subparsers.add_parser("search", help="Search memories")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--type", dest="entry_type", default=None)
    search_parser.add_argument("--limit", type=int, default=20)

    # list
    list_parser = subparsers.add_parser("list", help="List all memories")
    list_parser.add_argument("--type", dest="entry_type", default=None)
    list_parser.add_argument("--limit", type=int, default=50)

    # export
    export_parser = subparsers.add_parser("export", help="Export as markdown")
    export_parser.add_argument("--format", default="markdown", choices=["markdown"])
    export_parser.add_argument("--type", dest="entry_type", default=None)

    # cleanup
    cleanup_parser = subparsers.add_parser("cleanup", help="Delete old entries")
    cleanup_parser.add_argument("--days", type=int, default=30)
    cleanup_parser.add_argument("--type", dest="entry_type", default=None)

    # stats
    subparsers.add_parser("stats", help="Show memory statistics")

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete a memory entry")
    delete_parser.add_argument("id", type=int, help="Entry ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    memory = AgentMemory()

    if args.command == "save":
        entry = memory.save(args.entry_type, args.content, args.tags, args.priority)
        print(f"Saved: [{entry.entry_type}] {entry.content[:60]}... (ID: {entry.id})")

    elif args.command == "search":
        results = memory.search(args.query, args.entry_type, args.limit)
        if not results:
            print("No results found.")
            return
        for r in results:
            icon = {3: "🔴", 2: "🟡", 1: "⚪"}.get(r.priority, "⚪")
            print(f"  {icon} [{r.entry_type}] {r.content[:80]}")
        print(f"\nFound {len(results)} results.")

    elif args.command == "list":
        entries = memory.list_all(args.entry_type, args.limit)
        if not entries:
            print("No entries found.")
            return
        for e in entries:
            icon = {3: "🔴", 2: "🟡", 1: "⚪"}.get(e.priority, "⚪")
            print(f"  #{e.id} {icon} [{e.entry_type}] {e.content[:80]}")
        print(f"\nShowing {len(entries)} of {memory.count()} entries.")

    elif args.command == "export":
        md = memory.export_markdown(args.entry_type)
        print(md)

    elif args.command == "cleanup":
        count = memory.cleanup(args.days, args.entry_type)
        print(f"Deleted {count} entries older than {args.days} days.")

    elif args.command == "stats":
        stats = memory.stats()
        print(f"Total entries: {stats['total']}")
        print(f"By type: {stats['by_type']}")
        print(f"DB size: {stats['db_size_mb']} MB")

    elif args.command == "delete":
        if memory.delete(args.id):
            print(f"Deleted entry #{args.id}")
        else:
            print(f"Entry #{args.id} not found")


if __name__ == "__main__":
    main()
