FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 設定 Python 環境變數
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8001

# 安裝基本系統套件
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴檔案並安裝 Python 套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製後端程式碼
COPY . .

# 暴露埠號 (預設為 8001)
EXPOSE 8001

# 使用 shell 形式啟動，確保傳遞 PORT 變數給 uvicorn
# --proxy-headers / --forwarded-allow-ips='*'：Cloud Run 的 HTTPS 在前端終止，容器內看到的是 http。
# 沒有信任 X-Forwarded-Proto 的話，Starlette 的轉址（例如 /mcp → /mcp/）會給出 http:// 的 Location，
# client 跟著轉會壞掉（POST 與金鑰失效）。Cloud Run 的前端是唯一能連到容器的來源，信任所有轉發標頭是安全的。
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001} --proxy-headers --forwarded-allow-ips='*'"]
