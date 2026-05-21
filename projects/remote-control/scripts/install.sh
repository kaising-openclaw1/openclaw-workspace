# RemoteEye 一键安装/部署脚本

set -e

echo "👁️ RemoteEye v2.0 安装脚本"
echo "=========================="

# 检查 Python 版本
python3 --version 2>/dev/null || {
    echo "❌ 需要 Python 3.10+"
    exit 1
}

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
IS_OK=$(python3 -c "import sys; print(sys.version_info >= (3, 10))")
if [ "$IS_OK" != "True" ]; then
    echo "❌ 需要 Python 3.10+，当前版本: $PYTHON_VERSION"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 安装被控端依赖
echo ""
echo "📦 安装被控端依赖..."
cd "$PROJECT_DIR/agent"
pip install -r requirements.txt --quiet --upgrade

# 安装服务器依赖
echo "📦 安装服务器依赖..."
cd "$PROJECT_DIR/server"
pip install -r requirements.txt --quiet --upgrade

# 创建配置目录
echo "📁 创建配置目录..."
mkdir -p ~/.remoteeye
mkdir -p ~/.remoteeye/recordings

echo ""
echo "✅ 安装完成！"
echo ""
echo "═══════════════════════════════════════"
echo "  启动方式："
echo ""
echo "  1. 启动服务器:"
echo "     cd server && python main.py"
echo ""
echo "  2. 启动被控端（基础）:"
echo "     cd agent && python agent.py --server ws://localhost:8000/ws/agent"
echo ""
echo "  3. 启动被控端（无人值守）:"
echo "     cd agent && python agent.py --server ws://localhost:8000/ws/agent --pin YOUR_PIN"
echo ""
echo "  4. 浏览器访问: http://localhost:8000"
echo "═══════════════════════════════════════"
echo ""
echo "📖 更多选项: python agent.py --help"
echo "🔒 可选加密: pip install cryptography"
echo "🎬 可选 H.264: pip install opencv-python"
echo "🔊 可选音频: pip install pyaudio"
echo "📊 可选监控: pip install psutil"
