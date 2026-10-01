# Corp Backend (FastAPI + GCP Firebase Firestore CRUD)

`corp-backend` 是基於 Python 3.10 與 FastAPI 打造的後端微服務，提供與 Google Cloud Platform (GCP) Firebase Firestore 資料庫無縫整合的 RESTful API 介面，支援完整的 CRUD 操作。

---

## 核心功能與特色

- **FastAPI 效能與自動化文件**：提供高吞吐量非同步架構，並自動產生 OpenAPI (`/docs`) 與 ReDoc (`/redoc`) 文件。
- **GCP Firebase Admin SDK 整合**：封裝完整的 Firestore Document CRUD 操作。
- **多重憑證載入機制**：
  1. `FIREBASE_CREDENTIALS_PATH`: 服務帳戶 JSON 密鑰檔案路徑
  2. `FIREBASE_CREDENTIALS_JSON`: 服務帳戶 JSON 字串內容 (適合 CI/CD 或 Docker 容器環境變數)
  3. `GOOGLE_APPLICATION_CREDENTIALS`: 標準 GCP 環境變數
  4. **GCP Application Default Credentials (ADC)**: 部署於 GCP Cloud Run / GKE 時可免憑證檔自動認證
- **健壯的資料處理解析**：自動將 Firestore 特有的 `Timestamp` / `DatetimeWithNanoseconds` 轉換為 ISO8601 字串，防止 JSON 序列化失敗。
- **靈活的 Docker 容器支援**：基於 `python:3.10-slim` 映像檔建立。

---

## 專案結構

```
corp-backend/
├── app/
│   ├── __init__.py
│   ├── config.py           # Pydantic Settings 環境變數管理
│   ├── crud.py             # Firestore 典範 CRUD 操作層
│   ├── firebase_client.py  # Firebase Admin SDK 初始化與 Client 管理
│   ├── schemas.py          # Pydantic Request/Response 資料模型
│   ├── main.py             # FastAPI 應用程式主進入點
│   └── routers/
│       ├── firestore.py    # Firestore CRUD API 路由 (/api/v1/collections/...)
│       └── health.py       # 服務健康檢查路由 (/health)
├── .dockerignore
├── .env.example            # 環境變數範本檔
├── Dockerfile              # Docker 容器化設定 (python:3.10-slim)
├── README.md               # 服務說明文件
└── requirements.txt        # Python 套件依賴
```

---

## 環境變數設定

請複製 `.env.example` 並重新命名為 `.env`：

```bash
cp .env.example .env
```

`.env` 內容說明：

```env
PORT=8001
API_V1_STR=/api/v1
GCP_PROJECT_ID=your-gcp-project-id

# 憑證載入 (任選一種方式)
FIREBASE_CREDENTIALS_PATH=./path/to/serviceAccountKey.json
# FIREBASE_CREDENTIALS_JSON={"type": "service_account", ...}

# MCP endpoint 的 Bearer 金鑰（各自獨立，未設定時對應 endpoint 回 503）
MCP_API_KEY=<隨機字串>
MCP_ADMIN_API_KEY=<另一組隨機字串>
```

### MCP endpoint

| 路徑 | tools | 金鑰 | 使用者 |
|---|---|---|---|
| `/mcp` | `search_order`（唯讀；訂單編號與電話號碼都符合才回傳）、`get_latest_promotions`（唯讀；公司最新活動，預設「全館 9 折」，內容改 `app/promotions.py` 的 `PROMOTIONS`） | `MCP_API_KEY` | 聊天後端（LLM） |
| `/mcp-admin` | `get_order`、`list_orders`、`create_order`、`update_order`、`delete_order` | `MCP_ADMIN_API_KEY` | 管理用途，聊天後端不使用 |

請求需帶 `Authorization: Bearer <金鑰>`；`get_order` 只憑訂單編號就回傳整筆訂單、`list_orders` 會回傳所有訂單，兩者都沒有驗證或租戶隔離，放在 `/mcp` 會讓人在聊天視窗逐筆枚舉別人的訂單，所以只放 `/mcp-admin`。
**Host header 檢查**：MCP SDK 內建 DNS rebinding 防護，預設只放行 `localhost`。部署到 Cloud Run 後 Host 是 `*.run.app`，
不處理的話所有已通過認證的請求都會被回 `421 Invalid Host header`。目前在 Cloud Run 上（有 `K_SERVICE`）且沒設定時會自動停用，
邊界改由 Bearer 金鑰把關；也可以用 `MCP_ALLOWED_HOSTS`（逗號分隔）只放行指定網域。
測試：`pip install -r requirements-dev.txt` 後在本目錄執行 `python -m pytest tests`。

---

## 本地開發與啟動方式

### 1. 安裝套件

建議建立虛擬環境 (`venv`) 並安裝依賴：

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. 啟動 FastAPI 開發伺服器

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

啟動後即可存取：
- **Swagger API 文件**: [http://localhost:8001/docs](http://localhost:8001/docs)
- **健康檢查**: [http://localhost:8001/health](http://localhost:8001/health)

---

## RESTful API Endpoints 規格

### 1. 健康檢查

- **`GET /health`**
  - 回應：`{"status": "healthy", "app_name": "Corp Backend API", "firebase_connected": true, ...}`

---

### 2. Firestore CRUD API (`/api/v1/collections/{collection_name}/docs`)

#### A. 新增文件 (Create)
- **`POST /api/v1/collections/{collection_name}/docs`**
- **Body**:
  ```json
  {
    "doc_id": "custom-doc-001",
    "data": {
      "company_name": "Acme Corp",
      "tax_id": "12345678",
      "status": "active"
    }
  }
  ```
  *(若不提供 `doc_id`，Firestore 將自動生成隨機 ID)*

#### B. 查詢文件列表 (List)
- **`GET /api/v1/collections/{collection_name}/docs?limit=50&order_by=company_name`**

#### C. 取得單一文件 (Read)
- **`GET /api/v1/collections/{collection_name}/docs/{doc_id}`**

#### D. 完全覆蓋文件 (Overwrite / Put)
- **`PUT /api/v1/collections/{collection_name}/docs/{doc_id}`**
- **Body**:
  ```json
  {
    "company_name": "Acme Corp Ltd.",
    "tax_id": "12345678",
    "updated_by": "admin"
  }
  ```

#### E. 增量更新文件 (Merge / Patch)
- **`PATCH /api/v1/collections/{collection_name}/docs/{doc_id}`**
- **Body**:
  ```json
  {
    "data": {
      "status": "inactive"
    },
    "merge": true
  }
  ```

#### F. 刪除文件 (Delete)
- **`DELETE /api/v1/collections/{collection_name}/docs/{doc_id}`**

---

## Docker 容器啟動

```bash
# 建置 Docker 映像檔
docker build -t corp-backend .

# 執行容器 (掛載本地 .env)
docker run -d --name corp_backend -p 8001:8001 --env-file .env corp-backend
```
