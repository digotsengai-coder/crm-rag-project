# Backend — 智慧CRM系統 API

FastAPI 服務，提供 `/api/chat`，對應提案 #1（產品問答 RAG），並支援 `@mcp` 開頭的訊息由 LLM 透過公司 MCP server 的 tools 回答，
另外有管理者用的 `/api/admin/summary`（當日提問摘要）跟 `/api/providers`（可用 LLM 清單）。

## 環境需求

- Python 3.10+
- 本地 LLM（provider=local）固定用 **MLX + `mlx-community/Qwen3.5-2B-4bit`**（模型名稱可用
  `.env` 的 `MLX_LLM_MODEL_NAME` 覆蓋），**只支援 Apple Silicon（M 系列晶片）Mac**，吃 Mac 的
  Metal GPU 加速；需要額外安裝 `requirements-mlx.txt`（`pip install -r requirements-mlx.txt`）。
  `app/llm.py` 預設用 `enable_thinking=False` 關掉內部思考過程直接回答，輸出偶爾還是簡體字，
  `generate()` 會自動做簡轉繁（台灣用語）後處理。
  **在非 Apple Silicon 機器上（包含正式環境 Cloud Run）呼叫 provider=local 會直接回錯誤**——
  正式環境固定用線上 provider，不提供本地 LLM 這個選項；本機開發如果不是 Apple Silicon，也只能
  選線上 provider。
  （原本用的 openbmb/MiniCPM5-2B 已經拿掉：一來它在 Apple Silicon 的 MPS 上會直接當機
  segfault，二來它要求的 `transformers>=5.6` 會跟其他想接的套件版本衝突。）
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
| `local`（預設） | 本地 Qwen3.5-2B（MLX） | 不需要 API key、免費，但僅限 Apple Silicon 開發機 |
| `anthropic` | Claude | `llm_keys.json` 填 `anthropic.api_key` |
| `openai` | GPT | `llm_keys.json` 填 `openai.api_key` |
| `google` | Gemini | `llm_keys.json` 填 `google.api_key` |
| `xai` | Grok | `llm_keys.json` 填 `xai.api_key` |

`llm_keys.json` 不會進 git（已加進 `.gitignore`），每個人要自己填自己的 key。
沒填 key 的 provider 選了會友善回覆「尚未設定 API key」，不會讓服務掛掉；
`GET /api/providers` 可以查詢目前有哪些 provider 已經設定好 key。

## RAG 引擎

檢索固定用 `llamaindex` 引擎：LlamaIndex 的 `VectorStoreIndex` + **pgvector（PostgreSQL）**
做索引與檢索（本地 embedding），需要另外安裝 `requirements-local-llm.txt`。支援單一文件的
新增/刪除/更新（見下方「知識庫文件管理」），不用整批重建索引。

本地 embedding 模型用哪個實作由 `.env` 的 `EMBEDDING_BACKEND` 決定：
- `onnx_int8`（預設）：`app/rag/onnx_embedding.py` 直接用 `onnxruntime` 跑 int8 量化版
  `multilingual-e5-base`（`Teradata/multilingual-e5-base` 這個 repo 轉換的），檔案小、
  記憶體佔用低，繞過官方的 `optimum` 整合套件（跟 `mlx-lm` 等套件要求的 `transformers`
  版本硬衝突，無解）。
- `huggingface`：原本的 fp32 `HuggingFaceEmbedding`，int8 版本有問題時可以切回這個，
  不用改程式碼，`.env` 設 `EMBEDDING_BACKEND=huggingface` 即可，但要先手動安裝
  `pip install -r requirements-embedding-fallback.txt`（torch/transformers 這個分支專用，
  正式 image 不會裝，見該檔案開頭說明）。

（原本還有兩套：自製的 `custom` 引擎——Chroma + 手寫檢索，已隨 `llamaindex` 引擎改用
pgvector 一起退休；線上 Gemini embedding + Chroma 的 `gemini`/`online` 引擎也已移除，
embedding 統一改用本地 llamaindex，不再依賴線上 embedding API。線上 `google` provider
目前只用在 LLM 回答，見上方「切換回答模型」。）

知識庫檔案都在 `app/data/`：`products_20_quirky.md`（20 項產品文案，用 `product_parser.py` 拆分）
與 `warranty_policy.md` / `return_policy.md` / `shipping_payment.md` / `faq.md`（保固、退換貨、運送
付款、常見問題，用 `policy_parser.py` 依 markdown 標題拆分）。這些檔案只在 pgvector table 是空的
時候（例如第一次接上新資料庫）由 `app/rag/documents_store.py` 的 `seed_if_empty()` 自動灌入一次，
之後要新增/刪除/更新內容改走 `/api/admin/documents` 系列 API，不用再手動改檔案或清資料重建索引。

### pgvector（Supabase）

`llamaindex` 引擎需要一個有裝 pgvector extension 的 PostgreSQL。本機開發與 Cloud Run 正式
環境統一指向同一個 Supabase 專案的 **Transaction pooler**（Cloud Run 這種無伺服器環境的
建議用法），不再各自起一個 pgvector：

