@echo off
echo ============================================
echo    Adaptive Learning System - Starting
echo ============================================
echo.

REM Check if virtual environment exists
if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo WARNING: .env file not found!
    echo Please run setup.bat first and configure your API keys.
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

echo Starting Adaptive Learning Platform...
echo.
echo Access the application at: http://localhost:5002
echo.
echo Press Ctrl+C to stop the server.
echo ============================================
echo.

REM Set environment variables and run
set PORT=5002
python app.py

pause
