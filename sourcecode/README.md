# 智慧CRM系統 — 顧客查詢產品資訊 / MCP 查詢 Demo

對應「智慧CRM系統功能提案」#1（顧客查詢產品資訊，RAG）的完整可運行專案，並可透過公司自己的 MCP server 擴充查詢功能（例如訂單）。
單一聊天視窗，訊息以 `@MCP` 開頭（名稱可在後台「Chatbot 設定」改成公司自訂的名稱，例如 `@阿柴`）時由 LLM 透過該公司的 MCP tools 回答，其他訊息走 RAG。

```
使用者輸入 → [後端 /api/chat]
                 ├─ 以 @mcp 開頭 → LLM 透過公司 MCP server 的 tools 回答（Gemini）
                 └─ 其他問題 → ProductQueryAgent：向量化 → 查詢RAG資料庫 → LLM生成回答（#1）
```

## 專案結構

```
crm-rag-project/
├── backend/                 # FastAPI 服務
│   ├── app/
│   │   ├── main.py          # API 入口 /api/chat
│   │   ├── agent.py         # ProductQueryAgent（對應提案 #1 流程 01~04）
│   │   ├── mcp_client.py    # 通用 MCP client（2026-07-28 無狀態協定）
│   │   ├── mcp_chat.py      # @mcp 對話路徑
│   │   ├── documents.py     # 知識庫來源（讀取 app/data/ 底下的產品文案 + 保固/退換貨/運送付款/FAQ 政策文件）
│   │   ├── llm.py           # Qwen2.5 載入與生成
│   │   └── rag/              # chunking / embedding / Chroma 向量資料庫
│   └── requirements.txt
│
├── corp-frontend/            # React + Vite 顧客端購物介面
├── admin-frontend/           # React + Vite 後台管理介面
└── chat-widget/              # 可獨立部署與嵌入的 React 聊天元件
```

## 前端樣式架構

三個前端均使用 Tailwind CSS v4，但維持獨立 package、lockfile、Vite 與 Prettier 設定，不使用 monorepo workspace 或跨 App 樣式 import。

| App            | Tailwind 入口                   | 元件樣式位置                      | 特殊整合                                                                |
| -------------- | ------------------------------- | --------------------------------- | ----------------------------------------------------------------------- |
| Corp Frontend  | `corp-frontend/src/index.css`   | TSX 內的靜態 utility mapping      | 保留 1120、820、560px 斷點                                              |
| Admin Frontend | `admin-frontend/src/styles.css` | `admin-frontend/src/uiStyles.ts`  | 保留 Ant Design，以 descendant variants 與必要的 important utility 覆寫 |
| Chat Widget    | `chat-widget/src/widget.css`    | `chat-widget/src/widgetStyles.ts` | CSS 以 `?inline` 注入 Shadow DOM，保留 runtime theme variables          |

Tailwind 入口不載入 Preflight，避免改變 Ant Design、原生控制項與既有瀏覽器預設。入口 CSS 只放 `@theme` token、字型與共用動畫；元件外觀使用 TSX utility，不新增傳統 selector class。

### Token 與 utility 規則

- 4px spacing 基準可精準表示的尺寸使用數字 utility，例如 9px → `2.25`、10px → `2.5`、13px → `3.25`、21px → `5.25`。
- 字級使用 Tailwind 預設字級或語意化 `--text-*` token；圓角使用 `--radius-*` token，不以 spacing utility 代替。
- 重複顏色、字級、圓角、陰影與動畫集中於 `@theme`。只有 `clamp()`、複合 grid、動態 viewport 與一次性圖片漸層使用 arbitrary value。
- class 必須是完整靜態字串；組合時使用 `tw()`，不可動態拼接 utility 名稱。
- 單邊框 utility 不與 `border-solid` 併用，避免其他邊出現預設框線。
- 靜態樣式不得保留 inline style；runtime theme、自動高度與動態圖片 URL 例外。

### 格式化與驗證

每個 App 的 `prettier-plugin-tailwindcss` 會依官方順序排列 class，並透過 `tailwindStylesheet` 識別該 App 的自訂 token。修改前端樣式後，在對應 App 執行：

```bash
npm run format
npm run format:check
npm run build
```

Chat Widget 另需執行：

```bash
npm run inject:target
```

完成後應以瀏覽器檢查 hover、focus、disabled、active、reduced-motion、響應式斷點、Ant portal 與 Shadow DOM 隔離；視覺等價調整以 computed style 為驗收依據。

## 需求環境

- Node.js 18+
- Python 3.10+
- 建議有 NVIDIA GPU（VRAM 12GB 以上）以執行 4-bit 量化的 Qwen2.5-7B-Instruct；
  沒有 GPU 可在 `backend/.env` 把 `USE_SMALL_MODEL` 設為 `true`，改用可在 CPU 執行的 Qwen2.5-1.5B-Instruct

## 用 VSCode 開啟

1. `File → Open Folder` 開啟 `crm-rag-project` 資料夾（根目錄，而非任一前後端目錄單獨開）
2. VSCode 會提示安裝建議套件（Python、ESLint、Prettier），可以直接安裝
3. 用內建終端機（`Ctrl+`` / `Cmd+``）分別啟動所需的前後端與 Widget 服務（見下方步驟）

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

### 2) 啟動 Corp Frontend（終端機分頁 2）

```bash
cd corp-frontend
npm install
cp .env.example .env
npm run dev
```

終端機會顯示網址（預設 http://localhost:5173），用瀏覽器打開即可看到聊天客服視窗。

### 3) 啟動 Chat Widget（終端機分頁 3）

```bash
cd chat-widget
npm install
cp .env.example .env
npm run build
npm run preview
```

Widget 預設由 http://localhost:5175/chat-widget.js 提供，嵌入標籤必須包含 `data-client-id`。

### 4) 啟動 Admin Frontend（終端機分頁 4）

```bash
cd admin-frontend
npm install
cp .env.example .env
npm run dev
```

終端機會顯示網址（預設 http://localhost:5174），用瀏覽器打開即可進入後台管理介面。

### 5) 測試

在聊天視窗輸入：

- 「無線滑鼠支援多少 DPI？」→ 觸發 #1 產品問答（RAG + LLM）
- 「智慧手錶有什麼特別功能？」→ 觸發 #1 產品問答，回答會提到隱藏的彩蛋錶面
- 「@mcp 幫我查訂單 A12345」→ 由 LLM 透過該公司 MCP server 的 tools 查詢（需先在後台設定 MCP URL 與金鑰，且使用 Gemini 或本地模型）

## 之後可以延伸的部分

- 提案 #3（機器學習銷量預測）、#4（後台數據圖表生成）屬於不同架構（時間序列預測 / Dashboard + 排程推播），
  不在本專案範圍內，可作為獨立的後續模組開發
- 向量資料庫已改用持久化模式（`chromadb.PersistentClient`，索引存在 `backend/chroma_data/`），服務重啟不需要重新 embed；
  若 `documents.py` 知識庫內容有更動，需手動刪除 `backend/chroma_data/` 目錄以重建索引
- 訂單等查詢功能由各公司的 MCP server 提供（範例見 `corp-backend`），backend 不再內建模擬訂單資料
