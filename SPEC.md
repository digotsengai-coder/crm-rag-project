# 智慧CRM系統 — 系統規格書

版本：對應 `master` 分支現況 | 最後更新：2026-09-03

## 1. 系統概述

### 1.1 目的

對應「智慧CRM系統功能提案」#1（顧客查詢產品資訊，RAG 問答）與 #2（顧客查詢訂單），提供單一聊天視窗
的線上客服機器人。後端依訊息內容自動判斷是「訂單查詢」還是「一般問題」，一般問題會走 RAG（檢索增強
生成）流程：從知識庫找出相關片段，交給 LLM 依片段內容生成回答。

提案 #3（銷量預測）、#4（後台數據圖表）不在本系統範圍內，屬於獨立模組。

### 1.2 核心設計原則

- **可切換性**：回答用的 LLM（本地/線上付費）、RAG 檢索引擎（自訂/LlamaIndex）都可以透過設定切換，
  不需要改程式碼，方便比較與擴充。
- **降級優雅**：任何外部相依（線上 LLM API、GPU）不可用時，系統仍能用本地模型/CPU 運作，不會整個掛掉。
- **輕量優先**：資料庫用 SQLite、向量索引用檔案持久化，不依賴額外的伺服器型基礎設施，方便本機開發與展示。

## 2. 系統架構

```
┌─────────────────────┐        HTTP/JSON         ┌──────────────────────────────────┐
│  前端（React + Vite）│ ───────────────────────▶ │        後端（FastAPI）             │
│  SmartCRMChatWidget  │ ◀─────────────────────── │                                    │
└─────────────────────┘                           │  ┌──────────────────────────────┐  │
                                                    │  │ 路由判斷（訂單 vs 產品問題）   │  │
                                                    │  └──────────────────────────────┘  │
                                                    │         │                │          │
                                              訂單查詢          一般問題（RAG）             │
                                                    │         ▼                          │
                                                    │  ┌───────────────┐                  │
                                                    │  │ ProductQueryAgent │               │
                                                    │  └───────┬───────┘                  │
                                                    │          │                          │
                                                    │  ┌───────▼────────┐   ┌───────────┐ │
                                                    │  │ RAG 檢索引擎     │   │ LLM 供應商 │ │
                                                    │  │（custom/llama-  │──▶│ 分派層     │ │
                                                    │  │  index，可切換） │   │           │ │
                                                    │  └────────────────┘   └─────┬─────┘ │
                                                    │                              │        │
                                                    └──────────────────────────────┼────────┘
                                                                                   ▼
                                              ┌────────────┬────────────┬──────────┬──────────┐
                                              │  本地 Qwen  │  Anthropic │  OpenAI  │ Google/xAI│
                                              │ 2.5 1.5B/7B │   Claude   │   GPT    │ Gemini/Grok│
                                              └────────────┴────────────┴──────────┴──────────┘

平行的資料儲存：
- SQLite：orders.db（訂單）、chat_log.db（對話紀錄，供摘要功能使用）
- 向量索引：chroma_data/（custom 引擎）、llamaindex_data/（LlamaIndex 引擎），兩者互不影響、可並存
- 知識庫原始檔：app/data/*.md（產品文案 + 政策文件）
```

## 3. 核心流程

### 3.1 使用者提問處理流程（`POST /api/chat`）

1. **Rate limit 檢查**：同一 IP 每 60 秒最多 20 次請求，超過回 429。
2. **輸入驗證**：訊息長度 1-500 字（Pydantic `Field` 驗證，超過直接回 422）。
3. **路由判斷**：用正規表示式比對訊息是否含訂單編號格式（`[A-Za-z]\d{5}`）或「訂單」字樣。
   - 命中 → 走訂單查詢（查 SQLite `orders` 表，回傳配送狀態時間軸資料）
   - 未命中 → 走產品/政策問答（RAG 流程）
