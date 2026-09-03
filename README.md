# 智慧CRM系統 — 顧客查詢產品資訊 / 訂單查詢 Demo

對應「智慧CRM系統功能提案」#1（顧客查詢產品資訊，RAG）與 #2（顧客查詢訂單）的完整可運行專案。
單一聊天視窗，後端依訊息內容自動判斷是產品問題還是訂單查詢。

```
使用者輸入 → [後端 /api/chat]
                 ├─ 偵測到訂單編號 → 查詢訂單資料（#2）
                 └─ 一般問題 → ProductQueryAgent：向量化 → 查詢RAG資料庫 → LLM生成回答（#1）
```

## 專案結構

```
crm-rag-project/
├── backend/                 # FastAPI 服務
│   ├── app/
│   │   ├── main.py          # API 入口 /api/chat
│   │   ├── agent.py         # ProductQueryAgent（對應提案 #1 流程 01~04）
│   │   ├── orders.py        # 模擬訂單資料（對應提案 #2）
│   │   ├── documents.py     # 知識庫來源（讀取 app/data/ 底下的產品文案 + 保固/退換貨/運送付款/FAQ 政策文件）
│   │   ├── llm.py           # Qwen2.5 載入與生成
│   │   └── rag/              # chunking / embedding / Chroma 向量資料庫
│   └── requirements.txt
│
└── frontend/                 # React + Vite 顧客端聊天視窗
    └── src/components/SmartCRMChatWidget.jsx
```

## 需求環境

- Node.js 18+
- Python 3.10+
- 建議有 NVIDIA GPU（VRAM 12GB 以上）以執行 4-bit 量化的 Qwen2.5-7B-Instruct；
  沒有 GPU 可在 `backend/.env` 把 `USE_SMALL_MODEL` 設為 `true`，改用可在 CPU 執行的 Qwen2.5-1.5B-Instruct

## 用 VSCode 開啟

1. `File → Open Folder` 開啟 `crm-rag-project` 資料夾（根目錄，而非 backend 或 frontend 單獨開）
2. VSCode 會提示安裝建議套件（Python、ESLint、Prettier），可以直接安裝
3. 用內建終端機（`Ctrl+`` / `Cmd+``）開兩個終端機分頁，分別啟動 backend 與 frontend（見下方步驟）

## 啟動步驟

### 1) 啟動後端（終端機分頁 1）

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows 用: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

看到 `Application startup complete` 代表後端啟動成功。可以打開 http://localhost:8000/health 確認。

> 第一次呼叫聊天 API 時會即時下載 Embedding 模型與 LLM 模型，依網路速度可能需要數分鐘到數十分鐘，屬正常現象。
> 詳細說明請看 `backend/README.md`。

### 2) 啟動前端（終端機分頁 2）

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

終端機會顯示網址（預設 http://localhost:5173），用瀏覽器打開即可看到聊天客服視窗。

### 3) 測試

在聊天視窗輸入：
- 「無線滑鼠支援多少 DPI？」→ 觸發 #1 產品問答（RAG + LLM）
- 「智慧手錶有什麼特別功能？」→ 觸發 #1 產品問答，回答會提到隱藏的彩蛋錶面
- 「查詢訂單 A12345」→ 觸發 #2 訂單查詢（回傳配送進度時間軸）

## 之後可以延伸的部分

- 提案 #3（機器學習銷量預測）、#4（後台數據圖表生成）屬於不同架構（時間序列預測 / Dashboard + 排程推播），
  不在本專案範圍內，可作為獨立的後續模組開發
- 向量資料庫已改用持久化模式（`chromadb.PersistentClient`，索引存在 `backend/chroma_data/`），服務重啟不需要重新 embed；
  若 `documents.py` 知識庫內容有更動，需手動刪除 `backend/chroma_data/` 目錄以重建索引
- 訂單資料目前是寫死在 `backend/app/orders.py` 的模擬資料，之後可換成真實訂單資料庫查詢
