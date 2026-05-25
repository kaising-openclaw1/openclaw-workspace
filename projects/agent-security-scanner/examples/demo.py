#!/usr/bin/env python3
"""Agent Security Scanner 演示脚本

展示如何使用安全扫描器检测 AI Agent 配置中的漏洞。
"""

import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import SecurityScanner, generate_cli_report


def demo_basic_scan():
    """基础扫描演示"""
    print("=" * 60)
    print("  Agent Security Scanner — 演示")
    print("=" * 60)
    print()

    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")

    if not os.path.exists(config_path):
        print(f"⚠️ 配置文件不存在: {config_path}")
        print("请先创建配置文件，参考 examples/config.yaml")
        return

    scanner = SecurityScanner(config_path)
    report = scanner.run_all()

    print(generate_cli_report(report))

    print()
    print("💡 修复建议:")
    print("  1. 为系统提示添加不可覆盖的安全规则层")
    print("  2. 配置输出过滤中间件，脱敏 PII 和敏感数据")
    print("  3. 设置工具调用白名单和黑名单")
    print("  4. 启用完整的审计日志和决策追踪")
    print("  5. 添加速率限制防止资源耗尽")
    print()
    print("📖 完整文档: README.md")


if __name__ == "__main__":
    demo_basic_scan()
