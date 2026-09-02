@echo off
chcp 65001 >nul
cd /d %~dp0

if not exist venv (
    echo [1/4] 建立虛擬環境...
    python -m venv venv
)

echo [2/4] 啟用虛擬環境...
call venv\Scripts\activate.bat

echo [3/4] 安裝套件中（第一次執行會比較久）...
pip install -r requirements.txt

if not exist .env (
    copy .env.example .env
    echo 已建立 .env（預設 USE_SMALL_MODEL=false，如果沒有GPU請自行改成 true）
)

echo [4/4] 啟動後端服務 http://localhost:8000 ...
echo 第一次呼叫聊天功能時會下載模型，需要一些時間，屬正常現象。
uvicorn app.main:app --reload --port 8000

pause
