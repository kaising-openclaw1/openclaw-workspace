# Agent Security Scanner 🔒

> **AI Agent 安全扫描工具** — 自动检测 Agent 部署中的常见安全漏洞

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-1.0.0-orange.svg)]()

## 痛点

根据 Gravitee 2026 Q1 报告，**仅 14.4% 的 AI Agent 获得了企业安全审批**。大多数 Agent 部署存在以下风险：

- 🚨 **Prompt 注入** — 恶意输入操控 Agent 行为
- 🚨 **数据泄露** — Agent 意外暴露敏感信息
- 🚨 **权限越界** — Agent 执行了超出预期的操作
- 🚨 **工具滥用** — 恶意用户通过 Agent 调用危险 API
- 🚨 **Token 劫持** — API 密钥被注入攻击获取
- 🚨 **无审计日志** — 无法追踪 Agent 的决策过程

**Agent Security Scanner** 提供一站式安全检测，让你的 AI Agent 从"能用"到"安全"。

## 功能

- ✅ **Prompt 注入检测** — 测试常见注入攻击向量（角色扮演、指令覆盖、分隔符逃逸）
- ✅ **数据泄露扫描** — 检测 Agent 是否会输出敏感信息（邮箱、电话、密钥、内部数据）
- ✅ **权限边界验证** — 确认 Agent 只在授权范围内操作
- ✅ **工具调用审计** — 监控 Agent 调用外部工具的行为
- ✅ **HTML 安全报告** — 一键生成可视化安全评估报告
- ✅ **CVSS 风格评分** — 量化每个漏洞的严重程度
- ✅ **修复建议** — 针对每个发现的问题给出具体修复方案

## 快速开始

```bash
pip install -r requirements.txt

# 扫描你的 Agent 配置
python -m scanner scan --config agent_config.yaml

# 运行注入测试
python -m scanner injection-test --target http://localhost:8000

# 生成安全报告
python -m scanner report --output security_report.html
```

## 扫描模块

| 模块 | 检测内容 | 严重级别 |
|------|----------|----------|
| `prompt_injection` | 角色扮演、指令覆盖、分隔符逃逸、多语言注入 | 🔴 高 |
| `data_leak` | PII 泄露、密钥泄露、内部信息泄露 | 🔴 高 |
| `permission_check` | 权限越界、未授权工具调用、资源过度使用 | 🟡 中 |
| `tool_abuse` | 危险 API 调用、命令注入、文件系统遍历 | 🔴 高 |
| `audit_trail` | 日志完整性、决策可追溯性、异常检测 | 🟡 中 |
| `rate_limit` | 速率限制、资源消耗、DoS 防护 | 🟢 低 |

## 输出示例

```
╔══════════════════════════════════════════════════════════╗
║         Agent Security Scan Report                       ║
║         2026-05-25 10:00:00                              ║
╠══════════════════════════════════════════════════════════╣
║  Overall Score: 62/100 (⚠️ 需要改进)                     ║
╠══════════════════════════════════════════════════════════╣
║  🔴 Critical: 2   🟡 Medium: 3   🟢 Low: 1              ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  [1] 🔴 Prompt Injection - Direct Override               ║
║      Severity: 9.2 (Critical)                            ║
║      Agent executed injected instructions                ║
║      Fix: Add input sanitization + system prompt lock    ║
║                                                          ║
║  [2] 🔴 Data Leak - PII Exposure                         ║
║      Severity: 8.5 (High)                                ║
║      Agent revealed internal email format                ║
║      Fix: Add output filtering + PII redaction           ║
║                                                          ║
║  [3] 🟡 Permission - Unauthorized Tool Call              ║
║      Severity: 6.0 (Medium)                              ║
║      Agent called external API without confirmation      ║
║      Fix: Add tool call approval workflow                ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

## 配置文件示例

```yaml
# agent_config.yaml
agent:
  name: "customer-service-agent"
  endpoint: "http://localhost:8000/api/chat"
  api_key: "${AGENT_API_KEY}"

scans:
  - name: prompt_injection
    enabled: true
    test_cases:
      - role_play: true
      - instruction_override: true
      - delimiter_escape: true
      - multi_language: true

  - name: data_leak
    enabled: true
    sensitive_patterns:
      - email
      - phone
      - api_key
      - internal_url

  - name: permission_check
    enabled: true
    allowed_tools:
      - search
      - summarize
    denied_tools:
      - execute_code
      - send_email

security:
  min_score: 80  # 最低安全评分
  auto_block: true  # 自动阻断高风险请求
```

## 集成

### CI/CD 集成

```yaml
# .github/workflows/security-scan.yml
name: Agent Security Scan
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: python -m scanner scan --config agent_config.yaml --fail-on critical
```

### API 集成

```python
from scanner import SecurityScanner

scanner = SecurityScanner("agent_config.yaml")
result = scanner.run_all()

if result.score < 80:
    print(f"⚠️ Security score {result.score}/100 - review needed")
    for vuln in result.critical:
        print(f"  🔴 {vulnerability.name}: {vulnerability.description}")
```

## 安装

```bash
git clone https://github.com/yourname/agent-security-scanner.git
cd agent-security-scanner
pip install -r requirements.txt
```

## License

MIT License — 自由使用，欢迎贡献
