#!/bin/bash
# ============================================================
# RemoteEye v3.0 - macOS .dmg 安装包构建脚本
# 需要: Python 3.10+, pip3, PyInstaller
# 用法: cd packaging/macos && bash build-dmg.sh
# ============================================================
set -e

APP="RemoteEye"
VER="3.0.0"
PROJ="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="/tmp/remoteeye-macos"

echo "╔════════════════════════════════════════╗"
echo "║  RemoteEye v3.0 - macOS .dmg 打包      ║"
echo "╚════════════════════════════════════════╝"

# 检查
python3 --version >/dev/null 2>&1 || { echo "❌ 需要 Python 3.10+"; exit 1; }

echo "📦 安装依赖..."
pip3 install --quiet pyinstaller fastapi uvicorn websockets Pillow psutil aiofiles cryptography 2>/dev/null || \
python3 -m pip install --quiet pyinstaller fastapi uvicorn websockets Pillow psutil aiofiles cryptography

echo "📁 准备工作目录..."
rm -rf "$WORK"
mkdir -p "$WORK"/{Agent,Server,web/static/css,web/static/js,web/templates}
cp "$PROJ"/agent/*.py "$WORK/Agent/"
cp "$PROJ"/server/*.py "$WORK/Server/"
cp "$PROJ"/web/static/css/*.css "$WORK/web/static/css/" 2>/dev/null || true
cp "$PROJ"/web/static/js/*.js "$WORK/web/static/js/" 2>/dev/null || true
cp "$PROJ"/web/templates/*.html "$WORK/web/templates/" 2>/dev/null || true

echo "🏗️ 打包 Agent..."
cd "$WORK/Agent"
pyinstaller --onefile --name RemoteEyeAgent --noconsole \
  --add-data "web:web" \
  --hidden-import=PIL agent.py 2>&1 | grep -i "error" || echo "  Agent ✅"

echo "🏗️ 打包 Server..."
cd "$WORK/Server"
pyinstaller --onefile --name RemoteEyeServer --noconsole main.py 2>&1 | grep -i "error" || echo "  Server ✅"

echo "📦 创建 .app 结构..."
mkdir -p "$WORK/RemoteEye.app/Contents/{MacOS,Resources}"

cat > "$WORK/RemoteEye.app/Contents/MacOS/RemoteEye" << 'EOF'
#!/bin/bash
DIR="$(cd "$(dirname "$0")/.." && pwd)"
# 默认启动 Agent，传 --server 参数启动 Server
if [ "$1" = "--server" ]; then
  exec "$DIR/Resources/RemoteEyeServer"
else
  exec "$DIR/Resources/RemoteEyeAgent" "$@"
fi
EOF
chmod +x "$WORK/RemoteEye.app/Contents/MacOS/RemoteEye"

cp "$WORK/Agent/dist/RemoteEyeAgent" "$WORK/RemoteEye.app/Contents/Resources/" 2>/dev/null || true
cp "$WORK/Server/dist/RemoteEyeServer" "$WORK/RemoteEye.app/Contents/Resources/" 2>/dev/null || true

cat > "$WORK/RemoteEye.app/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>RemoteEye</string>
  <key>CFBundleDisplayName</key><string>RemoteEye</string>
  <key>CFBundleIdentifier</key><string>com.remoteeye.main</string>
  <key>CFBundleVersion</key><string>$VER</string>
  <key>CFBundleShortVersionString</key><string>$VER</string>
  <key>CFBundleExecutable</key><string>RemoteEye</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
EOF

# 创建 launchd 开机自启配置
mkdir -p "$WORK/RemoteEye.app/Contents/Resources/LaunchAgents"
cat > "$WORK/RemoteEye.app/Contents/Resources/LaunchAgents/com.remoteeye.agent.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.remoteeye.agent</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Applications/RemoteEye.app/Contents/MacOS/RemoteEye</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict>
</plist>
EOF

# 打包 dmg
mkdir -p "$PROJ/dist"
echo "🏗️ 创建 .dmg..."
hdiutil create \
  -volname "RemoteEye v$VER" \
  -srcfolder "$WORK/RemoteEye.app" \
  -ov -format UDZO \
  "$PROJ/dist/RemoteEye-v${VER}.dmg" 2>&1 | tail -1

SIZE=$(du -sh "$PROJ/dist/RemoteEye-v${VER}.dmg" 2>/dev/null | cut -f1)
echo ""
echo "╔════════════════════════════════════════╗"
echo "║  ✅ 构建完成!                          ║"
echo "║  📦 dist/RemoteEye-v${VER}.dmg"
echo "║  📊 $SIZE"
echo "║  💡 安装: 打开 DMG，拖入 Applications"
echo "╚════════════════════════════════════════╝"

rm -rf "$WORK"
