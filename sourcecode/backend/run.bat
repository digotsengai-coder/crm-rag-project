@echo off
cd /d "%~dp0"

echo ================================
echo Current folder:
cd
echo ================================

if not exist "venv\Scripts\python.exe" (
    echo.
    echo ERROR: venv\Scripts\python.exe not found
    echo.
    pause
    exit /b 1
)

echo Found venv Python.
echo.

venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

pause