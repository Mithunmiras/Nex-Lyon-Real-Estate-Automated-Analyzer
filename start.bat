@echo off
echo.
echo  ====================================================
echo   Nex-Lyon Real Estate Analyzer - One-Click Setup
echo  ====================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Node.js not found. Install from https://nodejs.org/
    pause
    exit /b 1
)

echo  [1/4] Installing Python dependencies...
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    python -m pip install -r requirements.txt
)

echo  [2/4] Installing frontend dependencies...
cd frontend
call npm install --silent
if errorlevel 1 (
    echo  [ERROR] npm install failed
    pause
    exit /b 1
)

echo  [3/4] Building frontend...
call npm run build --silent
if errorlevel 1 (
    echo  [ERROR] Frontend build failed
    pause
    exit /b 1
)

echo  [4/4] Starting server...
cd ..
echo.
echo  ====================================================
echo   Open your browser at: http://localhost:5000
echo  ====================================================
echo.
python server.py
pause
