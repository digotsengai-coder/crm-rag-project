# Backend — 智慧CRM系統 API

FastAPI 服務，提供 `/api/chat`，對應提案 #1（產品問答 RAG）與 #2（訂單查詢）。

## 環境需求

- Python 3.10+
- 完整版 LLM（`USE_SMALL_MODEL=false`，預設）：建議有 NVIDIA GPU，VRAM 12GB 以上（4-bit 量化跑 Qwen2.5-7B-Instruct）
- 若沒有 GPU：把 `.env` 的 `USE_SMALL_MODEL` 改成 `true`，會改用 CPU 也能跑的 Qwen2.5-1.5B-Instruct（速度較慢）

## 啟動步驟

```bash
cd backend
python -m venv venv

# macOS / Linux
source venv/bin/activate
# Windows (PowerShell)
venv\Scripts\Activate.ps1

pip install -r requirements.txt

cp .env.example .env
# 需要的話編輯 .env，把 USE_SMALL_MODEL 改成 true/false

uvicorn app.main:app --reload --port 8000
```

啟動後可用瀏覽器打開 http://localhost:8000/health 確認服務正常。

## 注意事項

- **第一次呼叫 `/api/chat`（產品問題）時**，會即時下載 Embedding 模型與 LLM 模型，
  依網路速度可能需要數分鐘到數十分鐘，屬正常現象，请耐心等候。
- 若想在服務啟動時就先載入模型（避免使用者第一次提問要等很久），
  可以在啟動後手動呼叫一次：
  ```bash
  curl -X POST http://localhost:8000/api/warmup
  ```
- `bitsandbytes` 的 4-bit 量化主要支援 NVIDIA GPU（CUDA），
  若在 Windows 沒有 GPU 或安裝上遇到問題，請改用 `USE_SMALL_MODEL=true`。
- 向量資料庫（Chroma）目前是記憶體版，每次重啟服務都會重新建立索引；
  正式環境可改用 `chromadb.PersistentClient`。

## API

### `POST /api/chat`

```json
// request
{ "message": "掃地機器人的電池可以用多久？" }

// response（產品問題）
{ "type": "product", "text": "...", "source": "產品規格手冊", "sources": [...] }

// response（訂單查詢）
{ "type": "order", "code": "A12345", "status": 2, "eta": "8月28日", "items": "..." }
```
