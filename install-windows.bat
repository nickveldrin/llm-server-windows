@echo off
REM llm-server Windows Installer
REM This script installs all dependencies and sets up the Windows port

echo ========================================
echo   llm-server Windows Installer v2.0.0
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8 or later from:
    echo   https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [1/4] Python found!
python --version
echo.

REM Check if pip is available
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip is not available
    echo Please reinstall Python with pip enabled.
    pause
    exit /b 1
)

echo [2/4] Installing Python dependencies...
python -m pip install --upgrade pip -q

REM Install required packages
python -m pip install psutil requests wmi uv -q
if errorlevel 1 (
    echo WARNING: Some packages may not have installed correctly
    echo Continuing anyway...
)
echo.

echo [3/4] Creating Windows launcher scripts...

REM Create batch file for easy launching
(
echo @echo off
echo REM llm-server Windows launcher
echo cd /d "%%~dp0"
echo python "%%~dp0llm-server-windows.py" %%*
echo exit /b %%errorlevel%%
) > llm-server-windows.bat

REM Create auto-updater
(
echo @echo off
echo REM llm-server Auto-Updater
echo python "%%~dp0llm-server-windows.py" %%*
echo echo.
echo echo Checking for updates...
echo python -c "import requests; r = requests.get('https://api.github.com/repos/raketenkater/llm-server/releases/latest', timeout=10); print('Update available!' if 'tag_name' in r.text else 'Up to date')"
echo pause
) > llm-server-update.bat

echo    Created: llm-server-windows.bat
echo    Created: llm-server-update.bat
echo.

echo [4/4] Setting up model directory...
if not exist "%USERPROFILE%\ai_models" (
    mkdir "%USERPROFILE%\ai_models"
    echo    Created: %USERPROFILE%\ai_models
) else (
    echo    Model directory already exists
)
echo.

echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Quick Start:
echo   1. Place your GGUF model file in %USERPROFILE%\ai_models\
echo   2. Make sure you have installed ik_llama.cpp or llama.cpp
echo   3. Run: llm-server-windows.bat model.gguf
echo.
echo Options:
echo   --ai-tune          Auto-optimize server flags (requires GPU)
echo   --benchmark        Run benchmark and exit
echo   --verbose          Enable debug output
echo   --backend llama    Use llama.cpp instead of ik_llama.cpp
echo.
echo GPU Requirements:
echo   - NVIDIA GPU with CUDA support
echo   - nvidia-smi in PATH (usually comes with NVIDIA drivers)
echo   - At least 4GB VRAM recommended
echo.
echo Next Steps:
echo   1. Install NVIDIA drivers if not already installed
echo   2a. Option A: Download pre-built binaries (easiest)
echo       Place llama-server.exe and DLLs in a folder like D:\ai\loaders\llamacpp\
echo       Download from: https://github.com/ggml-org/llama.cpp/releases
echo   2b. Option B: Build from source
echo       git clone https://github.com/ggml-org/llama.cpp
echo       cd llama.cpp && mkdir build && cd build
echo       cmake .. -DCMAKE_BUILD_TYPE=Release
echo       cmake --build . --config Release
echo   3. Test with: llm-server-windows.bat model.gguf --ai-tune
echo.
pause
