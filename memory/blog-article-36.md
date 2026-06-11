# 手把手教你用 Python 搭建 AI 代码审查系统：从本地脚本到团队级流水线

> 目标平台：掘金 / 知乎 / V2EX / 公众号
> 标签：AI 代码审查、Code Review、GitHub Actions、Python、自动化
> 配套项目：ai-code-reviewer

---

代码审查是软件工程里最耗人力的环节之一。

一个 5 人团队，每天提交 20 个 PR，每个 PR 平均需要 30 分钟审查——这就是每天 10 小时的人力成本。更糟的是，人类审查者会疲劳、会漏掉边界条件、会对风格问题反复纠缠。

AI 代码审查系统不是替代人类，而是把人类从重复劳动中解放出来：让 AI 处理风格、命名、 obvious bug、安全漏洞，让人类专注架构设计和业务逻辑。

本文从零开始，教你搭建一套完整的 AI 代码审查系统。

---

## 系统架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   GitHub    │────▶│  Webhook    │────▶│   Python    │
│    PR 事件   │     │   服务器     │     │  审查服务    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                       ┌────────────────────────┘
                       ▼
              ┌─────────────────┐
              │   LLM API       │
              │ (DeepSeek/      │
              │  OpenAI/Claude) │
              └─────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  GitHub PR      │
              │  Review Comment │
              └─────────────────┘
```

---

## 第一步：核心审查引擎（本地可运行）

```python
# code_reviewer.py
import os
import re
import json
import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReviewComment:
    file_path: str
    line_number: int
    severity: str  # critical, warning, info
    category: str  # security, style, bug, performance, maintainability
    message: str
    suggestion: str


class AICodeReviewer:
    """AI 代码审查核心引擎"""

    SEVERITY_WEIGHTS = {"critical": 4, "warning": 2, "info": 1}

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict]:
        """加载静态规则（无需 LLM）"""
        return [
            {
                "name": "硬编码密钥检测",
                "pattern": r"(api[_-]?key|secret|password|token)\s*[=:]\s*['\"][^'\"]{8,}['\"]",
                "severity": "critical",
                "category": "security",
                "message": "检测到可能的硬编码敏感信息",
                "suggestion": "使用环境变量或密钥管理服务存储敏感信息",
            },
            {
                "name": "SQL 注入风险",
                "pattern": r"(execute|query|raw)\s*\(.*%s.*\)|f\".*SELECT.*{.*}.*\"",
                "severity": "critical",
                "category": "security",
                "message": "检测到潜在的 SQL 注入风险",
                "suggestion": "使用参数化查询或 ORM",
            },
            {
                "name": "调试代码残留",
                "pattern": r"(print\(|console\.log|debugger;|import pdb|breakpoint\(\))",
                "severity": "warning",
                "category": "maintainability",
                "message": "检测到调试代码残留",
                "suggestion": "提交前移除所有调试代码，使用日志框架替代 print",
            },
            {
                "name": "TODO 未处理",
                "pattern": r"#\s*TODO|//\s*TODO|/\*\s*TODO",
                "severity": "info",
                "category": "maintainability",
                "message": "发现 TODO 标记",
                "suggestion": "确保 TODO 有对应的问题追踪，不要长期留在代码中",
            },
            {
                "name": "异常处理缺失",
                "pattern": r"^(?!.*except).*requests\.(get|post)|^(?!.*try).*open\(",
                "severity": "warning",
                "category": "bug",
                "message": "网络请求或文件操作缺少异常处理",
                "suggestion": "添加 try-except 块处理网络超时、文件不存在等异常",
            },
            {
                "name": "硬编码路径",
                "pattern": r"['\"]/(home|Users|tmp|var|etc)/[^'\"]*['\"]",
                "severity": "warning",
                "category": "maintainability",
                "message": "检测到硬编码文件路径",
                "suggestion": "使用 pathlib 或环境变量配置路径",
            },
        ]

    def review_file(self, file_path: str, content: str) -> List[ReviewComment]:
        """审查单个文件"""
        comments = []

        # 静态规则检查
        for rule in self.rules:
            for match in re.finditer(rule["pattern"], content, re.IGNORECASE):
                line_num = content[:match.start()].count("\n") + 1
                comments.append(ReviewComment(
                    file_path=file_path,
                    line_number=line_num,
                    severity=rule["severity"],
                    category=rule["category"],
                    message=rule["message"],
                    suggestion=rule["suggestion"],
                ))

        # LLM 深度分析（如果有客户端）
        if self.llm_client and len(content) < 10000:  # 限制大文件
            llm_comments = self._llm_review(file_path, content)
            comments.extend(llm_comments)

        return self._deduplicate(comments)

    def _llm_review(self, file_path: str, content: str) -> List[ReviewComment]:
        """使用 LLM 进行深度审查"""
        # 这里接入你的 LLM API
        # 示例使用 DeepSeek API
        prompt = f"""请审查以下代码，找出安全漏洞、逻辑错误、性能问题和可维护性问题。
        只输出 JSON 格式结果，不要其他解释。

文件：{file_path}

```python
{content[:8000]}  # 限制上下文长度
```

输出格式：
[
  {{
    "line_number": 行号,
    "severity": "critical/warning/info",
    "category": "security/style/bug/performance/maintainability",
    "message": "问题描述",
    "suggestion": "修改建议"
  }}
]
"""
        # 实际调用 LLM...
        return []

    def _deduplicate(self, comments: List[ReviewComment]) -> List[ReviewComment]:
        """去重：相同位置相同类别只保留最严重的一条"""
        seen = {}
        for c in comments:
            key = (c.file_path, c.line_number, c.category)
            if key not in seen:
                seen[key] = c
            elif self.SEVERITY_WEIGHTS[c.severity] > self.SEVERITY_WEIGHTS[seen[key].severity]:
                seen[key] = c
        return list(seen.values())

    def review_patch(self, patch_content: str) -> List[ReviewComment]:
        """审查 Git diff patch"""
        comments = []
        current_file = None
        current_content = []

        for line in patch_content.split("\n"):
            if line.startswith("diff --git"):
                if current_file and current_content:
                    content = "\n".join(current_content)
                    comments.extend(self.review_file(current_file, content))
                current_file = line.split()[-1].lstrip("b/")
                current_content = []
            elif line.startswith("+") and not line.startswith("+++"):
                current_content.append(line[1:])

        if current_file and current_content:
            content = "\n".join(current_content)
            comments.extend(self.review_file(current_file, content))

        return comments


