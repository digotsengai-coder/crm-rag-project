# Backend — 智慧CRM系統 API

FastAPI 服務，提供 `/api/chat`，對應提案 #1（產品問答 RAG）與 #2（訂單查詢），
另外有管理者用的 `/api/admin/summary`（當日提問摘要）跟 `/api/providers`（可用 LLM 清單）。

## 環境需求

- Python 3.10+
- 完整版本地 LLM（`USE_SMALL_MODEL=false`，預設）：建議有 NVIDIA GPU，VRAM 12GB 以上（4-bit 量化跑 Qwen2.5-7B-Instruct）
- 若沒有 GPU：把 `.env` 的 `USE_SMALL_MODEL` 改成 `true`，改用 CPU/Apple Silicon MPS 也能跑的 Qwen2.5-1.5B-Instruct（速度較慢）
- 或完全不跑本地模型，改用線上付費 API（見下方「切換回答模型」）

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
cp llm_keys.example.json llm_keys.json
# 需要的話編輯 .env / llm_keys.json，見下面兩節說明

uvicorn app.main:app --reload --port 8000
```

啟動後可用瀏覽器打開 http://localhost:8000/health 確認服務正常。服務啟動時會自動預載
Embedding 與本地 LLM 模型（第一次啟動會需要下載，依網路速度可能要數分鐘到數十分鐘）。

## 切換回答模型

`/api/chat` 的 `provider` 欄位決定用哪個 LLM 回答（前端聊天視窗有下拉選單可以選）：

| provider | 說明 | 需要什麼 |
|---|---|---|
| `local`（預設） | 本地 Qwen2.5，`USE_SMALL_MODEL` 決定跑 1.5B 或 7B | 不需要 API key，免費但速度較慢 |
| `anthropic` | Claude | `llm_keys.json` 填 `anthropic.api_key` |
| `openai` | GPT | `llm_keys.json` 填 `openai.api_key` |
| `google` | Gemini | `llm_keys.json` 填 `google.api_key` |
| `xai` | Grok | `llm_keys.json` 填 `xai.api_key` |

`llm_keys.json` 不會進 git（已加進 `.gitignore`），每個人要自己填自己的 key。
沒填 key 的 provider 選了會友善回覆「尚未設定 API key」，不會讓服務掛掉；
`GET /api/providers` 可以查詢目前有哪些 provider 已經設定好 key。

## RAG 引擎切換

`.env` 的 `RAG_ENGINE` 決定檢索用哪套實作，兩套功能等價、介面相同，可以隨時切換：

- `custom`（預設）：這個專案自己寫的 Chroma + e5 embedding 檢索邏輯
- `llamaindex`：改用 LlamaIndex 的 `VectorStoreIndex` 做索引與檢索

兩套引擎共用同一套語意拆分規則（`app/rag/product_parser.py`），差別只在「怎麼建索引、怎麼查」，
所以檢索結果品質應該接近，但兩套引擎各自的距離分數尺度不同，`app/config.py` 的
`RAG_NO_INFO_THRESHOLDS` 分開設定「查無資訊」的判斷門檻。索引檔也分開存放
（`chroma_data/` vs `llamaindex_data/`），互不影響，可以兩套都建好、隨時切換不用重建。

知識庫檔案都在 `app/data/`：`products_20_quirky.md`（20 項產品文案，用 `product_parser.py` 拆分）
與 `warranty_policy.md` / `return_policy.md` / `shipping_payment.md` / `faq.md`（保固、退換貨、運送
付款、常見問題，用 `policy_parser.py` 依 markdown 標題拆分）。`app/documents.py` 的 `get_all_chunks()`
把兩類文件的 chunk 合併成一份清單，兩套 RAG 引擎都吃同一份。若知識庫內容有更動，兩套引擎的索引
都要手動刪除對應目錄（`chroma_data/` / `llamaindex_data/`）才會重建。

## 注意事項

- 第一次啟動會需要下載 Embedding 模型與本地 LLM 模型，依網路速度可能需要數分鐘到數十分鐘
- 向量資料庫（Chroma / LlamaIndex）都已改用持久化模式，服務重啟不需要重新 embed
- `bitsandbytes` 的 4-bit 量化只支援 NVIDIA GPU（CUDA），沒有 GPU 請用 `USE_SMALL_MODEL=true`
- `/api/admin/summary` 目前沒有任何身分驗證，正式上線前必須加上管理者登入/權限檢查

## API

### `POST /api/chat`

```json
// request
{
  "message": "無線滑鼠支援多少 DPI？",
  "history": [],
  "provider": "local"
}

// response（產品問題）
{ "type": "product", "text": "...", "source": "Wireless Mouse（無線滑鼠）", "sources": [...] }

// response（訂單查詢）
{ "type": "order", "code": "A12345", "status": 2, "eta": "8月28日", "items": "..." }
```

### `GET /api/providers`

回傳可選的 LLM 清單與是否已設定 key，供前端畫下拉選單用。

### `GET /api/admin/summary?date=YYYY-MM-DD`

回傳指定日期（預設今天，UTC）使用者提問的主題摘要，`date` 省略時查今天。
