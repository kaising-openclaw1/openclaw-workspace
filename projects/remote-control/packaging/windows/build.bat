@echo off
REM ============================================================
REM RemoteEye v3.0 - Windows 11 安装包构建脚本
REM 需要: Python 3.10+、Inno Setup 6
REM ============================================================

echo ╔════════════════════════════════════════╗
echo ║  RemoteEye v3.0 - Windows .exe 打包    ║
echo ╚════════════════════════════════════════╝
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到 Python
    echo 请安装 Python 3.10+ (https://www.python.org/downloads/)
    pause
    exit /b 1
)

echo 📦 安装依赖...
pip install pyinstaller fastapi uvicorn websockets Pillow pynput psutil aiofiles cryptography --quiet

echo 📁 准备文件...
set PROJ=%~dp0..\..
set WORK=%~dp0work
rd /s /q "%WORK%" 2>nul
mkdir "%WORK%\agent" "%WORK%\server" "%WORK%\web\static\css" "%WORK%\web\static\js" "%WORK%\web\templates"
xcopy "%PROJ%\agent\*.py" "%WORK%\agent\" /y >nul
xcopy "%PROJ%\server\*.py" "%WORK%\server\" /y >nul
xcopy "%PROJ%\web\static\css\*.css" "%WORK%\web\static\css\" /y >nul 2>nul
xcopy "%PROJ%\web\static\js\*.js" "%WORK%\web\static\js\" /y >nul 2>nul
xcopy "%PROJ%\web\templates\*.html" "%WORK%\web\templates\" /y >nul 2>nul

echo 🏗️ 打包 Agent...
cd /d "%WORK%\agent"
pyinstaller --onefile --name RemoteEyeAgent --noconsole agent.py

echo 🏗️ 打包 Server...
cd /d "%WORK%\server"
pyinstaller --onefile --name RemoteEyeServer --noconsole main.py

echo.
echo ╔════════════════════════════════════════╗
echo ║  ✅ PyInstaller 打包完成              ║
echo ║  📦 Agent:  work\agent\dist\RemoteEyeAgent.exe
echo ║  📦 Server: work\server\dist\RemoteEyeServer.exe
echo ║
echo ║  💡 用 Inno Setup 生成 .exe 安装包:
echo ║     iscc.exe "%~dp0RemoteEye.iss"
echo ╚════════════════════════════════════════╝
pause
