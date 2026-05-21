"""Report generator — renders review results in multiple formats."""

from .rules import ReviewResult
from typing import Optional


class ReportGenerator:
    """Generate review reports in different formats."""

    @staticmethod
    def generate(result: ReviewResult, fmt: str = "markdown") -> str:
        if fmt == "markdown":
            return result.to_markdown()
        elif fmt == "html":
            return ReportGenerator._to_html(result)
        elif fmt == "json":
            import json
            return json.dumps({
                "summary": result.summary,
                "overall_score": result.overall_score,
                "changed_files": result.changed_files,
                "total_lines": result.total_lines,
                "issues": [
                    {
                        "severity": i.severity,
                        "category": i.category,
                        "file": i.file,
                        "line": i.line,
                        "description": i.description,
                        "suggestion": i.suggestion,
                    }
                    for i in result.issues
                ],
            }, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"Unknown format: {fmt}")

    @staticmethod
    def _to_html(result: ReviewResult) -> str:
        severity_colors = {
            "critical": "#ff4444",
            "warning": "#ffbb33",
            "info": "#33b5e5",
        }
        rows = ""
        for issue in result.issues:
            color = severity_colors.get(issue.severity, "#888")
            rows += f"""<tr>
                <td><span style="color:{color};font-weight:bold">{issue.severity.upper()}</span></td>
                <td>{issue.category}</td>
                <td><code>{issue.file}:{issue.line}</code></td>
                <td>{issue.description}</td>
                <td>{issue.suggestion}</td>
            </tr>\n"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Code Review Report</title>
<style>
body{{font-family:-apple-system,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#333}}
h1{{border-bottom:2px solid #d4a574;padding-bottom:.5rem}}
table{{width:100%;border-collapse:collapse;margin:1rem 0}}
th,td{{padding:.5rem;border:1px solid #ddd;text-align:left;font-size:.9rem}}
th{{background:#f5f5f5}}
.score{{font-size:3rem;font-weight:800;color:#d4a574}}
</style></head><body>
<h1>🔍 Code Review Report</h1>
<p class="score">{result.overall_score:.0f}/100</p>
<p>Files: {result.changed_files} | Lines: {result.total_lines} | Issues: {len(result.issues)}</p>
<h2>Summary</h2><p>{result.summary}</p>
<h2>Issues</h2>
<table>
<tr><th>Severity</th><th>Category</th><th>Location</th><th>Description</th><th>Suggestion</th></tr>
{rows}
</table>
</body></html>"""
        return html
