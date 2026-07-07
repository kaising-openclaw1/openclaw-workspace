#!/usr/bin/env python3
"""
Bounty Scanner — Scan GitHub for open-source bounty opportunities.

Zero external dependencies. Pure Python 3.8+.
"""

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

# ── Config ──────────────────────────────────────────────────────────────

GITHUB_API_BASE = "https://api.github.com"
REQUEST_DELAY = 0.5  # seconds between API calls (respect rate limits)
USER_AGENT = "bounty-scanner/1.0"

BOUNTY_LABELS = [
    "bounty",
    "paid",
    "💰",
    "bounty:",
    "reward",
    "bug bounty",
    "sponsored",
]

# ── Data Types ──────────────────────────────────────────────────────────


@dataclass
class BountyIssue:
    rank: int = 0
    title: str = ""
    url: str = ""
    repo: str = ""
    bounty_amount: int = 0
    bounty_currency: str = "$"
    labels: List[str] = field(default_factory=list)
    repo_stars: int = 0
    repo_last_push: str = ""
    issue_created: str = ""
    issue_updated: str = ""
    score: float = 0.0
    state: str = "open"
    body_preview: str = ""


# ── HTTP Helpers ────────────────────────────────────────────────────────


def _request(url: str) -> Union[Dict[str, Any], List[Any]]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github.v3+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data: dict | list = json.loads(resp.read().decode())
            return data
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f"  ⚠ Rate limited. Waiting 60s...", file=sys.stderr)
            time.sleep(60)
            return _request(url)
        print(f"  ⚠ HTTP {e.code} for {url}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  ⚠ Request failed: {e}", file=sys.stderr)
        return []


def _parse_bounty(title: str, labels: List[str], body: str = "") -> int:
    """Extract bounty amount from title, labels, or body."""
    # Check labels first
    for label in labels:
        m = re.search(r"[\$€£]?\s*(\d[\d,]*)\s*", label)
        if m:
            return int(m.group(1).replace(",", ""))

    # Check title
    patterns = [
        r"[\$€£]\s*(\d[\d,]*)",
        r"bounty[:\s]*[\$€£]?\s*(\d[\d,]*)",
        r"reward[:\s]*[\$€£]?\s*(\d[\d,]*)",
        r"(\d[\d,]*)\s*(?:USD|usd)",
    ]
    for pat in patterns:
        m = re.search(pat, title)
        if m:
            return int(m.group(1).replace(",", ""))

    # Check body (first 500 chars)
    if body:
        for pat in patterns:
            m = re.search(pat, body[:500])
            if m:
                return int(m.group(1).replace(",", ""))

    return 0


def _score_issue(issue: BountyIssue) -> float:
    """Score an issue by bounty amount, repo health, and freshness."""
    score = 0.0

    # Bounty amount (0-50 points)
    amount = issue.bounty_amount
    if amount >= 1000:
        score += 50
    elif amount >= 500:
        score += 40
    elif amount >= 200:
        score += 30
    elif amount >= 100:
        score += 20
    elif amount >= 50:
        score += 10
    elif amount > 0:
        score += 5

    # Repo stars (0-25 points)
    stars = issue.repo_stars
    if stars >= 10000:
        score += 25
    elif stars >= 5000:
        score += 20
    elif stars >= 1000:
        score += 15
    elif stars >= 100:
        score += 10
    elif stars >= 10:
        score += 5

    # Freshness (0-25 points)
    if issue.issue_created:
        try:
            created = datetime.fromisoformat(
                issue.issue_created.replace("Z", "+00:00")
            )
            days_old = (datetime.now(timezone.utc) - created).days
            if days_old <= 7:
                score += 25
            elif days_old <= 30:
                score += 20
            elif days_old <= 90:
                score += 15
            elif days_old <= 180:
                score += 10
            else:
                score += 5
        except Exception:
            pass

    return min(score, 100.0)


# ── Search ──────────────────────────────────────────────────────────────


