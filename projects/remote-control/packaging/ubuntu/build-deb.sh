#!/bin/bash
# ============================================================
# RemoteEye v3.0 - Ubuntu/Debian .deb 安装包构建脚本
# 用法: cd packaging/ubuntu && bash build-deb.sh
# 输出: dist/remoteeye_3.0.0_amd64.deb
# ============================================================
set -e

APP="remoteeye"
VER="3.0.0"
ARCH="amd64"
B="/tmp/remoteeye-deb"
PROJ="$(cd "$(dirname "$0")/../.." && pwd)"

echo "╔════════════════════════════════════════╗"
echo "║  RemoteEye v3.0 - Ubuntu .deb 打包     ║"
echo "╚════════════════════════════════════════╝"

command -v python3 >/dev/null || { echo "❌ 需要 python3"; exit 1; }
command -v dpkg-deb >/dev/null || { echo "❌ 需要 dpkg-deb"; exit 1; }

# 安装依赖
echo "📦 安装依赖..."
pip3 install --user --quiet fastapi uvicorn websockets Pillow pynput psutil aiofiles cryptography 2>/dev/null || \
python3 -m pip install --user --quiet fastapi uvicorn websockets Pillow pynput psutil aiofiles cryptography

# 目录结构
echo "📁 创建结构..."
rm -rf "$B"
mkdir -p "$B"/{DEBIAN,usr/{bin,share/remoteeye/{agent,server,web/static/{css,js},web/templates},lib/systemd/system},etc/remoteeye}

# 复制文件
echo "📄 复制文件..."
cp "$PROJ"/agent/*.py "$B/usr/share/remoteeye/agent/"
cp "$PROJ"/server/*.py "$B/usr/share/remoteeye/server/"
cp "$PROJ"/web/static/css/*.css "$B/usr/share/remoteeye/web/static/css/" 2>/dev/null || true
cp "$PROJ"/web/static/js/*.js "$B/usr/share/remoteeye/web/static/js/" 2>/dev/null || true
cp "$PROJ"/web/templates/*.html "$B/usr/share/remoteeye/web/templates/" 2>/dev/null || true

# 启动脚本
cat > "$B/usr/bin/remoteeye-agent" << 'SCRIPT'
#!/bin/bash
PYLIB="$HOME/.local/lib/python3.*/site-packages"
export PYTHONPATH="$PYLIB:$PYTHONPATH"
cd /usr/share/remoteeye/agent && exec python3 agent.py "$@"
SCRIPT
chmod +x "$B/usr/bin/remoteeye-agent"

cat > "$B/usr/bin/remoteeye-server" << 'SCRIPT'
#!/bin/bash
PYLIB="$HOME/.local/lib/python3.*/site-packages"
export PYTHONPATH="$PYLIB:$PYTHONPATH"
cd /usr/share/remoteeye/server && exec python3 main.py "$@"
SCRIPT
chmod +x "$B/usr/bin/remoteeye-server"

# systemd 服务
cat > "$B/usr/lib/systemd/system/remoteeye-agent.service" << 'EOF'
[Unit]
Description=RemoteEye Agent v3.0
After=network.target
[Service]
Type=simple
ExecStart=/usr/bin/remoteeye-agent --server ws://localhost:8000/ws/agent
Restart=always
RestartSec=10
[Install]
WantedBy=multi-user.target
EOF

cat > "$B/usr/lib/systemd/system/remoteeye-server.service" << 'EOF'
[Unit]
Description=RemoteEye Server v3.0
After=network.target
[Service]
Type=simple
ExecStart=/usr/bin/remoteeye-server
Restart=always
RestartSec=10
[Install]
WantedBy=multi-user.target
EOF

# DEBIAN/control
cat > "$B/DEBIAN/control" << EOF
Package: $APP
Version: $VER
Section: net
Priority: optional
Architecture: $ARCH
Depends: python3 (>= 3.8), libx11-6, libxtst6, libxrandr2
Maintainer: RemoteEye Team
Description: RemoteEye v3.0 - 专业级开源远程控制
 对标向日葵/TeamViewer/RustDesk
 功能: 远程桌面、文件传输、远程终端、会话录制、E2E加密、差分截屏、自适应画质
EOF

cat > "$B/DEBIAN/postinst" << 'EOF'
#!/bin/bash
echo "✅ RemoteEye v3.0 安装完成!"
echo "启动被控端: remoteeye-agent"
echo "启动服务器: remoteeye-server"
echo "开机自启:   sudo systemctl enable remoteeye-agent remoteeye-server"
echo "Web控制台:  http://localhost:8000"
EOF
chmod +x "$B/DEBIAN/postinst"

# 打包
mkdir -p "$PROJ/dist"
echo "🏗️ 打包..."
dpkg-deb --build "$B" "$PROJ/dist/${APP}_${VER}_${ARCH}.deb" 2>&1 | tail -1

SIZE=$(du -sh "$PROJ/dist/${APP}_${VER}_${ARCH}.deb" 2>/dev/null | cut -f1)
echo ""
echo "╔════════════════════════════════════════╗"
echo "║  ✅ 构建完成!                          ║"
echo "║  📦 dist/${APP}_${VER}_${ARCH}.deb ($SIZE)"
echo "╚════════════════════════════════════════╝"
rm -rf "$B"
