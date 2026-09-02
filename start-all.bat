@echo off
chcp 65001 >nul
cd /d %~dp0

echo 分別開啟兩個視窗啟動後端與前端...

start "CRM Backend (port 8000)" cmd /k "backend\start-backend.bat"
start "CRM Frontend (port 5173)" cmd /k "frontend\start-frontend.bat"

echo 已開啟兩個新視窗，請分別留意其中的訊息。
echo 後端網址：http://localhost:8000
echo 前端網址：http://localhost:5173
pause
