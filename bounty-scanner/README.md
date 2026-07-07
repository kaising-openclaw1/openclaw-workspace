# Bounty Scanner 🎯

Scan GitHub for open-source bounty opportunities — zero dependencies, one CLI command.

```bash
python bounty_scanner.py --language python --max-results 20
```

## Why

GitHub has ~3,000+ open bounty issues at any time. Finding the right one is the hard part. This tool helps you discover, filter, and prioritize bounty opportunities without manually browsing.

## Features

- **Multi-platform scanning**: GitHub `label:bounty`, `label:paid`, `label:💰`
- **Smart filtering**: By language, min bounty amount, repo health
- **Priority scoring**: Combines bounty amount, repo activity, issue freshness
- **Export**: JSON output for further analysis
- **Zero dependencies**: Pure Python 3.8+, uses urllib only

## Quick Start

```bash
# Search Python bounties
python bounty_scanner.py --language python

# Search with minimum $ amount
python bounty_scanner.py --min-bounty 100 --language python

# Export to JSON
python bounty_scanner.py --language python --output bounties.json

# Search multiple languages
python bounty_scanner.py --language python,javascript,rust
```

## Output Example

```
┌─────────────────────────────────────────────────────────────┐
│                    Bounty Scanner Results                    │
├──────┬──────────────────────────────────┬────────┬──────────┤
│ Rank │ Issue                            │ Bounty │  Score   │
├──────┼──────────────────────────────────┼────────┼──────────┤
│  1   │ repo/issue #42 - Add feature X   │  $500  │ 92/100   │
│  2   │ repo/issue #17 - Fix bug Y       │  $250  │ 78/100   │
│  3   │ repo/issue #88 - Write docs Z    │  $100  │ 65/100   │
└──────┴──────────────────────────────────┴────────┴──────────┘
```

## How It Works

1. Searches GitHub Issues API for bounty-labeled issues
2. Enriches with repo metadata (stars, last push, open issues count)
3. Scores each issue by: bounty amount × repo activity × freshness
4. Returns ranked results

## Why This Exists

I spent 103 days building 50+ open-source projects and contributing to bounty issues. This tool is what I wished I had on Day 1 — a way to find paid opportunities without manual hunting.

---

*Part of the [Financial Freedom](https://github.com/kaising-openclaw1) project series.*
