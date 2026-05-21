"""Core code review engine — orchestrates LLM-based analysis."""

import json
from typing import List, Optional

from .llm_client import LLMClient
from .rules import ReviewIssue, ReviewResult, RULE_CATEGORIES

SYSTEM_PROMPT = """你是一个资深的高级软件工程师，拥有 15 年以上的代码审查经验。
你的任务是审查代码变更，发现潜在问题并给出建设性建议。

请严格遵循以下规则：
1. 只报告真实存在的问题，不要为了凑数而编造
2. 每个问题都要包含：文件路径、行号、问题描述、修复建议
3. 按照严重程度分类：critical（必须修复）、warning（建议修复）、info（可选优化）
4. 用中文描述问题，代码示例保持英文
5. 最后给出总体评分（0-100）和审查摘要"""


class CodeReviewer:
    """AI-powered code review engine."""

    def __init__(self, model: str = "qwen-plus", api_key: Optional[str] = None):
        self.llm = LLMClient(model=model, api_key=api_key)

    def review_diff(self, diff_text: str, language: str = "python",
                    rules: Optional[List[str]] = None) -> ReviewResult:
        """Review a git diff and return structured results."""
        rules = rules or list(RULE_CATEGORIES.keys())

        active_rules = {}
        for r in rules:
            if r in RULE_CATEGORIES:
                active_rules[r] = RULE_CATEGORIES[r]

        rule_text = json.dumps(active_rules, ensure_ascii=False, indent=2)

        user_prompt = f"""请审查以下代码变更。

语言：{language}
审查维度：
{rule_text}

代码变更（git diff 格式）：
```diff
{diff_text}
```

请以 JSON 格式返回审查结果，格式如下：
{{
    "issues": [
        {{
            "severity": "critical|warning|info",
            "category": "security|performance|best-practices|naming|architecture",
            "file": "文件路径",
            "line": 行号,
            "description": "问题描述",
            "suggestion": "修复建议",
            "code_snippet": "相关代码片段"
        }}
    ],
    "summary": "总体审查总结",
    "overall_score": 85,
    "changed_files": 3,
    "total_lines": 150
}}

如果没有发现问题，issues 返回空数组。"""

        try:
            result = self.llm.chat_json(SYSTEM_PROMPT, user_prompt)
            return self._parse_result(result)
        except Exception as e:
            # Fallback: return a result with the error noted
            return ReviewResult(
                summary=f"审查过程中出错：{str(e)}",
                overall_score=50.0,
            )

    def review_file(self, file_path: str, source_code: str,
                    language: str = "python",
                    rules: Optional[List[str]] = None) -> ReviewResult:
        """Review a single file's source code."""
        diff_text = f"+++ {file_path}\n@@\n{source_code}"
        return self.review_diff(diff_text, language=language, rules=rules)

    def _parse_result(self, data: dict) -> ReviewResult:
        """Parse LLM JSON response into ReviewResult."""
        result = ReviewResult(
            summary=data.get("summary", ""),
            overall_score=float(data.get("overall_score", 50)),
            changed_files=data.get("changed_files", 0),
            total_lines=data.get("total_lines", 0),
        )

        for issue_data in data.get("issues", []):
            issue = ReviewIssue(
                severity=issue_data.get("severity", "info"),
                category=issue_data.get("category", "best-practices"),
                file=issue_data.get("file", "unknown"),
                line=issue_data.get("line", 0),
                description=issue_data.get("description", ""),
                suggestion=issue_data.get("suggestion", ""),
                code_snippet=issue_data.get("code_snippet", ""),
            )
            result.issues.append(issue)

        return result