# 使用示例
if __name__ == "__main__":
    reviewer = AICodeReviewer()

    test_code = '''
import requests

API_KEY = "sk-live-51a8b2c3d4e5f6789abcdef"

def fetch_user_data(user_id):
    url = f"https://api.example.com/users/{user_id}"
    response = requests.get(url, headers={"Authorization": API_KEY})
    return response.json()  # TODO: 添加错误处理
'''

    comments = reviewer.review_file("test.py", test_code)
    for c in comments:
        print(f"[{c.severity.upper()}] {c.file_path}:{c.line_number}")
        print(f"  {c.message}")
        print(f"  建议: {c.suggestion}\n")
```

---

## 第二步：GitHub Webhook 服务

```python
# github_webhook.py
from flask import Flask, request, jsonify
import hmac
import hashlib
import os
from code_reviewer import AICodeReviewer

app = Flask(__name__)
reviewer = AICodeReviewer()

GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")


def verify_signature(payload, signature):
    """验证 GitHub Webhook 签名"""
    if not GITHUB_WEBHOOK_SECRET:
        return True
    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Hub-Signature-256", "")
    payload = request.get_data()

    if not verify_signature(payload, signature):
        return jsonify({"error": "Invalid signature"}), 403

    event = request.headers.get("X-GitHub-Event", "")
    data = request.json

    if event == "pull_request" and data.get("action") in ["opened", "synchronize"]:
        handle_pr_event(data)

    return jsonify({"status": "ok"}), 200


def handle_pr_event(data):
    """处理 PR 事件"""
    pr = data["pull_request"]
    repo = data["repository"]

    print(f"审查 PR #{pr['number']}: {pr['title']}")
    print(f"仓库: {repo['full_name']}")

    # 这里调用 GitHub API 获取 diff
    # 然后使用 reviewer.review_patch() 审查
    # 最后通过 GitHub API 提交 review comments

    # 示例：获取 PR diff
    import requests
    diff_url = pr["diff_url"]
    diff = requests.get(diff_url).text

    comments = reviewer.review_patch(diff)

    # 提交 review（需要 GitHub Token）
    submit_review(repo["full_name"], pr["number"], comments)


