@echo off
chcp 65001 >nul
cd /d %~dp0

if not exist node_modules (
    echo [1/3] 安裝 npm 套件中...
    call npm install
)

if not exist .env (
    copy .env.example .env
    echo 已建立 .env
)

echo [2/3] 啟動前端服務 http://localhost:5173 ...
echo [3/3] 瀏覽器打開終端機顯示的網址即可看到聊天視窗
call npm run dev

pause
