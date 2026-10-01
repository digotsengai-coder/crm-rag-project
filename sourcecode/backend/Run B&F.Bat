@echo off
setlocal

title CRM System Launcher

echo ========================================
echo       Starting CRM System
echo ========================================
echo.

REM ===== Backend path =====
set "BACKEND=%~dp0"

REM ===== Frontend path =====
set "FRONTEND=%~dp0..\frontend"

echo Backend path:
echo %BACKEND%

echo.
echo Frontend path:
echo %FRONTEND%
echo.

REM ==========================================
REM Start Backend
REM ==========================================
echo Starting Backend...

start "CRM Backend - Port 8000" cmd /k ^
cd /d "%BACKEND%" ^&^& ^
"%BACKEND%venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000

REM ==========================================
REM Start Frontend
REM ==========================================
echo Starting Frontend...

start "CRM Frontend - Port 5173" cmd /k ^
cd /d "%FRONTEND%" ^&^& ^
npm run dev

REM ==========================================
REM Wait
REM ==========================================
echo.
echo Waiting for frontend...
timeout /t 7 /nobreak >nul

REM ==========================================
REM Open Chrome
REM ==========================================
echo Opening Chrome...

if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:5173"
    goto done
)

if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" "http://localhost:5173"
    goto done
)

REM Try Chrome from PATH
start "" chrome "http://localhost:5173"

:done
echo.
echo ========================================
echo Backend  : http://localhost:8000
echo Frontend : http://localhost:5173
echo ========================================

timeout /t 3 /nobreak >nul
endlocal
exit