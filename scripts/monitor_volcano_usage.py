#!/usr/bin/env python3
"""
火山引擎 Ark API 用量监控脚本
运行方式: python3 monitor_volcano_usage.py
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime

API_KEY = "ark-a1cdd913-b3a5-4f1c-80ed-b1c7f2b4a658-64d06"
BASE_URL = "https://ark.cn-beijing.volces.com/api/coding/v3"
LOG_FILE = os.path.expanduser("~/.openclaw/workspace/logs/volcano_usage.log")
ALERT_THRESHOLD = 80  # 用量超过 80% 报警

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def check_api_health():
    """检查 API 是否可用"""
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{BASE_URL}/models",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        log(f"⚠️ API 检查失败: {e}")
        return False

def estimate_usage_from_logs():
    """
    估算用量（火山没有直接配额查询 API，通过日志估算）
    实际用量需要到控制台查看
    """
    hermes_log = os.path.expanduser("~/.hermes/logs/agent.log")
    if not os.path.exists(hermes_log):
        return None
    
    # 统计今日请求次数
    today = datetime.now().strftime("%Y-%m-%d")
    count = 0
    try:
        with open(hermes_log, "r") as f:
            for line in f:
                if today in line and "Streaming failed before delivery" in line:
                    count += 1
    except:
        pass
    return count

def main():
    log("=" * 50)
    log("🔥 火山 Ark 用量监控启动")
    
    # 检查 API 健康
    if check_api_health():
        log("✅ API 连接正常")
    else:
        log("❌ API 连接异常")
    
    # 估算用量
    req_count = estimate_usage_from_logs()
    if req_count is not None:
        log(f"📊 今日估计请求数: {req_count}")
    
    # 检查 hermes 配置
    config_path = os.path.expanduser("~/.hermes/config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            content = f.read()
        if "deepseek-v4-pro" in content:
            log("⚠️ WARNING: hermes 仍使用 deepseek-v4-pro（贵模型），建议切换")
        elif "doubao-lite" in content:
            log("✅ hermes 已切换到 doubao-lite（经济模型）")
    
    log("💡 提示: 用量详情请到 https://console.volcengine.com/ark/ 查看")
    log("=" * 50)

if __name__ == "__main__":
    main()
