#!/bin/bash
# ============================================================
# RemoteEye v3.0 - 跨平台打包构建主脚本
# 用法: ./build-all.sh [--platform windows|ubuntu|macos|all]
# ============================================================

set -e

PLATFORM="${1:---all}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "╔══════════════════════════════════════════════════════╗"
echo "║         RemoteEye v3.0 跨平台打包构建                ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

cd "$PROJECT_DIR"

build_windows() {
    echo ""
    echo "🪟 ========== Windows 11 =========="
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        cd "$SCRIPT_DIR/windows"
        chmod +x build.bat
        ./build.bat
    else
        echo "⚠️  非 Windows 环境，生成构建文件但无法执行"
        echo "📁 请将 packaging/windows/ 复制到 Windows 机器上运行 build.bat"
        echo "📋 需要: Python 3.10+、PyInstaller、Inno Setup 6"
        echo ""
        echo "📦 生成文件:"
        echo "   - packaging/windows/RemoteEye.iss (Inno Setup 安装脚本)"
        echo "   - packaging/windows/build.bat (构建脚本)"
        echo "   - packaging/windows/config.json (默认配置)"
    fi
}

build_ubuntu() {
    echo ""
    echo "🐧 ========== Ubuntu/Debian =========="
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        cd "$SCRIPT_DIR/ubuntu"
        chmod +x build-deb.sh
        ./build-deb.sh
    else
        echo "⚠️  非 Linux 环境，生成构建文件但无法执行"
        echo "📁 请将 packaging/ubuntu/ 复制到 Ubuntu 机器上运行 build-deb.sh"
        echo "📋 需要: dpkg-deb、python3、pip3"
    fi
}

build_macos() {
    echo ""
    echo "🍎 ========== macOS =========="
    if [[ "$OSTYPE" == "darwin"* ]]; then
        cd "$SCRIPT_DIR/macos"
        chmod +x build-dmg.sh
        ./build-dmg.sh
    else
        echo "⚠️  非 macOS 环境，生成构建文件但无法执行"
        echo "📁 请将 packaging/macos/ 复制到 Mac 机器上运行 build-dmg.sh"
        echo "📋 需要: Python 3.10+、PyInstaller、create-dmg (可选)"
    fi
}

case "$PLATFORM" in
    windows|--windows|-w)
        build_windows
        ;;
    ubuntu|--ubuntu|-u)
        build_ubuntu
        ;;
    macos|--macos|-m)
        build_macos
        ;;
    all|--all|-a|*)
        build_windows
        build_ubuntu
        build_macos
        ;;
esac

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ 打包脚本生成完成！                               ║"
echo "║  📁 packaging/ 目录下包含各平台构建脚本              ║"
echo "╚══════════════════════════════════════════════════════╝"
