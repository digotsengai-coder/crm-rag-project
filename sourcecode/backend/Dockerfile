# onnxruntime==1.29.0（requirements-local-llm.txt，llamaindex 引擎的 embedding 依賴）
# 沒有出 Python 3.10 的安裝包，只支援 3.11 以上，基底映像檔版本要跟著調整
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 設定 Python 環境變數
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# 安裝基本系統套件
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴檔案並安裝 Python 套件；RAG 只剩 llamaindex 引擎（需要 pgvector），
# requirements-local-llm.txt 不再是選用依賴，正式環境也要裝
COPY requirements.txt requirements-local-llm.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-local-llm.txt

# 複製後端程式碼
COPY . .

# 暴露埠號 (Cloud Run 預設為 8000)
EXPOSE 8000

# 使用 shell 形式啟動，確保 Cloud Run 輸入的 $PORT 變數能正確傳遞給 uvicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

