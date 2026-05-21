"""Tests for code review engine."""

import json
import unittest
from unittest.mock import patch, MagicMock

from bot.code_reviewer import CodeReviewer
from bot.rules import ReviewResult, ReviewIssue, RULE_CATEGORIES
from bot.report_generator import ReportGenerator


class TestRules(unittest.TestCase):
    def test_rule_categories_exist(self):
        self.assertIn("security", RULE_CATEGORIES)
        self.assertIn("performance", RULE_CATEGORIES)
        self.assertIn("best-practices", RULE_CATEGORIES)
        self.assertIn("naming", RULE_CATEGORIES)
        self.assertIn("architecture", RULE_CATEGORIES)

    def test_review_result_counts(self):
        result = ReviewResult(
            issues=[
                ReviewIssue("critical", "security", "app.py", 10, "SQL injection", "Use params", ""),
                ReviewIssue("warning", "performance", "app.py", 20, "N+1 query", "Use join", ""),
                ReviewIssue("info", "naming", "app.py", 30, "Bad name", "Rename x to user_id", ""),
            ]
        )
        self.assertEqual(result.critical_count, 1)
        self.assertEqual(result.warning_count, 1)
        self.assertEqual(result.info_count, 1)
        self.assertEqual(len(result.issues), 3)

    def test_review_result_markdown(self):
        result = ReviewResult(
            summary="Good code overall",
            overall_score=85.0,
            changed_files=2,
            total_lines=100,
        )
        md = result.to_markdown()
        self.assertIn("85", md)
        self.assertIn("Good code overall", md)

    def test_review_result_json_report(self):
        result = ReviewResult(
            summary="Test",
            overall_score=90.0,
            issues=[ReviewIssue("info", "naming", "x.py", 5, "desc", "suggestion", "")],
        )
        report = ReportGenerator.generate(result, fmt="json")
        data = json.loads(report)
        self.assertEqual(data["overall_score"], 90.0)
        self.assertEqual(len(data["issues"]), 1)


class TestReportGenerator(unittest.TestCase):
    def test_html_report(self):
        result = ReviewResult(
            summary="Test summary",
            overall_score=75.0,
            changed_files=1,
            total_lines=50,
            issues=[
                ReviewIssue("critical", "security", "auth.py", 10, "SQL injection", "Use params", ""),
            ],
        )
        html = ReportGenerator.generate(result, fmt="html")
        self.assertIn("<html>", html)
        self.assertIn("SQL injection", html)
        self.assertIn("75", html)

    def test_invalid_format(self):
        result = ReviewResult()
        with self.assertRaises(ValueError):
            ReportGenerator.generate(result, fmt="xml")


class TestCodeReviewer(unittest.TestCase):
    @patch("bot.code_reviewer.LLMClient")
    def test_review_diff_calls_llm(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.chat_json.return_value = {
            "issues": [],
            "summary": "No issues found",
            "overall_score": 100,
            "changed_files": 1,
            "total_lines": 10,
        }
        mock_client_cls.return_value = mock_client

        reviewer = CodeReviewer(model="qwen-plus", api_key="test-key")
        result = reviewer.review_diff("+++ test.py\n@@\n+print('hello')")

        self.assertEqual(result.overall_score, 100)
        self.assertEqual(len(result.issues), 0)
        mock_client.chat_json.assert_called_once()

    @patch("bot.code_reviewer.LLMClient")
    def test_review_diff_handles_errors(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.chat_json.side_effect = RuntimeError("API error")
        mock_client_cls.return_value = mock_client

        reviewer = CodeReviewer(model="qwen-plus", api_key="test-key")
        result = reviewer.review_diff("+++ test.py\n@@\n+print('hello')")

        self.assertIn("出错", result.summary)


if __name__ == "__main__":
    unittest.main()
