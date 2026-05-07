#!/bin/bash
# RemoteEye 一键安装脚本

echo "👁️ RemoteEye 安装脚本"
echo "===================="

# 检查 Python 版本
python3 --version 2>/dev/null || {
    echo "❌ 需要 Python 3.10+"
    exit 1
}

# 安装被控端依赖
echo "📦 安装被控端依赖..."
cd "$(dirname "$0")/../agent"
pip install -r requirements.txt --quiet

# 安装服务器依赖
echo "📦 安装服务器依赖..."
cd "$(dirname "$0")/../server"
pip install -r requirements.txt --quiet

echo ""
echo "✅ 安装完成！"
echo ""
echo "启动方式："
echo "  1. 启动服务器: cd server && python main.py"
echo "  2. 启动被控端: cd agent && python agent.py --server ws://localhost:8000/ws/agent"
echo "  3. 浏览器访问: http://localhost:8000"