def search_github(
    language: str = "",
    max_results: int = 20,
    min_bounty: int = 0,
) -> List[BountyIssue]:
    """Search GitHub Issues for bounty-labeled issues."""
    results: List[BountyIssue] = []

    # Build query
    query_parts = ['is:issue', 'is:open']
    label_query = " ".join(f'label:"{l}"' for l in BOUNTY_LABELS)
    query_parts.append(f"({label_query})")
    if language:
        query_parts.append(f"language:{language}")

    query = " ".join(query_parts)
    encoded_query = urllib.parse.quote(query)

    # Search issues
    url = (
        f"{GITHUB_API_BASE}/search/issues"
        f"?q={encoded_query}"
        f"&sort=created"
        f"&order=desc"
        f"&per_page={min(max_results, 100)}"
    )

    print(f"🔍 Searching: {query}", file=sys.stderr)
    data = _request(url)
    if not data or not isinstance(data, dict):
        print("  ⚠ No results from API", file=sys.stderr)
        return results

    items = data.get("items", [])
    print(f"  Found {len(items)} potential issues", file=sys.stderr)

    for item in items[:max_results]:
        repo_full_name = item.get("repository_url", "").replace(
            f"{GITHUB_API_BASE}/repos/", ""
        )
        labels = [lbl.get("name", "") for lbl in item.get("labels", [])]
        body = item.get("body") or ""

        bounty_amount = _parse_bounty(
            item.get("title", ""), labels, body
        )

        if min_bounty > 0 and bounty_amount < min_bounty:
            continue

        # Fetch repo info
        repo_stars = 0
        repo_last_push = ""
        if repo_full_name:
            repo_data = _request(f"{GITHUB_API_BASE}/repos/{repo_full_name}")
            if isinstance(repo_data, dict):
                repo_stars = repo_data.get("stargazers_count", 0)
                repo_last_push = repo_data.get("pushed_at", "")
            time.sleep(REQUEST_DELAY)

        issue = BountyIssue(
            title=item.get("title", ""),
            url=item.get("html_url", ""),
            repo=repo_full_name,
            bounty_amount=bounty_amount,
            bounty_currency="$",
            labels=labels,
            repo_stars=repo_stars,
            repo_last_push=repo_last_push or "",
            issue_created=item.get("created_at", ""),
            issue_updated=item.get("updated_at", ""),
            state=item.get("state", "open"),
            body_preview=body[:200] if body else "",
        )
        issue.score = _score_issue(issue)
        results.append(issue)
        time.sleep(REQUEST_DELAY)

    # Sort by score descending
    results.sort(key=lambda x: x.score, reverse=True)
    for i, r in enumerate(results, 1):
        r.rank = i

    return results


# ── Output ──────────────────────────────────────────────────────────────


def print_table(results: List[BountyIssue]) -> None:
    """Print results as a formatted table."""
    if not results:
        print("\n  No bounty issues found. Try different search terms.")
        return

    # Header
    print()
    print("┌──────┬──────────────────────────────────────────────────┬──────────┬──────────┐")
    print("│ Rank │ Issue                                            │ Bounty   │  Score   │")
    print("├──────┼──────────────────────────────────────────────────┼──────────┼──────────┤")

    for r in results[:15]:  # Show top 15
        title = r.title[:48] + ".." if len(r.title) > 48 else r.title
        bounty_str = f"{r.bounty_currency}{r.bounty_amount}" if r.bounty_amount > 0 else "TBD"
        score_str = f"{r.score:.0f}/100"
        print(
            f"│ {r.rank:>4} │ {title:<48} │ {bounty_str:>8} │ {score_str:>8} │"
        )

    print("└──────┴──────────────────────────────────────────────────┴──────────┴──────────┘")
    print(f"\n  Showing top {min(len(results), 15)} of {len(results)} results")
    print()


def print_json(results: List[BountyIssue]) -> None:
    """Print results as JSON."""
    data = [asdict(r) for r in results]
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ── CLI ─────────────────────────────────────────────────────────────────


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Bounty Scanner — Find paid GitHub issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bounty_scanner.py --language python
  python bounty_scanner.py --language python --min-bounty 100
  python bounty_scanner.py --language python,javascript --max-results 30
  python bounty_scanner.py --language python --output bounties.json
        """,
    )
    parser.add_argument(
        "--language", "-l",
        default="",
        help="Programming language filter (comma-separated for multiple)",
    )
    parser.add_argument(
        "--max-results", "-n",
        type=int,
        default=20,
        help="Maximum results to return (default: 20)",
    )
    parser.add_argument(
        "--min-bounty", "-m",
        type=int,
        default=0,
        help="Minimum bounty amount to filter (default: 0 = any)",
    )
    parser.add_argument(
        "--output", "-o",
        default="",
        help="Output file path (JSON format). Prints to stdout if omitted.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON to stdout",
    )

    args = parser.parse_args()

    print(f"\n  🎯 Bounty Scanner v1.0", file=sys.stderr)
    print(f"  {'=' * 40}", file=sys.stderr)

    all_results: List[BountyIssue] = []
    languages = [l.strip() for l in args.language.split(",") if l.strip()]

    if languages:
        for lang in languages:
            results = search_github(
                language=lang,
                max_results=args.max_results,
                min_bounty=args.min_bounty,
            )
            all_results.extend(results)
        # Re-rank combined results
        all_results.sort(key=lambda x: x.score, reverse=True)
        for i, r in enumerate(all_results, 1):
            r.rank = i
    else:
        all_results = search_github(
            language="",
            max_results=args.max_results,
            min_bounty=args.min_bounty,
        )

    if args.output:
        data = [asdict(r) for r in all_results]
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n  ✅ Results saved to {args.output}", file=sys.stderr)

    if args.json:
        print_json(all_results)
    else:
        print_table(all_results)


if __name__ == "__main__":
    main()
