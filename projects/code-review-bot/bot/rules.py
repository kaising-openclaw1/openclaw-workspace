"""Review rules — predefined code review checklists."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ReviewIssue:
    """A single issue found during code review."""
    severity: str  # critical, warning, info
    category: str  # security, performance, best-practices, naming, architecture
    file: str
    line: int
    description: str
    suggestion: str
    code_snippet: str = ""


@dataclass
class ReviewResult:
    """Complete review result for a diff."""
    issues: List[ReviewIssue] = field(default_factory=list)
    summary: str = ""
    overall_score: float = 0.0  # 0-100
    changed_files: int = 0
    total_lines: int = 0

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "info")

    def to_markdown(self) -> str:
        """Render review result as markdown."""
        lines = [f"## Code Review Report\n"]
        lines.append(f"**Overall Score:** {self.overall_score:.0f}/100\n")
        lines.append(f"**Files Changed:** {self.changed_files} | **Lines:** {self.total_lines}\n")

        if self.critical_count:
            lines.append(f"🚨 **{self.critical_count} Critical Issues**\n")
        if self.warning_count:
            lines.append(f"⚠️  **{self.warning_count} Warnings**\n")
        if self.info_count:
            lines.append(f"ℹ️  **{self.info_count} Suggestions**\n")

        lines.append("---\n")
        lines.append(self.summary)
        lines.append("\n---\n")
        lines.append("### Issues\n")

        for issue in self.issues:
            emoji = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(issue.severity, "📌")
            lines.append(f"{emoji} **[{issue.severity.upper()}]** `{issue.file}:{issue.line}`")
            lines.append(f"   - {issue.description}")
            if issue.suggestion:
                lines.append(f"   - 💡 {issue.suggestion}")
            if issue.code_snippet:
                lines.append(f"   ```\n   {issue.code_snippet}\n   ```")
            lines.append("")

        return "\n".join(lines)


# Rule categories for code review
RULE_CATEGORIES = {
    "security": {
        "name": "Security",
        "description": "Detect security vulnerabilities",
        "checks": [
            "SQL injection (f-string/sql concatenation)",
            "XSS (unescaped output)",
            "Hardcoded secrets / API keys / passwords",
            "Path traversal (unsanitized file paths)",
            "Insecure deserialization (pickle, yaml.load)",
            "Command injection (os.system, subprocess with shell=True)",
            "Missing authentication / authorization checks",
            "Insecure random (random module for security purposes)",
            "SSRF (user-controlled URLs)",
            "Sensitive data in logs",
        ],
    },
    "performance": {
        "name": "Performance",
        "description": "Identify performance issues",
        "checks": [
            "N+1 query pattern",
            "Unbounded loops / recursion",
            "Memory leaks (unclosed resources)",
            "Inefficient string concatenation in loops",
            "Missing indexes on database queries",
            "Synchronous calls in async context",
            "Redundant computations (no memoization)",
            "Large payload without pagination",
        ],
    },
    "best-practices": {
        "name": "Best Practices",
        "description": "Code quality and maintainability",
        "checks": [
            "Missing error handling (bare except, no logging)",
            "Magic numbers / strings without constants",
            "Functions too long (>50 lines)",
            "Duplicated code blocks",
            "Missing type hints in public APIs",
            "No docstrings for public functions/classes",
            "Improper logging (print instead of logger)",
            "Unused imports / variables",
        ],
    },
    "naming": {
        "name": "Naming Conventions",
        "description": "Naming style and clarity",
        "checks": [
            "Non-descriptive variable names (x, tmp, data)",
            "Inconsistent naming style",
            "Boolean variables not prefixed with is_/has_/can_",
            "Class names not PascalCase",
            "Function names not snake_case",
            "Constants not UPPER_SNAKE_CASE",
        ],
    },
    "architecture": {
        "name": "Architecture",
        "description": "Design and structure issues",
        "checks": [
            "Circular imports / dependencies",
            "God class / too many responsibilities",
            "Violation of SOLID principles",
            "Tight coupling between modules",
            "Missing separation of concerns",
            "Business logic in presentation layer",
        ],
    },
}
