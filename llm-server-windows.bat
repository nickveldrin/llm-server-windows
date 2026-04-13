@echo off
REM llm-server Windows launcher
REM This script launches the Python version of llm-server

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or later from https://www.python.org/
    exit /b 1
)

python -c "import psutil, requests" >nul 2>&1
if errorlevel 1 (
    echo Installing required Python packages...
    pip install psutil requests -q
)

python "%~dp0llm-server-windows.py" %*
exit /b %errorlevel%
