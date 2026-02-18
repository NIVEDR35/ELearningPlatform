@echo off
echo Stopping Adaptive Learning System...
echo.

REM Find and kill Python processes running app.py
for /f "tokens=2" %%a in ('tasklist /fi "imagename eq python.exe" /fo list ^| find "PID"') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo Server stopped.
pause
