# RemoteEye v3.0 跨平台安装包

## 当前状态
- 版本: v3.0
- 代码量: 4,562 行
- 功能: 心跳保活 | 优雅关闭 | 实时聊天 | 录制清理 | 审计日志 | 指数退避
- 安装包: 0 个 (构建脚本已就绪)

## 📦 一键构建

### 🐧 Ubuntu/Debian (.deb)
```bash
cd packaging/ubuntu
chmod +x build-deb.sh
./build-deb.sh
```
输出: `dist/remoteeye_3.0.0_amd64.deb`
安装: `sudo dpkg -i dist/remoteeye_3.0.0_amd64.deb`
使用: `remoteeye-agent` / `remoteeye-server`

### 🪟 Windows 11 (.exe)
需要 Python 3.10+ 和 Inno Setup 6
```cmd
cd packaging\windows
build.bat
```
输出: `work\agent\dist\RemoteEyeAgent.exe` + `work\server\dist\RemoteEyeServer.exe`

### 🍎 macOS (.dmg)
需要 Python 3.10+ 和 PyInstaller
```bash
cd packaging/macos
chmod +x build-dmg.sh
./build-dmg.sh
```
输出: `dist/RemoteEye-v3.0.dmg`

---

## 技术栈
| 平台 | 打包方式 | 依赖 |
|------|---------|------|
| Ubuntu | dpkg-deb | python3, pip3 |
| Windows | PyInstaller + Inno Setup | Python 3.10+, Inno Setup 6 |
| macOS | PyInstaller + hdiutil | Python 3.10+, PyInstaller |
