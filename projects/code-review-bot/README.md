# 🤖 Code Review Bot — AI 驱动的自动化代码审查

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

基于 LLM 的智能代码审查工具，自动分析 Pull Request / 代码变更，生成结构化的审查报告，覆盖代码质量、安全漏洞、性能优化、最佳实践等维度。

## 特性

- 🔍 **多维度审查**：代码质量、安全漏洞、性能问题、命名规范、架构设计
- 📊 **严重性分级**：Critical / Warning / Info 三级分类，优先处理关键问题
- 🔧 **自动修复建议**：不仅指出问题，还给出具体修复代码
- 📝 **PR 评论集成**：支持 GitHub / GitLab PR 自动评论
- 🎯 **可定制规则**：通过配置文件自定义审查规则和忽略模式
- ⚡ **增量分析**：只审查变更文件，节省 token 消耗

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### 配置

```bash
cp .env.example .env
# 编辑 .env 填入 API Key
```

### 使用

```python
from bot.code_reviewer import CodeReviewer

reviewer = CodeReviewer(
    model="qwen-plus",  # 或 gpt-4, claude-3-sonnet
    api_key="your-api-key"
)

# 审查代码变更
result = reviewer.review_diff(
    diff_text=open("changes.diff").read(),
    language="python",
    rules=["security", "performance", "best-practices"]
)

# 输出结构化报告
for issue in result.issues:
    print(f"[{issue.severity}] {issue.file}:{issue.line}")
    print(f"  {issue.description}")
    print(f"  💡 {issue.suggestion}")
```

### CLI 模式

```bash
# 审查本地 diff
python -m bot.cli review --diff changes.diff --lang python

# 审查 GitHub PR
python -m bot.cli review-pr --repo owner/repo --pr 42

# 生成 HTML 报告
python -m bot.cli review --diff changes.diff --format html --output report.html
```

## 架构

```
code-review-bot/
├── bot/
│   ├── __init__.py
│   ├── code_reviewer.py      # 核心审查引擎
│   ├── llm_client.py         # LLM 调用层（多模型适配）
│   ├── rules.py              # 审查规则库
│   ├── report_generator.py   # 报告生成器
│   └── cli.py                # 命令行入口
├── examples/
│   ├── basic_review.py       # 基础使用示例
│   └── github_integration.py # GitHub 集成示例
├── tests/
│   ├── test_reviewer.py
│   └── test_rules.py
├── .env.example
├── requirements.txt
└── README.md
```

## 审查规则

| 规则类别 | 检测内容 |
|---------|---------|
| security | SQL 注入、XSS、硬编码密钥、路径穿越、不安全的反序列化 |
| performance | N+1 查询、内存泄漏风险、不必要的循环、低效算法 |
| best-practices | 异常处理缺失、日志不规范、魔法数字、重复代码 |
| naming | 命名约定、函数长度、类职责单一 |
| architecture | 循环依赖、过度耦合、违反 SOLID 原则 |

## 支持的 LLM

- Qwen Plus / Qwen Max（推荐，中文能力强，成本低）
- GPT-4 / GPT-4o
- Claude 3.5 Sonnet
- DeepSeek V3

## 商业授权

- **开源版**：MIT 协议，个人使用
- **企业版**：自定义规则、团队协作、CI/CD 集成、私有化部署 — 联系 contact@example.com

## License

MIT © Kai Studio
