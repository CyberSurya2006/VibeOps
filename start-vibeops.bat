@echo off
title VibeOps Cockpit Launcher
echo ===================================================
echo               VibeOps Agent Cockpit                
echo ===================================================
echo Checking environment prerequisites...

:: 1. Verify Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ and try again.
    pause
    exit /b 1
)

:: 2. Setup virtual environment if missing
if not exist "venv" (
    echo Creating python virtual environment (venv)...
    python -m venv venv
)

:: 3. Activate venv and install packages
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing and verifying dependencies...
python -m pip install --upgrade pip
pip install -r backend\requirements.txt

:: 4. Start the FastAPI server in the background
echo Starting local agent server on http://localhost:8000...
start /b python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

:: 5. Open the frontend cockpit
echo Spawning cockpit interface in browser...
timeout /t 2 >nul
start "" "frontend\index.html"

echo ===================================================
echo [SUCCESS] VibeOps is running successfully!
echo Close this window to terminate the backend server.
echo ===================================================
echo Server Logs:
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