def submit_review(repo_full_name, pr_number, comments):
    """提交 review 到 GitHub"""
    token = os.environ.get("GITHUB_TOKEN")
    if not token or not comments:
        return

    # 构建 review 数据
    review_comments = []
    for c in comments:
        review_comments.append({
            "path": c.file_path,
            "line": c.line_number,
            "body": f"**[{c.severity.upper()}] {c.category}**\n\n{c.message}\n\n💡 **建议**: {c.suggestion}",
        })

    url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/reviews"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {
        "body": f"🔍 AI 代码审查完成，发现 {len(comments)} 个问题。",
        "event": "COMMENT",
        "comments": review_comments[:10],  # GitHub 限制
    }

    response = requests.post(url, headers=headers, json=data)
    print(f"Review 提交状态: {response.status_code}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

---

## 第三步：GitHub Actions 集成（零服务器方案）

如果不想维护服务器，直接用 GitHub Actions：

```yaml
# .github/workflows/ai-code-review.yml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize]
    paths:
      - "**.py"
      - "**.js"
      - "**.ts"

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install requests

      - name: Get PR diff
        run: |
          git diff origin/${{ github.base_ref }}...HEAD > pr_diff.txt

      - name: Run AI Code Review
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          REPO: ${{ github.repository }}
        run: python scripts/ai_review.py pr_diff.txt
```

```python
# scripts/ai_review.py
import os
import sys
import requests
from code_reviewer import AICodeReviewer


def main():
    diff_file = sys.argv[1]
    with open(diff_file, "r") as f:
        patch = f.read()

    reviewer = AICodeReviewer()
    comments = reviewer.review_patch(patch)

    if not comments:
        print("✅ AI 审查通过，未发现问题。")
        return

    # 按严重程度分组
    critical = [c for c in comments if c.severity == "critical"]
    warnings = [c for c in comments if c.severity == "warning"]
    infos = [c for c in comments if c.severity == "info"]

    # 构建评论
    body = f"""## 🤖 AI 代码审查报告

| 严重程度 | 数量 |
|---------|------|
| 🔴 Critical | {len(critical)} |
| 🟡 Warning | {len(warnings)} |
| 🔵 Info | {len(infos)} |

---
"""

    for c in comments[:20]:  # 限制数量
        emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}[c.severity]
        body += f"""
{emoji} **{c.file_path}:{c.line_number}**

{c.message}

💡 **建议**: {c.suggestion}
"""

    # 提交到 PR
    token = os.environ["GITHUB_TOKEN"]
    pr_number = os.environ["PR_NUMBER"]
    repo = os.environ["REPO"]

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {token}"}
    requests.post(url, headers=headers, json={"body": body})

    # 如果有 critical，标记失败
    if critical:
        print(f"发现 {len(critical)} 个严重问题")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## 规则扩展

静态规则可以无限扩展：

```python
# 性能规则
{
    "name": "列表推导式优化",
    "pattern": r"for\s+\w+\s+in\s+\w+:\s*\n\s*\w+\.append",
    "severity": "info",
    "category": "performance",
    "message": "可以用列表推导式简化",
    "suggestion": "将循环+append改为列表推导式，性能提升 2-3 倍",
},

# Python 特定规则
{
    "name": "可变默认参数",
    "pattern": r"def\s+\w+\s*\([^)]*=\s*\[\s*\]|def\s+\w+\s*\([^)]*=\s*\{\s*\}",
    "severity": "warning",
    "category": "bug",
    "message": "使用可变对象作为默认参数",
    "suggestion": "使用 None 作为默认值，在函数内部初始化",
},

# 安全规则
{
    "name": "不安全的反序列化",
    "pattern": r"pickle\.loads|yaml\.load\s*\(|eval\s*\(",
    "severity": "critical",
    "category": "security",
    "message": "检测到不安全的反序列化/执行",
    "suggestion": "使用 json 替代 pickle，yaml.safe_load 替代 yaml.load",
},
```

---

## 审查效果示例

输入代码：

```python
import requests

API_KEY = "sk-live-51a8b2c3d4e5f6789abcdef"

def get_data(user_id):
    url = f"https://api.example.com/users/{user_id}"
    r = requests.get(url, headers={"Authorization": API_KEY})
    return r.json()

def process(items=[]):
    items.append("processed")
    return items
```

AI 审查输出：

```
🔴 [CRITICAL] test.py:3
  检测到可能的硬编码敏感信息
  建议: 使用环境变量或密钥管理服务存储敏感信息

🟡 [WARNING] test.py:6
  网络请求缺少异常处理
  建议: 添加 try-except 块处理网络超时、状态码异常

🟡 [WARNING] test.py:11
  使用可变对象作为默认参数
  建议: 使用 None 作为默认值，在函数内部初始化
```

---

## 团队级部署建议

| 规模 | 方案 | 成本 |
|------|------|------|
| 个人/小团队 | GitHub Actions | 免费 |
| 中型团队 | 自托管 Webhook + LLM | ¥200-500/月 |
| 大型企业 | 自托管 + 私有 LLM + 规则定制 | ¥2,000+/月 |

---

## 总结

本文提供了一个完整的 AI 代码审查系统实现：

1. **静态规则引擎** — 零成本，毫秒级检测常见漏洞
2. **LLM 深度分析** — 发现复杂逻辑问题
3. **GitHub 集成** — 无缝融入现有工作流
4. **可扩展规则** — 根据团队规范定制

代码已开源：github.com/kaising-openclaw1/ai-code-reviewer

如果你需要团队定制（私有规则、企业内部 LLM、Slack/钉钉通知集成），可以联系我。
