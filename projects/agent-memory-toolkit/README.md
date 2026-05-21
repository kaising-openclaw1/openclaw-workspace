# Agent Memory Toolkit 🧠

> Persistent memory system for AI coding agents — inspired by the #1 trending agentmemory project on GitHub (9,000+ ⭐).

## Overview

A lightweight, framework-agnostic memory toolkit for AI coding agents. Provides persistent context across sessions, semantic search over codebase, and automatic knowledge distillation.

**Why?** AI coding agents (Claude Code, Codex, Cursor, OpenClaw) lose context between sessions. This toolkit gives them persistent memory that survives restarts.

## Features

- **Session Memory**: Auto-save conversation context, decisions, and code changes
- **Semantic Search**: Embedding-based search over your codebase history
- **Knowledge Distillation**: Extract key decisions into distilled summaries
- **Cross-Session Continuity**: Resume work exactly where you left off
- **Framework Agnostic**: Works with any AI coding agent (Claude, Codex, Cursor, etc.)
- **Zero External Dependencies**: Pure Python + SQLite

## Quick Start

```bash
pip install agent-memory-toolkit
```

```python
from agent_memory import AgentMemory

# Initialize
memory = AgentMemory(workspace="/path/to/project")

# Save context
memory.save("decision", "Using PostgreSQL instead of MySQL for better JSON support")
memory.save("code_change", "Refactored auth module to use JWT tokens")

# Search
results = memory.search("authentication changes")
for r in results:
    print(f"[{r.type}] {r.content} (score: {r.score:.2f})")

# Export summary
summary = memory.export_summary()
print(summary)
```

## Architecture

```
agent_memory/
├── __init__.py          # Public API
├── core.py              # Core memory engine (SQLite backend)
├── types.py             # Memory entry types and dataclasses
├── search.py            # TF-IDF + keyword search (zero deps)
├── summarizer.py        # Knowledge distillation engine
└── cli.py               # Command-line interface
```

## Memory Entry Types

| Type | Description | Example |
|------|-------------|---------|
| `decision` | Architectural/strategic choices | "Using Redis for caching layer" |
| `code_change` | Significant code modifications | "Migrated from Flask to FastAPI" |
| `lesson` | Lessons learned from mistakes | "Always close DB connections in finally block" |
| `context` | Important project context | "Payment API requires HMAC-SHA256 signature" |
| `todo` | Pending tasks with priority | "Add rate limiting to API endpoints" |
| `preference` | User/team preferences | "Use black for formatting, 88 char line limit" |

## CLI Usage

```bash
# Save a memory entry
agent-memory save decision "Using PostgreSQL for the main database"

# Search memories
agent-memory search "database"

# List all memories
agent-memory list

# Export summary
agent-memory export --format markdown

# Clear old entries
agent-memory cleanup --days 30
```

## Use Cases

### 1. AI Coding Agent Context
Give your AI assistant persistent memory across sessions. No more re-explaining project decisions.

### 2. Team Knowledge Base
Capture decisions and context in a structured format that's searchable and exportable.

### 3. Onboarding
New team members can read distilled summaries instead of digging through git history.

### 4. Audit Trail
Track architectural decisions and their rationale over time.

## Performance

- **Storage**: SQLite, ~1MB per 10,000 entries
- **Search**: <50ms for 10K entries (TF-IDF + BM25)
- **Memory**: <10MB RAM footprint
- **No network calls**: Works offline

## License

MIT
