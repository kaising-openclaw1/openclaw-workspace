"""
EvalReporter - 评估报告生成器

支持多种输出格式：
- JSON
- Markdown
- HTML
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from .evaluator import EvalResult


class EvalReporter:
    """评估报告生成"""

    def __init__(self, agent_name: str = "Unnamed Agent", model: str = "unknown"):
        self.agent_name = agent_name
        self.model = model
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate(
        self,
        results: List[EvalResult],
        fmt: str = "markdown",
        stress_tests: Optional[List[Dict]] = None,
    ) -> str:
        if fmt == "json":
            return self._as_json(results, stress_tests)
        elif fmt == "html":
            return self._as_html(results, stress_tests)
        else:
            return self._as_markdown(results, stress_tests)

    def _as_json(self, results: List[EvalResult], stress_tests: Optional[List[Dict]]) -> str:
        report = self._build_report_dict(results, stress_tests)
        return json.dumps(report, indent=2, ensure_ascii=False)

    def _as_markdown(self, results: List[EvalResult], stress_tests: Optional[List[Dict]]) -> str:
        lines = [
            f"# AI Agent 评估报告",
            f"",
            f"- **Agent:** {self.agent_name}",
            f"- **模型:** {self.model}",
            f"- **评估时间:** {self.timestamp}",
            f"",
        ]

        # 总体统计
        total = len(results)
        success_count = sum(1 for r in results if r.success)
        avg_score = sum(r.score for r in results) / total if total else 0
        avg_latency = sum(r.latency_ms for r in results) / total if total else 0
        total_cost = sum(r.cost_usd for r in results)

        lines.extend([
            "## 总体表现\n",
            f"| 指标 | 值 |",
            f"|------|-----|",
            f"| 总任务数 | {total} |",
            f"| 成功数 | {success_count} |",
            f"| 成功率 | {success_count/total*100:.1f}% |",
            f"| 平均得分 | {avg_score:.1f}/100 |",
            f"| 平均延迟 | {avg_latency:.0f}ms |",
            f"| 总成本 | ${total_cost:.6f} |",
            "",
        ])

        # 得分分布
        excellent = sum(1 for r in results if r.score >= 90)
        good = sum(1 for r in results if 70 <= r.score < 90)
        fair = sum(1 for r in results if 50 <= r.score < 70)
        poor = sum(1 for r in results if r.score < 50)

        lines.extend([
            "## 得分分布\n",
            f"- 🔴 优秀 (90-100): {excellent}",
            f"- 🟡 良好 (70-89): {good}",
            f"- 🟠 一般 (50-69): {fair}",
            f"- ⚫ 较差 (<50): {poor}",
            "",
        ])

        # 分类表现
        by_cat: Dict[str, List[EvalResult]] = {}
        for r in results:
            by_cat.setdefault(r.category, []).append(r)

        lines.extend(["## 分类表现\n", "| 分类 | 任务数 | 平均分 | 成功率 | 平均延迟 |"])
        lines.extend(["|------|--------|--------|--------|----------|"])
        for cat, cat_results in sorted(by_cat.items()):
            avg = sum(r.score for r in cat_results) / len(cat_results)
            succ = sum(1 for r in cat_results if r.success)
            lat = sum(r.latency_ms for r in cat_results) / len(cat_results)
            lines.append(f"| {cat} | {len(cat_results)} | {avg:.1f} | {succ/len(cat_results)*100:.0f}% | {lat:.0f}ms |")

        lines.append("")

        # 详细结果
        lines.extend(["## 详细结果\n", "| # | 任务 | 分类 | 得分 | 状态 | 延迟 | 成本 |"])
        lines.extend(["|---|------|------|------|------|------|------|"])
        for i, r in enumerate(results, 1):
            status = "✅" if r.success else "❌"
            lines.append(
                f"| {i} | {r.task_name} | {r.category} "
                f"| {r.score:.1f} | {status} "
                f"| {r.latency_ms:.0f}ms | ${r.cost_usd:.6f} |"
            )

        # 压力测试
        if stress_tests:
            lines.extend(["\n## 压力测试\n"])
            for st in stress_tests:
                lines.extend([
                    f"### {st['task_name']}\n",
                    f"- 迭代次数: {st['iterations']}",
                    f"- 平均延迟: {st['latency_mean_ms']:.0f}ms (P99: {st['latency_p99_ms']:.0f}ms)",
                    f"- 平均得分: {st['score_mean']:.1f}",
                    f"- 一致性: {st['consistency']:.2%}",
                    f"- 成功率: {st['success_rate']:.2%}",
                    f"- 总成本: ${st['cost_total_usd']:.6f}",
                    "",
                ])

        lines.extend([
            "---",
            f"*报告生成时间: {self.timestamp}*",
        ])

        return "\n".join(lines)

    def _as_html(self, results: List[EvalResult], stress_tests: Optional[List[Dict]]) -> str:
        """生成 HTML 报告"""
        md = self._as_markdown(results, stress_tests)
        # 简单 Markdown → HTML 转换
        html = md
        import re
        # Headers
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        # Bold
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        # Line breaks
        html = html.replace('\n', '<br>\n')
        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Agent Evaluation Report</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f5f5f5; }}
</style>
</head>
<body>
{html}
</body>
</html>"""

    def _build_report_dict(self, results: List[EvalResult], stress_tests: Optional[List[Dict]]) -> Dict:
        total = len(results)
        return {
            "agent_name": self.agent_name,
            "model": self.model,
            "timestamp": self.timestamp,
            "total_tasks": total,
            "success_count": sum(1 for r in results if r.success),
            "success_rate": round(sum(1 for r in results if r.success) / total, 4) if total else 0,
            "avg_score": round(sum(r.score for r in results) / total, 2) if total else 0,
            "avg_latency_ms": round(sum(r.latency_ms for r in results) / total, 2) if total else 0,
            "total_cost_usd": round(sum(r.cost_usd for r in results), 6),
            "results": [
                {
                    "task": r.task_name,
                    "category": r.category,
                    "score": r.score,
                    "success": r.success,
                    "latency_ms": r.latency_ms,
                    "cost_usd": r.cost_usd,
                }
                for r in results
            ],
            "stress_tests": stress_tests or [],
        }
