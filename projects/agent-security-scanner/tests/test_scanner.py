"""Agent Security Scanner 测试套件"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import (
    SecurityScanner,
    ConfigLoader,
    PromptInjectionScanner,
    DataLeakScanner,
    PermissionScanner,
    AuditTrailScanner,
    RateLimitScanner,
    Severity,
    Report,
    generate_cli_report,
)

# 测试用配置
VALID_CONFIG = """
agent:
  name: "test-agent"
  endpoint: "http://localhost:8000/api/chat"

scans:
  - name: prompt_injection
    enabled: true
    test_cases:
      - role_play: true

  - name: data_leak
    enabled: true
    sensitive_patterns:
      - email
      - phone

  - name: permission_check
    enabled: true
    allowed_tools:
      - search
    denied_tools:
      - execute_code

  - name: audit_trail
    enabled: true

  - name: rate_limit
    enabled: true

security:
  min_score: 80
"""


def create_temp_config(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


class TestConfigLoader:
    def test_valid_config(self):
        path = create_temp_config(VALID_CONFIG)
        config = ConfigLoader(path)
        assert config.agent_name == "test-agent"
        assert config.agent_endpoint == "http://localhost:8000/api/chat"
        os.unlink(path)

    def test_missing_agent(self):
        path = create_temp_config("scans:\n  - name: test\n")
        with pytest.raises(ValueError, match="agent"):
            ConfigLoader(path)
        os.unlink(path)

    def test_missing_scans(self):
        path = create_temp_config("agent:\n  name: test\n")
        with pytest.raises(ValueError, match="scans"):
            ConfigLoader(path)
        os.unlink(path)


class TestSeverity:
    def test_score_weight(self):
        assert Severity.CRITICAL.score_weight == 15
        assert Severity.HIGH.score_weight == 10
        assert Severity.MEDIUM.score_weight == 5
        assert Severity.LOW.score_weight == 2

    def test_icon(self):
        assert Severity.CRITICAL.icon == "🔴"
        assert Severity.LOW.icon == "🟢"


class TestSecurityScanner:
    def test_full_scan(self):
        path = create_temp_config(VALID_CONFIG)
        scanner = SecurityScanner(path)
        report = scanner.run_all()

        assert report.agent_name == "test-agent"
        assert len(report.results) == 5
        assert report.overall_score >= 0
        assert report.overall_score <= 100
        assert "total_scans" in report.summary
        os.unlink(path)

    def test_report_summary(self):
        path = create_temp_config(VALID_CONFIG)
        scanner = SecurityScanner(path)
        report = scanner.run_all()

        summary = report.summary
        assert summary["total_scans"] == 5
        assert summary["critical"] == report.critical_count
        assert summary["high"] == report.high_count
        os.unlink(path)


class TestGenerateCliReport:
    def test_report_format(self):
        path = create_temp_config(VALID_CONFIG)
        scanner = SecurityScanner(path)
        report = scanner.run_all()

        output = generate_cli_report(report)
        assert "Agent Security Scan Report" in output
        assert "Overall Score" in output
        assert "Critical" in output
        os.unlink(path)

    def test_pass_fail_threshold(self):
        path = create_temp_config(VALID_CONFIG)
        scanner = SecurityScanner(path)
        report = scanner.run_all()

        output = generate_cli_report(report)
        if report.summary.get("passed_threshold"):
            assert "通过阈值" in output
        else:
            assert "未达到" in output
        os.unlink(path)


class TestReport:
    def test_vuln_counts(self):
        from scanner import ScanResult, Vulnerability

        report = Report(agent_name="test", timestamp="2026-05-25")
        report.results = [
            ScanResult(
                module="test",
                passed=False,
                vulnerabilities=[
                    Vulnerability("v1", "test", Severity.CRITICAL, 9.0, "desc"),
                    Vulnerability("v2", "test", Severity.HIGH, 7.0, "desc"),
                    Vulnerability("v3", "test", Severity.LOW, 3.0, "desc"),
                ],
            ),
        ]

        assert report.critical_count == 1
        assert report.high_count == 1
        assert report.low_count == 1
        assert report.total_vulns == 3
