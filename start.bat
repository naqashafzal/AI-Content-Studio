@echo off
TITLE AI Content Studio - 1-Click Start
color 0b

echo ===================================================
echo     AI Content Studio - Auto Installer ^& Runner
echo ===================================================
echo.

:: Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH! Please install Python 3.10+.
    pause
    exit /b
)

:: Check for Node.js
node --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js is not installed or not in PATH! Please install Node 18+.
    pause
    exit /b
)

:: Setup Python Virtual Environment
IF NOT EXIST ".venv" (
    echo [INFO] Creating Python Virtual Environment...
    python -m venv .venv
)

echo [INFO] Installing/Checking Python Dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements.txt >nul
pip install python-multipart >nul

:: Setup Node.js Frontend
echo [INFO] Installing/Checking Frontend Dependencies...
cd web
call npm install >nul
cd ..

echo.
echo ===================================================
echo     Installation Complete! Starting Servers...
echo ===================================================
echo.

:: Start Backend in a new window
echo [INFO] Starting API Server (Backend)...
start "AI Content Studio - API Backend" cmd /c "call .venv\Scripts\activate.bat && python server\main.py"

:: Start Frontend in a new window
echo [INFO] Starting Web UI (Frontend)...
cd web
start "AI Content Studio - Web UI" cmd /c "npm run dev"
cd ..

echo.
echo [SUCCESS] Both servers are starting up in separate windows! 
echo The Web UI will be available at http://localhost:3000
echo.
pause