```
RAG_PG_HOST=aws-0-ap-northeast-2.pooler.supabase.com
RAG_PG_PORT=6543
RAG_PG_DATABASE=postgres
RAG_PG_USER=postgres.<你的 Supabase 專案 ref>
RAG_PG_PASSWORD=<專案建立時設定的資料庫密碼，不要外流／提交進版控>
RAG_PG_TABLE=kb_chunks
```

Supabase 專案預設就有 `vector` extension 可用；`PGVectorStore.from_params()` 預設
`perform_setup=True`，第一次寫入時會自動建立資料表（實體資料表名稱是
`data_<RAG_PG_TABLE>`，例如 `data_kb_chunks`，不是 `RAG_PG_TABLE` 本身），不用手動建 schema。

也可以改指向本機自己起的 PostgreSQL（例如 `docker run -d -e POSTGRES_PASSWORD=postgres
-p 5432:5432 pgvector/pgvector:pg16`），只要裝了 `vector` extension、把 `RAG_PG_*` 指過去
即可，不需要改程式碼。

### RAG 重排序（reranker，選用）

向量檢索先撈一批候選，再用 **Qwen3-Reranker-0.6B**（ONNX INT8）逐一判斷「這段有沒有回答問題」，
重排後只留前 k 名給 LLM。實作在 `app/rag/reranker.py`，用 `onnxruntime` 在同一個 Python 行程內執行
（跟 `app/rag/onnx_embedding.py` 同樣做法），不需要編譯任何東西、沒有子行程。

**模型**：Hugging Face `n24q02m/Qwen3-Reranker-0.6B-ONNX` 的 `onnx/model_yesno_quantized.onnx`
（約 600 MB）加 `tokenizer.json`，第一次啟用時由 `huggingface_hub` 自動下載到 Hugging Face 快取。
- 授權 Apache-2.0，可商用。但這是**個人維護的社群轉檔**，不是 Qwen 官方發布，上線前請自行評估。
- **一定要用 YesNo 版**：完整版會輸出整個詞表，推論要吃約 12 GB 記憶體；YesNo 版只輸出
  `[no, yes]` 兩個 logit，約 600 MB。輸出索引 0 是 no、索引 1 是 yes（已用真實模型驗證）。
- 每份候選各跑一次（batch=1），所以延遲隨候選數線性增加。

**兩層開關，正式環境不會啟用**

1. **伺服器能力**（`reranker.is_supported()`）：必須同時滿足 `RERANK_ENABLED=true`、**不在 Cloud Run
   上**（Cloud Run 一定會設 `K_SERVICE`，即使誤設 `RERANK_ENABLED=true` 也一律停用）、且
   `onnxruntime`／`tokenizers` 已安裝。不支援時連模型都不會下載，模型也不會進 Docker 映像檔
   （`.dockerignore` 排除了 `*.onnx`、`*.gguf`）。
2. **每家公司的偏好**：後台「Chatbot 設定」頁的「重排序」開關（`chatbots.rerank_enabled`，預設關閉）。

為什麼不能只靠頁面不讓勾：**本機與正式環境共用同一個資料庫**，在本機勾了 rerank 會存進資料庫，正式
環境也讀得到。所以兩層都成立才會生效；資料庫裡是「開」但伺服器不支援時，檢索**靜默退回一般向量檢索
top-k**，不報錯、行為與沒開一樣。伺服器不支援時，後台開關會停用並顯示說明，直接呼叫 API 想開啟也會被
`400` 拒絕（關閉任何環境都允許）。

**檢索片段數 k**：每次送給 LLM 的片段數，系統預設 **5**（`RAG_DEFAULT_TOP_K`），每家公司可在後台
「Chatbot 設定」頁調整（`chatbots.rag_top_k`，1～10），有沒有開 rerank 都適用。開啟 rerank 時，向量
檢索先撈 `RERANK_CANDIDATES`（預設 20）筆候選，重排後只留 k 筆。

**設定（`.env`，都是伺服器層級）**

| 變數 | 預設 | 說明 |
|---|---|---|
| `RERANK_ENABLED` | `false` | 總開關；正式環境不要設 |
| `RERANK_CANDIDATES` | `20` | 開啟 rerank 時向量檢索撈幾筆候選（上限 100） |
| `RAG_DEFAULT_TOP_K` | `5` | k 的系統預設值 |
| `RERANK_INSTRUCTION` | Qwen 官方預設說明 | 給 reranker 的任務說明，見下方注意事項 |
| `RERANK_TIMEOUT_SECONDS` | `15` | 單次 rerank 的總時間預算，超過就退回純向量排序 |
| `RERANK_MAX_DOC_TOKENS` | `512` | 每份候選最多保留的 token 數 |
| `RERANK_MAX_CONCURRENCY` | `1` | 同時進行的 rerank 數；每次都會吃滿 CPU |
| `RERANK_ONNX_THREADS` | `0` | onnxruntime 執行緒數，0＝自動；實測調整沒有明顯幫助 |