4. **RAG 流程**（`ProductQueryAgent.generate_answer()`）：
   a. 若有對話歷史，把上一輪使用者問題接到這次的查詢字串前面（解決「那電池呢？」這種代名詞指涉問題，
      因為單獨這句話向量化後檢索不到正確片段）
   b. 用選定的 RAG 引擎檢索最相關的 `top_k`（預設 3）個片段
   c. **本地模型**：若最相關片段的檢索距離超過門檻（`RAG_NO_INFO_THRESHOLDS`），直接回「查無此資訊」，
      不呼叫 LLM——這是因為實測發現 1.5B 模型自行判斷「有沒有答案」非常不穩定，改用檢索分數判斷更可靠
   d. **線上模型**：能力足夠強，讓 LLM 自己判斷片段中有沒有答案（system prompt 內建這條規則）
   e. 組 prompt（system prompt + 對話歷史 + 檢索片段 + 使用者問題），呼叫選定的 LLM provider 生成回答
5. **紀錄**：問答結果寫入 `chat_log` 表（供 `/api/admin/summary` 使用），失敗不影響回應。

### 3.2 多輪對話

前端把已顯示的訊息組成 `history`（`[{role, content}]`）隨每次請求送出，後端只保留最近
`MAX_HISTORY_TURNS`（預設 4 輪）。**注意**：歷史只存在前端記憶體，重整頁面即消失，後端不持久化對話 session。

## 4. 資料設計

### 4.1 SQLite 資料表

| 資料庫檔案 | 資料表 | 欄位 | 用途 |
|---|---|---|---|
| `orders.db` | `orders` | code, status, eta, items | 模擬訂單資料，`status` 0-3 對應下單/出貨/配送中/送達 |
| `chat_log.db` | `chat_log` | id, created_at, client_ip, message, response_type, response_text | 每次問答紀錄，供當日摘要功能使用 |

兩者啟動時自動建表；`orders` 表空的話會灌入 5 筆種子資料。

### 4.2 知識庫與向量索引

| 檔案 | 內容 | 拆分邏輯 |
|---|---|---|
| `app/data/products_20_quirky.md` | 20 項產品行銷文案 | `product_parser.py`：依產品區塊切，每個產品的介紹段落/每條規格/特別功能各自一個 chunk（140 個） |
| `app/data/warranty_policy.md` | 保固與售後政策 | `policy_parser.py`：依 markdown H2 標題切，每個小節一個 chunk |
| `app/data/return_policy.md` | 退換貨規定 | 同上 |
| `app/data/shipping_payment.md` | 運送與付款方式 | 同上 |
| `app/data/faq.md` | 常見問題 | 同上，每個 Q&A 是一個 chunk |

`app/documents.py` 的 `get_all_chunks()` 合併以上所有 chunk（目前共 164 個），是兩套 RAG 引擎唯一的
資料來源，確保兩者索引內容一致。每個 chunk 統一格式：

```json
{"text": "...", "source": "檔名", "topic": "產品名稱或文件小節標題", "category": "分類", "product_id": "選填"}
```

### 4.3 向量索引持久化

| 引擎 | 索引儲存位置 | 相似度分數 |
|---|---|---|
| `custom`（預設） | `chroma_data/` | Chroma 原始 L2 距離，越低越相關 |
| `llamaindex` | `llamaindex_data/` | 1 − 相似度分數，統一成「越低越相關」跟 custom 引擎介面一致 |

兩者可同時建置、互不覆蓋，透過 `.env` 的 `RAG_ENGINE` 切換使用哪一個。知識庫內容更動後，需手動刪除
對應目錄才會觸發重建索引（服務有做「索引已存在就不重建」的檢查，避免每次啟動都重新 embed）。

## 5. API 規格

| Method | Path | 說明 |
|---|---|---|
| GET | `/health` | 健康檢查 |
| POST | `/api/warmup` | 手動觸發模型預載（服務啟動時已自動做一次） |
| GET | `/api/providers` | 回傳可選的 LLM 清單與是否已設定 API key |
| GET | `/api/admin/summary?date=YYYY-MM-DD` | 指定日期（預設今天）使用者提問的主題摘要，**目前無身分驗證** |
| POST | `/api/chat` | 主要問答端點，見下方 |

