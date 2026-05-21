"""CLI entry point for code review bot."""

import argparse
import sys
import os

from .code_reviewer import CodeReviewer
from .report_generator import ReportGenerator


def main():
    parser = argparse.ArgumentParser(description="AI Code Review Bot")
    subparsers = parser.add_subparsers(dest="command")

    # Review diff
    p_review = subparsers.add_parser("review", help="Review a diff file")
    p_review.add_argument("--diff", required=True, help="Path to diff file")
    p_review.add_argument("--lang", default="python", help="Programming language")
    p_review.add_argument("--format", choices=["markdown", "html", "json"], default="markdown")
    p_review.add_argument("--output", help="Output file path")
    p_review.add_argument("--model", default="qwen-plus", help="LLM model name")

    # Review PR (placeholder)
    p_pr = subparsers.add_parser("review-pr", help="Review a GitHub PR")
    p_pr.add_argument("--repo", required=True, help="Owner/repo")
    p_pr.add_argument("--pr", type=int, required=True, help="PR number")
    p_pr.add_argument("--model", default="qwen-plus", help="LLM model name")

    args = parser.parse_args()

    if args.command == "review":
        with open(args.diff, "r") as f:
            diff_text = f.read()

        reviewer = CodeReviewer(model=args.model)
        result = reviewer.review_diff(diff_text, language=args.lang)

        report = ReportGenerator.generate(result, fmt=args.format)

        if args.output:
            with open(args.output, "w") as f:
                f.write(report)
            print(f"Report saved to {args.output}")
        else:
            print(report)

    elif args.command == "review-pr":
        # TODO: GitHub API integration
        print("GitHub PR review coming soon! Use `review` with a local diff for now.")
        print(f"Target: {args.repo}#{args.pr}")
        sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