**行為與限制**
- 任何失敗（模型載入失敗、推論出錯、超過時間預算）都會印 `[rerank Error]` 並退回原本向量檢索的
  排序，聊天不會中斷；模型載入失敗只會印一次，修正設定後需重啟服務。
- 回傳給前端的 `sources[].distance` 仍是向量距離；reranker 分數（P(yes)，0～1）只放在內部的
  `rerank_score`，不進 API 回應。
- 改動了 `chatbots` 表：新增可為 NULL 的 `rag_top_k`（INTEGER）與 `rerank_enabled`（BOOLEAN）兩欄，
  由 `accounts_store._ensure_schema()` 啟動時以 `ADD COLUMN IF NOT EXISTS` 補上；NULL 代表用系統
  預設（k=5、rerank 關閉），既有公司不需回填，舊版程式不受影響。
- `RAG_NO_INFO_THRESHOLD`（provider=local 的「查無資料」門檻）是用向量距離校準的，改成取回傳
  chunk 中最小的向量距離判斷；開啟 rerank 後這個門檻沒有重新校準過。
- **延遲（Apple Silicon CPU，`app/data` 的產品 chunk 平均約 260 字）**：每筆約 0.25 秒，與執行緒數
  無關。50 筆約 12 秒、20 筆約 5 秒、10 筆約 2.4 秒；一般向量檢索約 0.24 秒。所以預設候選數是 20，
  想多撈一些召回率可以調高，但每多 10 筆約多 2.5 秒。
- **任務說明會大幅影響排序**：實測同一批資料，自己改寫成客服情境的說明，「最安靜的滑鼠」把靜音滑鼠
  排到第 5 名、「有賣鍵盤嗎」把螢幕排在鍵盤前面；換回官方預設說明就正常。所以預設用官方那句，要客製
  請先用真實問題比較。
- **排序品質尚未量化評估**：只用少數幾個問題人工看過。沒有評測集證明比純向量檢索好。
- 正式環境（Cloud Run）不啟用，見上方「兩層開關」。

## 知識庫文件管理

下列 API 依賴 llamaindex 引擎的 pgvector 索引（唯一支援的引擎）。
新增/更新是上傳檔案（`multipart/form-data`），不是 JSON body；**支援 `.md`（需 UTF-8）、`.pdf`、`.docx`**，
其他副檔名、非 UTF-8 的 `.md`、或 PDF/Word 解析失敗一律回 400（PDF/Word 沒有 Markdown 標題結構，
改用 LlamaIndex SentenceSplitter 依句子邊界、token 數切段並保留 overlap，見 `app/rag/documents_store.py` 的 `parse_plain_text`）：

| Method | Path | 說明 |
|---|---|---|
| `GET` | `/api/admin/documents` | 列出所有文件（`doc_id`/`category`/`chunk_count`/`uploaded_at`/`file_size_bytes`） |
| `POST` | `/api/admin/documents` | 上傳新文件（multipart：`file` + `category` 欄位），`doc_id` 直接沿用檔名，已存在回 409 |
| `PUT` | `/api/admin/documents/{doc_id}` | 上傳新版檔案覆蓋內容（multipart：`file` 欄位，分類沿用既有值），查無文件回 404 |
| `DELETE` | `/api/admin/documents/{doc_id}` | 刪除文件（該 `doc_id` 底下所有 chunk），查無文件回 404 |

「更新」會先比對 SHA256（`content_hash`）：內容跟既有版本一樣就跳過刪除+重新 embed，回應
`content_changed: false`；有變才刪除該文件舊 chunk、依 `category` 對應的 parser 重新解析插入
新 chunk（`content_changed: true`）。不另外保存文件原文，pgvector 的 chunk 表（文字 + 向量 +
metadata，含 `content_hash`/`uploaded_at`/`file_size_bytes`）就是唯一資料來源。

新增或更新時若偵測到**其他** `doc_id` 存了完全一樣的內容（`content_hash` 相同），回應會帶
`duplicate_of: "<那個 doc_id>"` 提示管理者，但不會擋下這次上傳/更新。

## 注意事項

- 第一次啟動會需要下載 Embedding 模型與本地 LLM 模型，依網路速度可能需要數分鐘到數十分鐘
- 向量資料存在 pgvector（PostgreSQL），服務重啟不需要重新 embed
- `/api/admin/summary`、`/api/admin/documents` 系列目前都沒有任何身分驗證，正式上線前必須加上
  管理者登入/權限檢查

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

// response（@mcp 對話，一律是文字；例如 message 為 "@mcp 幫我查訂單 A12345"）
{ "type": "text", "text": "您的訂單 A12345 已出貨……" }
```

### `GET /api/providers`

回傳可選的 LLM 清單與是否已設定 key，供前端畫下拉選單用。

### `GET /api/admin/summary?chatbot_id=<id>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

回傳指定 UTC 週區間使用者提問的主題摘要。歷史週的 `start_date` 必須為週一、`end_date` 必須為週日；本週的 `end_date` 必須是今天，查詢範圍最多七日。