### `POST /api/chat`

```jsonc
// request
{
  "message": "無線滑鼠支援多少 DPI？",
  "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}],
  "provider": "local"  // local | anthropic | openai | google | xai
}

// response（產品/政策問答）
{"type": "product", "text": "...", "source": "Wireless Mouse（無線滑鼠）", "sources": [{"text":"...","topic":"...","distance":0.22}]}

// response（訂單查詢）
{"type": "order", "code": "A12345", "status": 2, "eta": "8月28日", "items": "..."}

// response（一般文字，例如缺訂單編號、查無資訊）
{"type": "text", "text": "..."}
```

## 6. 可配置項（`backend/.env`）

| 變數 | 預設 | 說明 |
|---|---|---|
| `USE_SMALL_MODEL` | `false` | `true` 用 Qwen2.5-1.5B（CPU/MPS 可跑），`false` 用 7B（需 GPU 4-bit 量化） |
| `RAG_ENGINE` | `custom` | `custom` 或 `llamaindex`，見第 4.3 節 |
| `CORS_ORIGINS` | `http://localhost:5173` | 允許的前端來源，逗號分隔 |
| `CHROMA_PERSIST_DIR` / `LLAMAINDEX_PERSIST_DIR` | `./chroma_data` / `./llamaindex_data` | 索引持久化路徑 |
| `CHAT_LOG_DB_PATH` / `ORDERS_DB_PATH` | `./chat_log.db` / `./orders.db` | SQLite 檔案路徑 |
| `LLM_KEYS_PATH` | `./llm_keys.json` | 線上 LLM provider 的 API key 設定檔路徑 |

`backend/llm_keys.json`（不進 git，範本見 `llm_keys.example.json`）：每個 provider 各自的 `api_key`
與要用的 `model` 名稱，沒填的 provider 在前端下拉選單會標示「尚未設定 API key」，選了會回友善錯誤訊息
而不是讓服務出錯。

## 7. 前端

單一元件 `SmartCRMChatWidget.jsx`：聊天氣泡（文字/產品回答/訂單時間軸卡片三種樣式）、模型選擇下拉選單
（呼叫 `/api/providers` 動態產生選項）、快速回覆按鈕。純 React state 管理對話，無外部狀態管理套件、
無路由，因為整個應用就是一個聊天視窗。

## 8. 已知限制與待辦事項

| 項目 | 現況 | 風險 |
|---|---|---|
| `/api/admin/summary` 無身分驗證 | 任何知道網址的人都能看到當日顧客提問內容 | **高** — 上線前必須修 |
| 對話歷史不持久化 | 存前端記憶體，重整頁面消失 | 中 — 影響使用體驗，非資安問題 |
| Rate limit 是記憶體版 | 多台伺服器水平擴充時各自獨立計數，形同無效 | 中 — 僅單機部署適用 |
| 摘要功能無排程 | 需手動呼叫 API 才會產生 | 低 — 功能已可用，缺自動化 |
| 訂單資料為模擬資料 | `orders.py` 種子資料寫死在程式碼 | 低 — 之後接真實訂單系統時介面不用改 |
| `NO_INFO_DISTANCE_THRESHOLD` 為經驗值 | 用 20 項產品的測試資料手動校準，非嚴謹統計 | 低 — 資料量變大應重新校準 |

## 9. 環境需求與啟動

詳見 [README.md](README.md)（整體）與 [backend/README.md](backend/README.md)（後端細節，含模型切換、
RAG 引擎切換、多 LLM provider 設定）。

- Python 3.10+、Node.js 18+
- 本地模型模式建議 GPU（7B）或 Apple Silicon MPS/CPU（1.5B）
- 線上模型模式需對應 provider 的 API key，無需本地跑模型
