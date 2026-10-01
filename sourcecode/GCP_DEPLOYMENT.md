# GCP 部署與執行指南 (Google Cloud Platform Deployment Guide)

本專案支援以 Docker 容器化技術部署至 GCP（Google Cloud Platform）。
主要提供兩種執行方式：
1. **Cloud Run**（推薦：Serverless 無伺服器架構，自動擴充、用多少算多少）
2. **Compute Engine VM**（使用 Docker Compose 一鍵啟動前後端）

---

## 方式 A：部署至 Cloud Run (推薦 Serverless 部署)

### 前置準備
1. 安裝 [Google Cloud SDK (gcloud CLI)](https://cloud.google.com/sdk/docs/install)。
2. 在 Google Cloud Console 建立專案，並登入 `gcloud`：
   ```bash
   gcloud auth login
   gcloud config set project <YOUR_GCP_PROJECT_ID>
   ```
3. 啟用必要 API 服務：
   ```bash
   gcloud services enable run.googleapis.com \
                          artifactregistry.googleapis.com \
                          cloudbuild.googleapis.com
   ```

---

### 步驟 1：部署 Backend 至 Cloud Run

1. 切換至 `sourcecode/backend` 目錄並提交建置：
   ```bash
   cd sourcecode/backend
   
   # 建置並推送 Docker 鏡像
   gcloud builds submit --tag gcr.io/<YOUR_GCP_PROJECT_ID>/crm-backend:latest .
   
   # 部署至 Cloud Run
   gcloud run deploy crm-backend \
     --image gcr.io/<YOUR_GCP_PROJECT_ID>/crm-backend:latest \
     --region asia-east1 \
     --platform managed \
     --allow-unauthenticated \
     --set-env-vars GEMINI_API_KEY=<YOUR_GEMINI_API_KEY>,RAG_PG_HOST=aws-0-ap-northeast-2.pooler.supabase.com,RAG_PG_PORT=6543,RAG_PG_DATABASE=postgres,RAG_PG_USER=postgres.<YOUR_SUPABASE_PROJECT_REF> \
     --set-secrets RAG_PG_PASSWORD=RAG_PG_PASSWORD:latest
   ```
2. 部署完成後，CLI 會輸出 **Backend Service URL**（例如：`https://crm-backend-xyz-de.a.run.app`）。

---

### 步驟 1.5：Corp Backend 的 MCP 金鑰（`@mcp` 需要）

Corp Backend 的 MCP endpoint 需要 Bearer 金鑰，**沒設定時 `/mcp` 與 `/mcp-admin` 一律回 503**。
`cloudbuild.yaml` 的 corp-backend 部署步驟會從 Secret Manager 帶入下面兩個 secret，**必須先建好，否則部署會失敗**：

| Secret | 用途 | 給誰用 |
|---|---|---|
| `MCP_API_KEY` | `/mcp`（唯讀，`search_order`） | 聊天 backend：填進**該公司**的「Chatbot 設定 → MCP 金鑰」 |
| `MCP_ADMIN_API_KEY` | `/mcp-admin`（管理與寫入） | 管理用途，**不要**填進任何公司的設定 |

1. 產生隨機金鑰並建立 secret（兩把必須不同）：
   ```bash
   python3 -c "import secrets;print(secrets.token_urlsafe(32))" | gcloud secrets create MCP_API_KEY --data-file=-
   python3 -c "import secrets;print(secrets.token_urlsafe(32))" | gcloud secrets create MCP_ADMIN_API_KEY --data-file=-
   ```
2. 讓 Cloud Run 執行身分能讀取（與 backend 讀 `RAG_PG_PASSWORD` 相同的服務帳號）：
   ```bash
   gcloud secrets add-iam-policy-binding MCP_API_KEY --member="serviceAccount:<CLOUD_RUN_SERVICE_ACCOUNT>" --role="roles/secretmanager.secretAccessor"
   gcloud secrets add-iam-policy-binding MCP_ADMIN_API_KEY --member="serviceAccount:<CLOUD_RUN_SERVICE_ACCOUNT>" --role="roles/secretmanager.secretAccessor"
   ```
3. 部署後，到管理後台選擇該公司 →「Chatbot 設定」：MCP URL 填 `https://<corp-backend 網址>/mcp`，
   MCP 金鑰貼上 `MCP_API_KEY` 的值（`gcloud secrets versions access latest --secret=MCP_API_KEY`）。

---

### 步驟 2：部署 Corp Frontend 至 Cloud Run

1. 將前端 `API_BASE_URL` 指定為步驟 1 取得的 Backend URL 並進行建置：
   ```bash
   cd sourcecode/corp-frontend
   
   # 建置前端 Docker 鏡像（帶入 Backend URL）
   gcloud builds submit \
     --tag gcr.io/<YOUR_GCP_PROJECT_ID>/crm-frontend:latest \
     --substitutions _VITE_API_BASE_URL=https://crm-backend-xyz-de.a.run.app .
   
   # 部署前端至 Cloud Run
   gcloud run deploy crm-frontend \
     --image gcr.io/<YOUR_GCP_PROJECT_ID>/crm-frontend:latest \
     --region asia-east1 \
     --platform managed \
     --allow-unauthenticated \
     --port 80
   ```
2. 完成後打開產生的 **Corp Frontend Service URL** 即可看到客服對話視窗。

---

### 自動化一鍵部署 (Cloud Build)

也可以直接在 `sourcecode/` 根目錄執行 Cloud Build：
```bash
cd sourcecode
gcloud builds submit --config=cloudbuild.yaml .
```

正式部署時應以 Cloud Build substitution `_CHAT_WIDGET_CLIENT_ID` 覆寫預設測試值，Widget 服務會以
`crm-chat-widget` 部署，Corp Frontend 則載入該服務的 `/chat-widget.js`。

---

## 方式 B：部署至 Compute Engine (GCP VM + Docker Compose)

適合需要自建 VM 或保持服務持續運作的環境。

### 步驟
1. 在 GCP 建立一台 Compute Engine VM (例如 Ubuntu 22.04 LTS)。
2. 在 VM 防火牆開啟 HTTP (Port 80) 與 Port 8000。
3. 連線至 VM 並安裝 Docker / Docker Compose：
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose-plugin
   ```
4. 將專案程式碼複製至 VM。
5. 設定 `.env` 檔案（填入 `GEMINI_API_KEY` 等資訊）。
6. 在 `sourcecode/` 目錄執行 Docker Compose：
   ```bash
   sudo docker compose up -d --build
   ```
7. 訪問 VM 的外網 IP 即可啟動並測試系統。

---

## 設定檔說明檔總覽

| 檔案路徑 | 說明 |
| :--- | :--- |
| [`backend/Dockerfile`](backend/Dockerfile) | Backend Python 3.10 FastAPI 容器設定 |
| [`corp-backend/Dockerfile`](corp-backend/Dockerfile) | Corp Backend Python 3.10 FastAPI (Firebase Firestore) 容器設定 |
| [`corp-frontend/Dockerfile`](corp-frontend/Dockerfile) | Corp Frontend Vite Node + Nginx 雙階段建置容器設定 |
| [`corp-frontend/nginx.conf`](corp-frontend/nginx.conf) | Corp Frontend Nginx 靜態資源與路由設定 |
| [`admin-frontend/Dockerfile`](admin-frontend/Dockerfile) | Admin Frontend Vite Node + Nginx 雙階段建置容器設定 |
| [`admin-frontend/nginx.conf`](admin-frontend/nginx.conf) | Admin Frontend Nginx 靜態資源與路由設定 |
| [`chat-widget/Dockerfile`](chat-widget/Dockerfile) | 獨立 Chat Widget 建置與 Nginx 容器設定 |
| [`chat-widget/nginx.conf`](chat-widget/nginx.conf) | 單一 `chat-widget.js` 靜態資源服務設定 |
| [`docker-compose.yml`](docker-compose.yml) | Docker Compose 本地與 VM 一鍵啟動檔 |
| [`cloudbuild.yaml`](cloudbuild.yaml) | Google Cloud Build CI/CD 自動建置指令檔 |
