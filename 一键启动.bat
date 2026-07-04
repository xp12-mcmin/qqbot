@echo off
chcp 65001 >nul
title QQ机器人 启动器

:: ========== 切换到脚本目录 ==========
cd /d "%~dp0"

color 0A

echo ========================================
echo   QQ机器人 + 看门狗 启动器
echo ========================================
echo.

:: ========== 检查 Python ==========
echo [1/4] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python！
    echo 请安装 Python 3.10 或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo [Python] 版本: %PYTHON_VER%

:: ========== 检查依赖 ==========
echo.
echo [2/4] 检查依赖...

set NEED_INSTALL=0

python -c "import psutil" >nul 2>&1
if errorlevel 1 (
    echo [缺失] psutil
    set NEED_INSTALL=1
)
python -c "import websockets" >nul 2>&1
if errorlevel 1 (
    echo [缺失] websockets
    set NEED_INSTALL=1
)
python -c "import aiohttp" >nul 2>&1
if errorlevel 1 (
    echo [缺失] aiohttp
    set NEED_INSTALL=1
)
python -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo [缺失] pillow
    set NEED_INSTALL=1
)
python -c "import schedule" >nul 2>&1
if errorlevel 1 (
    echo [缺失] schedule
    set NEED_INSTALL=1
)

if %NEED_INSTALL%==1 (
    echo.
    echo [依赖] 正在安装缺失的库...
    pip install psutil websockets aiohttp pillow schedule -q
    echo [依赖] 安装完成
) else (
    echo [依赖] 所有库已安装
)

:: ========== 检查程序文件 ==========
echo.
echo [3/4] 检查程序文件...
if not exist "qai主程序.py" (
    echo [错误] 找不到主程序文件: qai主程序.py
    echo 请确保 qai主程序.py 存在
    pause
    exit /b 1
)
if not exist "llbot_watchdog.py" (
    echo [错误] 找不到看门狗文件: llbot_watchdog.py
    echo 缺少看门狗，拒绝启动！
    echo 请确保 llbot_watchdog.py 存在
    pause
    exit /b 1
)
echo [文件] 主程序: qai主程序.py
echo [文件] 看门狗: llbot_watchdog.py

:: ========== 启动程序 ==========
echo.
echo [4/4] 启动程序...

:: 启动看门狗

start "" /min pythonw llbot_watchdog.py
timeout /t 1 /nobreak >nul

:: 启动主程序
echo [主程序] 正在启动...
start "" python qai主程序.py
timeout /t 1 /nobreak >nul
echo [主程序] 已启动

echo.
echo ========================================
echo   启动完成！
echo   主程序: 显示控制台窗口
echo   看门狗: 后台运行
echo ========================================
echo.
echo [提示] 关闭此窗口不影响程序运行
echo.
pause