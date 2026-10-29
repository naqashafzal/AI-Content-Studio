@echo off
setlocal EnableDelayedExpansion
TITLE AI Content Studio Next-Gen - 1-Click Launcher
color 0b

:: Ensure execution from script directory
cd /d "%~dp0"

echo ===============================================================================
echo                AI CONTENT STUDIO - NEXT GENERATION v2.0
echo       Autonomous AI Creative Production, Video Editing ^& Publishing
echo ===============================================================================
echo.

:: 1. Check Python
echo [1/6] Checking Python runtime...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in your PATH!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo       Found Python %PY_VER% (OK)

:: 2. Check Node.js & npm
echo.
echo [2/6] Checking Node.js runtime...
node --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js is not installed or not in your PATH!
    echo Please install Node.js 18+ from https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f "tokens=1 delims= " %%v in ('node --version 2^>^&1') do set NODE_VER=%%v
echo       Found Node.js %NODE_VER% (OK)

:: 3. Check FFmpeg
echo.
echo [3/6] Checking FFmpeg multimedia engine...
ffmpeg -version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [WARNING] FFmpeg is not found in your system PATH!
    echo Video rendering, waveform analysis, and audio loudnorm require FFmpeg.
    echo Download FFmpeg from https://ffmpeg.org/download.html or install via winget:
    echo   winget install Gyan.FFmpeg
    echo.
    echo Continuing, but some video generation steps may fail without FFmpeg.
    timeout /t 3 >nul
) ELSE (
    echo       Found FFmpeg [OK]
)

:: 4. Ensure Workspace Directories
echo.
echo [4/6] Initializing storage directories...
if not exist "workspace" mkdir workspace
if not exist "outputs" mkdir outputs
if not exist "assets" mkdir assets
echo       Workspace directories ready.

:: 5. Setup Python Virtual Environment & Dependencies
echo.
echo [5/6] Checking Python virtual environment and packages...
IF NOT EXIST ".venv\Scripts\python.exe" (
    echo       Creating Python Virtual Environment...
    python -m venv .venv
    IF %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
echo       Verifying core dependencies...
python -m pip install -q -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Some python packages failed to install. Retrying with verbose output...
    python -m pip install -r requirements.txt
)
echo       Python environment ready.

:: 6. Check Frontend Dependencies
echo.
echo [6/6] Checking Frontend web dependencies...
cd web
IF NOT EXIST "node_modules" (
    echo       Installing frontend packages...
    call npm install
) ELSE (
    echo       Frontend dependencies ready.
)
cd ..

:: Launch Servers
echo.
echo ===============================================================================
echo     All Systems Operational! Launching Next-Gen Studio...
echo ===============================================================================
echo.
echo   - Backend API:  http://localhost:8008
echo   - Frontend UI:  http://localhost:3000
echo   - Swagger Docs: http://localhost:8008/docs
echo.

:: Start Backend API Server in a dedicated window
echo [INFO] Starting Backend API Server (FastAPI / Uvicorn on :8008)...
start "AI Content Studio - API Backend [:8008]" cmd /k "title AI Content Studio - API Backend [:8008] && color 0a && cd /d "%~dp0" && call .venv\Scripts\activate.bat && python server\main.py"

:: Start Frontend Next.js Dev Server in a dedicated window
echo [INFO] Starting Frontend Studio (Next.js Turbopack on :3000)...
start "AI Content Studio - Web UI [:3000]" cmd /k "title AI Content Studio - Web UI [:3000] && color 09 && cd /d "%~dp0\web" && npm run dev"

:: Wait 3 seconds and launch browser
echo [INFO] Opening Web UI in default browser...
timeout /t 3 /nobreak >nul
start http://localhost:3000

echo.
echo ===============================================================================
echo   Servers are running in background windows!
echo   Close those windows or press Ctrl+C inside them to terminate.
echo ===============================================================================
echo.
echo Press any key to exit this launcher window...
pause >nul
