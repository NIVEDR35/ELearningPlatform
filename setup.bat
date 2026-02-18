@echo off
echo ============================================
echo    Adaptive Learning System - Setup
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/4] Python found!
python --version
echo.

REM Create virtual environment
echo [2/4] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists. Skipping creation.
) else (
    python -m venv venv
    echo Virtual environment created!
)
echo.

REM Activate virtual environment and install dependencies
echo [3/4] Installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
echo.

REM Create .env file if it doesn't exist
echo [4/4] Setting up environment variables...
if not exist .env (
    echo Creating .env file...
    echo # Adaptive Learning System Configuration > .env
    echo. >> .env
    echo # Google Gemini API Key (Get from https://makersuite.google.com/app/apikey^) >> .env
    echo GEMINI_API_KEY=your_gemini_api_key_here >> .env
    echo. >> .env
    echo # YouTube API Key (Get from https://console.cloud.google.com/^) >> .env
    echo YOUTUBE_API_KEY=your_youtube_api_key_here >> .env
    echo. >> .env
    echo # Flask Settings >> .env
    echo FLASK_ENV=development >> .env
    echo FLASK_DEBUG=True >> .env
    echo SECRET_KEY=your-secret-key-change-this >> .env
    echo PORT=5002 >> .env
    echo.
    echo IMPORTANT: Please edit the .env file and add your API keys!
    echo.
) else (
    echo .env file already exists.
)

echo.
echo ============================================
echo    Setup Complete!
echo ============================================
echo.
echo IMPORTANT: Before running, please:
echo 1. Edit the .env file and add your API keys:
echo    - GEMINI_API_KEY (from https://makersuite.google.com/app/apikey)
echo    - YOUTUBE_API_KEY (from https://console.cloud.google.com/)
echo.
echo 2. Run the application using: run.bat
echo.
pause
