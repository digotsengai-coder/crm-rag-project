"""
FastAPI 入口。

單一對話窗設計：前端統一打 /api/chat，後端依訊息內容自動判斷是
「訂單查詢」（#2，比對訂單編號格式）還是「產品問題」（#1，交給 ProductQueryAgent 做 RAG），
對應提案「單一對話框、後端自動判斷」的架構。
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import asyncio
import re
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from typing import Callable, Literal

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from app import accounts_store, auth
from app.accounts_store import DEFAULT_MCP_TRIGGER_NAME
from app.config import settings
from app.schemas import (
    AccountCreateRequest,
    AccountInfo,
    AccountListResponse,
    AuditLogEntry,
    AuditLogListResponse,
    ChatRequest,
    ChatResponse,
    ChatbotCreateRequest,
    ChatbotInfo,
    ChatbotListResponse,
    ChatbotUpdateRequest,
    McpTokenResponse,
    PeriodSummaryResponse,
    DocumentInfo,
    DocumentListResponse,
    GoogleLoginRequest,
    LoginResponse,
    MeResponse,
    PrecheckRequest,
    PrecheckResponse,
    PrecheckResultItem,
    ProviderInfo,
    WidgetConfig,
    WidgetTheme,
)
from app.agent import get_agent
from app.chat_log import init_db as init_chat_log_db, log_chat, log_tool_calls
from app.mcp_chat import answer_with_mcp, parse_mcp_command
from app.rag import reranker
from app.summary import summarize_period
from app.providers import is_configured
from app.line_webhook import create_line_router
from app.meta_webhook import create_meta_router

PROVIDER_LABELS = {
    "local": "本地 Qwen3.5-2B（免費，僅限 Apple Silicon 開發機）",
    "anthropic": "Claude",
    "openai": "GPT",
    "google": "Gemini",
    "xai": "Grok",
}

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_CLIENT_ID_LENGTH = 128


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時預載 DB；避免在啟動階段載入重型模型導致 Cloud Run 健康檢查逾時
    if settings.DEV_LOGIN_ENABLED:
        print(f"[WARNING] DEV_LOGIN_ENABLED=true：/api/auth/dev-login 已開啟（僅限本機請求），帳號 {settings.DEV_LOGIN_EMAIL}")
    try:
        init_chat_log_db()
    except Exception as e:
        print(f"[Warning] Backend startup db init failed: {e}")
    try:
        # 多租戶帳號表（chatbots/accounts/chatbot_accounts/sessions/audit_log）冪等建立，
        # 順便跑 bootstrap_initial_platform_admins()（見 accounts_store._ensure_schema()）。
        accounts_store._ensure_schema()
    except Exception as e:
        print(f"[Warning] Backend startup accounts_store schema init failed: {e}")
    yield



app = FastAPI(title="智慧CRM系統 API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 簡易 rate limit：同一 IP 每 60 秒最多 RATE_LIMIT_MAX_REQUESTS 次 /api/chat 請求。
# 記憶體版實作，僅適合單一服務程序；多台伺服器水平擴充時需改用 Redis 等共用儲存。
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 20
_request_log: dict[str, deque] = defaultdict(deque)

# chatbot_id（X-Client-ID）額外的限流：chatbot_id 是公開識別碼，會出現在客戶網站的
# widget 原始碼裡，不是密鑰，任何人都拿得到；只靠上面的 per-IP 限流擋不住「換 IP／用多台
# 機器打同一個 chatbot_id」的濫用，所以另外對 chatbot_id 本身也做一組更寬鬆的總量限制
# （一家商家的真實流量本來就會來自很多不同顧客的 IP，門檻要比單一 IP 高很多）。
CHATBOT_RATE_LIMIT_WINDOW_SECONDS = 60
CHATBOT_RATE_LIMIT_MAX_REQUESTS = 120
_chatbot_request_log: dict[str, deque] = defaultdict(deque)


def _check_rate_limit(client_ip: str):
    now = time.time()
    timestamps = _request_log[client_ip]
    while timestamps and now - timestamps[0] > RATE_LIMIT_WINDOW_SECONDS:
        timestamps.popleft()
    if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="請求過於頻繁，請稍後再試。")
    timestamps.append(now)


def _check_chatbot_rate_limit(chatbot_id: str):
    now = time.time()
    timestamps = _chatbot_request_log[chatbot_id]
    while timestamps and now - timestamps[0] > CHATBOT_RATE_LIMIT_WINDOW_SECONDS:
        timestamps.popleft()
    if len(timestamps) >= CHATBOT_RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="這家商家的聊天機器人請求量過大，請稍後再試。")
    timestamps.append(now)


def _require_client_id(
    x_client_id: str | None = Header(default=None, alias="X-Client-ID"),
) -> str:
    """先固定企業客戶識別介面；唯一性與啟停狀態由未來客戶管理服務驗證。"""
    client_id = x_client_id.strip() if x_client_id else ""
    if not client_id or len(client_id) > MAX_CLIENT_ID_LENGTH:
        raise HTTPException(status_code=422, detail="X-Client-ID 必填，且長度不得超過 128 個字元。")
    return client_id


@app.get("/health")
def health():
    return {"status": "ok"}


# ---- 多租戶帳號：Google 登入 / session / 目前登入者資訊（Phase 1，見 app/auth.py） ----


@app.post("/api/auth/google", response_model=LoginResponse)
def login_with_google(req: GoogleLoginRequest):
    """
    驗證前端拿到的 Google ID token，查帳號表；帳號不存在時自動建立一個 tenant_primary 帳號
    （商家自助註冊，不用平台方手動加入），但不會自動幫他建立任何企業服務（chatbot），
    商家登入後要自己在後台新增第一個企業服務。驗證成功建立 session，回傳明文 token
    （僅此一次，之後的請求都帶 Authorization: Bearer <token>）。
    """
    try:
        email = auth.verify_google_id_token(req.id_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    account = accounts_store.get_account_by_email(email)
    if account is None:
        try:
            account = accounts_store.create_account(email, "tenant_primary", created_by=None)
        except IntegrityError:
            # 同一個新 email 在極短時間內併發登入兩次，兩者都查到 None 才會撞到這裡；
            # email 欄位有 UNIQUE 限制，其中一次 insert 會失敗，改查已經插入成功的那筆即可。
            account = accounts_store.get_account_by_email(email)
        accounts_store.record_audit(
            account["id"], action="self_register", target_type="account", target_id=account["id"],
            detail={"email": email},
        )
    token = accounts_store.create_session(account["id"])
    return LoginResponse(token=token, account=AccountInfo(**account))


# 這些網域是 RFC 2606／6761 保留的，不可能是真的 Google 帳號，所以自動建立管理員帳號是安全的
_DEV_LOGIN_RESERVED_SUFFIXES = (".invalid", ".local", ".localhost", ".test")


def _dev_login_allowed(request: Request) -> bool:
    if not settings.DEV_LOGIN_ENABLED:
        return False
    if os.getenv("K_SERVICE"):  # Cloud Run 一定會設這個變數：正式環境永遠停用，就算有人誤設 DEV_LOGIN_ENABLED
        return False
    return request.client is not None and request.client.host in ("127.0.0.1", "::1")


@app.post("/api/auth/dev-login", response_model=LoginResponse)
def dev_login(request: Request):
    """
    開發用一鍵登入：不經過 Google，直接以 settings.DEV_LOGIN_EMAIL 登入（見 config.py 的警告）。
    沒開啟、不是本機請求、或在 Cloud Run 上時一律回 404（不宣告這個端點存在）。
    這個端點不會修改任何既有帳號的角色；帳號不存在時只會為保留網域的 email 建立 platform_primary。
    """
    if not _dev_login_allowed(request):
        raise HTTPException(status_code=404, detail="Not Found")

    email = settings.DEV_LOGIN_EMAIL
    account = accounts_store.get_account_by_email(email)
    if account is None:
        if not email.lower().endswith(_DEV_LOGIN_RESERVED_SUFFIXES):
            raise HTTPException(
                status_code=409,
                detail=f"帳號 {email} 不存在，且它不是保留網域的位址，開發登入不會替真實 email 建立管理員帳號。",
            )
        account = accounts_store.create_account(email, "platform_primary", created_by=None)
    accounts_store.record_audit(
        account["id"], action="dev_login", target_type="account", target_id=account["id"], detail={"email": email},
    )
    token = accounts_store.create_session(account["id"])
    return LoginResponse(token=token, account=AccountInfo(**account))


@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    """撤銷目前 session（刪掉對應的 sessions row）。沒帶 token 或格式錯誤視同已登出，不報錯。"""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):].strip()
        if token:
            accounts_store.revoke_session(token)
    return {"status": "logged_out"}


@app.get("/api/auth/me", response_model=MeResponse)
def get_me(account: dict = Depends(auth.require_session)):
    """回傳目前登入帳號資訊，以及這個帳號看得到的公司清單（platform 角色回全部）。"""
    chatbots = accounts_store.list_chatbots_visible_to(account)
    return MeResponse(
        account=AccountInfo(**account),
        chatbots=[ChatbotInfo(**c) for c in chatbots],
    )


@app.post("/api/warmup")
def warmup():
    """手動觸發載入 Embedding / LLM 模型，避免第一次聊天時使用者要空等模型下載。"""
    get_agent()
    return {"status": "models loaded"}


@app.get("/api/providers", response_model=list[ProviderInfo])
def list_providers(_client_id: str = Depends(_require_client_id)):
    """前端聊天視窗用來畫「選擇回答模型」下拉選單，含每個 provider 有沒有設定 key。"""
    return [
        ProviderInfo(id=pid, label=label, configured=is_configured(pid))
        for pid, label in PROVIDER_LABELS.items()
    ]


DEFAULT_WELCOME_MESSAGE = "您好，我是線上客服，可以問我任何產品的規格、特色，或是退換貨政策喔。"
DEFAULT_QUICK_REPLIES = ["無線滑鼠支援多少 DPI？", "退貨要幾天內申請？"]


@app.get("/api/widget/config", response_model=WidgetConfig)
def widget_config(_client_id: str = Depends(_require_client_id)):
    """
    開頭語（welcome_message）、開場快速提問（quick_replies）依 _client_id（就是
    chatbot_id，見 _lookup_chatbot）讀取公司自訂的值；查無公司或公司沒填就退回
    DEFAULT_WELCOME_MESSAGE／DEFAULT_QUICK_REPLIES（原本 chat-widget 端寫死的內容搬過來
    當預設值），不讓 widget 掛掉。其餘品牌樣式 MVP 先共用，之後可以一併搬進公司資訊頁面。
    """
    chatbot = _lookup_chatbot(_client_id)
    welcome_message = (chatbot.get("welcome_message") if chatbot else None) or DEFAULT_WELCOME_MESSAGE
    quick_replies = (chatbot.get("quick_replies") if chatbot else None) or DEFAULT_QUICK_REPLIES
    return WidgetConfig(
        brand_name="線上客服",
        welcome_message=welcome_message,
        logo_url=None,
        theme=WidgetTheme(
            primary_color="#315b7d",
            surface_color="#ffffff",
            text_color="#17212b",
            border_radius=20,
        ),
        quick_replies=quick_replies,
    )


@app.get("/api/admin/summary", response_model=PeriodSummaryResponse)
def admin_summary(
    chatbot_id: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    _account: dict = Depends(auth.require_chatbot_access),
):
    """
    管理者查看指定公司、自選區間（UTC，最多 31 日）使用者提問的主題摘要。

    chatbot_id 必填 + require_chatbot_access：只有 platform 帳號或綁定這家公司的帳號
    才能看到這家公司的顧客提問內容，比照 /api/admin/documents* 的驗證模式。
    """
    if not DATE_PATTERN.match(start_date) or not DATE_PATTERN.match(end_date):
        raise HTTPException(status_code=400, detail="start_date 與 end_date 格式須為 YYYY-MM-DD")

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="start_date 與 end_date 必須是有效日期")

    today = datetime.now(timezone.utc).date()
    if start > end:
        raise HTTPException(status_code=400, detail="start_date 不得晚於 end_date")
    if (end - start).days > 30:
        raise HTTPException(status_code=400, detail="摘要查詢區間最多一個月（31 日）")
    if end > today:
        raise HTTPException(status_code=400, detail="end_date 不得晚於今天")

    try:
        result = summarize_period(start_date, end_date, chatbot_id)
    except Exception as e:
        # 同 /api/chat：未預期的例外要在應用程式層處理掉，回傳正常的錯誤回應，
        # 避免整個請求掛掉變成 Cloud Run 層級的 502/503（不帶 CORS 標頭）。
        print(f"[Summary Error] {e}")
        raise HTTPException(status_code=502, detail="產生摘要時發生錯誤，請稍後再試。")
    return PeriodSummaryResponse(**result)


def _get_llamaindex_index():
    """文檔管理 API 專用：取得 llamaindex 引擎的 pgvector 索引。"""
    from app.rag.engine import get_retriever

    return get_retriever().index


@app.get("/api/admin/documents", response_model=DocumentListResponse)
def list_documents(chatbot_id: str = Query(...), _account: dict = Depends(auth.require_chatbot_access)):
    """
    列出這家公司知識庫目前所有路徑（一份內容掛兩個路徑就是兩列，各自標籤），供管理頁面畫列表。

    chatbot_id 查詢參數 + require_chatbot_access：只有 platform 帳號或綁定這家公司的帳號
    才能查看（見 app/auth.py）。
    """
    from app.rag.documents_store import list_documents as _list_documents

    _get_llamaindex_index()  # 確認 pgvector 連線正常，不通就提早回錯誤
    try:
        docs = _list_documents(chatbot_id)
    except Exception as e:
        print(f"[Documents Error] list failed: {e}")
        raise HTTPException(status_code=502, detail="讀取知識庫文件列表時發生錯誤，請稍後再試。")
    return DocumentListResponse(documents=[DocumentInfo(**d) for d in docs])


def _extract_pdf_text(raw_bytes: bytes) -> str:
    """讀出 PDF 每一頁的文字並用空行接起來；掃描圖片型 PDF 抽不出文字會回錯誤，
    這類檔案需要 OCR 才能處理，目前不支援。"""
    import io

    from pypdf import PdfReader

    try:
        pages = [page.extract_text() or "" for page in PdfReader(io.BytesIO(raw_bytes)).pages]
    except Exception:
        raise HTTPException(status_code=400, detail="無法解析 PDF 檔案內容，請確認檔案未損毀。")
    text = "\n\n".join(p for p in pages if p.strip())
    if not text.strip():
        raise HTTPException(status_code=400, detail="PDF 檔案沒有可擷取的文字內容（掃描圖片型 PDF 暫不支援）。")
    return text


def _extract_docx_text(raw_bytes: bytes) -> str:
    """讀出 Word 文件每個段落的文字並用空行接起來；不保留標題階層，統一交給
    parse_plain_text 用 SentenceSplitter 依句子邊界切段（見 app/rag/documents_store.py 的說明）。"""
    import io

    from docx import Document

    try:
        paragraphs = [p.text for p in Document(io.BytesIO(raw_bytes)).paragraphs]
    except Exception:
        raise HTTPException(status_code=400, detail="無法解析 Word 檔案內容，請確認檔案未損毀。")
    text = "\n\n".join(p for p in paragraphs if p.strip())
    if not text.strip():
        raise HTTPException(status_code=400, detail="Word 檔案沒有可擷取的文字內容。")
    return text


def _read_document_upload(file: UploadFile) -> tuple[bytes, str, Callable[[str, str], list[dict]]]:
    """驗證上傳檔案格式（.md／.pdf／.docx），讀出原始 bytes，並回傳解析成文字後的內容
    與對應的 chunk parser（.md 保留原本的 H1/H2 標題拆分；PDF/Word 沒有 Markdown 結構，
    改用 parse_plain_text 的 SentenceSplitter 依句子邊界、token 數切段並保留 overlap，
    見 app/rag/documents_store.py）。"""
    from app.rag.documents_store import parse_generic_markdown, parse_plain_text

    filename = (file.filename or "").lower()
    raw_bytes = file.file.read()
    if filename.endswith(".md"):
        try:
            return raw_bytes, raw_bytes.decode("utf-8"), parse_generic_markdown
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="檔案編碼須為 UTF-8。")
    if filename.endswith(".pdf"):
        return raw_bytes, _extract_pdf_text(raw_bytes), parse_plain_text
    if filename.endswith(".docx"):
        return raw_bytes, _extract_docx_text(raw_bytes), parse_plain_text
    raise HTTPException(status_code=400, detail="目前只支援 .md、.pdf、.docx 檔案。")


def _check_client_hash(server_hash: str, client_sha256: str):
    """
    硬性檢查：上傳前端算的雜湊要跟伺服器重算的一致，才允許寫入。避免瀏覽器讀檔/傳輸過程
    內容跟預檢（precheck）階段比對的內容不一致（例如使用者在預檢後又動了檔案），
    這個檢查故意設計成擋下請求，不只是回傳給前端自行比對。
    """
    if server_hash != client_sha256:
        raise HTTPException(status_code=400, detail="檔案內容與上傳前計算的雜湊不符，請重新選檔上傳。")


@app.post("/api/admin/documents/precheck", response_model=PrecheckResponse)
def precheck_documents(
    req: PrecheckRequest, chatbot_id: str = Query(...), _account: dict = Depends(auth.require_chatbot_access)
):
    """
    批次上傳前的預檢：對每個 (path, client_sha256, tags) 交叉查「這家公司底下這個路徑目前
    指向什麼」跟「這個雜湊是不是已經存在這家公司別的地方」，讓前端知道每份文件是
    new/unchanged/content_changed/tags_only_changed/linked，不用實際寫入/重新 embed。
    純讀取（不動向量索引），但比照其他 admin 文件端點一併確認 pgvector 連線正常，行為與其餘
    端點保持一致。

    完全不需要 doc_id：身分判斷全部靠公司+路徑查 kb_document_labels、公司+內容雜湊查
    kb_documents，這兩張表的細節見 app/rag/documents_store.py。
    """
    from app.rag.documents_store import find_document_by_hash, get_label, list_paths_by_prefix

    _get_llamaindex_index()
    try:
        results = []
        seen_paths = set()
        for item in req.items:
            seen_paths.add(item.path)
            label = get_label(chatbot_id, item.path)
            if label is not None and label["content_hash"] == item.client_sha256:
                status: Literal[
                    "new", "unchanged", "content_changed", "tags_only_changed", "linked"
                ] = "unchanged" if set(label["tags"]) == set(item.tags) else "tags_only_changed"
            elif find_document_by_hash(chatbot_id, item.client_sha256) is not None:
                status = "linked"
            elif label is not None:
                status = "content_changed"
            else:
                status = "new"
            results.append(PrecheckResultItem(path=item.path, status=status))

        stale_paths: list[str] = []
        if req.scope_prefix:
            stale_paths = [
                p for p in list_paths_by_prefix(chatbot_id, req.scope_prefix) if p not in seen_paths
            ]
    except Exception as e:
        print(f"[Documents Error] precheck failed: {e}")
        raise HTTPException(status_code=502, detail="預檢知識庫文件時發生錯誤，請稍後再試。")
    return PrecheckResponse(items=results, stale_paths=stale_paths)


@app.put("/api/admin/documents/{path:path}", response_model=DocumentInfo)
def upsert_document(
    path: str,
    tags: list[str] = Form(default=[]),
    client_sha256: str = Form(...),
    file: UploadFile | None = File(default=None),
    chatbot_id: str = Query(...),
    account: dict = Depends(auth.require_chatbot_access),
):
    """
    新增/更新內容/改標籤/掛到既有內容（linked）統一走這支端點，不需要呼叫端提供 doc_id。
    後端依「這家公司底下這個路徑目前指向什麼」跟「這個雜湊是不是已經存在這家公司別的地方」
    決定實際動作，見 app/rag/documents_store.py 的 upsert_document()。平台帳號也能直接修改
    商家的 RAG 資料（非唯讀），跟商家帳號走同一條路徑，差別只在權限檢查（require_chatbot_access
    對 platform 角色一律放行）。

    `file` 只有在真的需要新內容（新文件／內容變更）時才要帶；純改標籤或掛到既有內容
    （雜湊已經存在別處）不需要上傳檔案。帶了 file 的情況一律先驗證雜湊，跟 client_sha256
    不符直接回 400（避免預檢後檔案內容又被改動）——雜湊比對的對象固定是原始檔案 bytes，
    不是 PDF/Word 轉檔後的擷取文字（見 _read_document_upload()）。

    支援 .md（保留原本的 H1/H2 標題拆分）、.pdf、.docx（沒有 Markdown 結構，改用 SentenceSplitter
    依句子邊界、token 數切段並保留 overlap，見 app/rag/documents_store.py 的 parse_plain_text）。
    """
    from app.rag.documents_store import (
        hash_content,
        parse_generic_markdown,
        upsert_document as _upsert_document,
    )

    index = _get_llamaindex_index()
    raw_text = None
    parser = parse_generic_markdown
    file_size_bytes = None
    if file is not None:
        raw_bytes, raw_text, parser = _read_document_upload(file)
        _check_client_hash(hash_content(raw_bytes), client_sha256)
        file_size_bytes = len(raw_bytes)
    try:
        result = _upsert_document(
            chatbot_id, path, tags, client_sha256, raw_text, index,
            parser=parser, file_size_bytes=file_size_bytes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[Documents Error] upsert {path} failed: {e}")
        raise HTTPException(status_code=502, detail="新增或更新知識庫文件時發生錯誤，請稍後再試。")
    try:
        accounts_store.record_audit(
            account["id"], action="upsert_document", target_type="kb_document", target_id=path,
            detail={"chatbot_id": chatbot_id, "status": result["status"], "tags": tags},
        )
    except Exception as e:
        # 稽核紀錄失敗不該讓文件已經寫入成功的請求跟著失敗，只印 log。
        print(f"[Audit Error] upsert_document {path} failed to record: {e}")
    return DocumentInfo(
        path=path, tags=tags, chunk_count=result["chunk_count"],
        content_changed=result["content_changed"], content_hash=client_sha256,
    )


@app.delete("/api/admin/documents/{path:path}")
def delete_document(
    path: str, chatbot_id: str = Query(...), account: dict = Depends(auth.require_chatbot_access)
):
    """
    刪除這家公司底下這個路徑的標籤紀錄；該內容如果沒有其他路徑指著了，才真的刪掉向量與內容紀錄
    （見 documents_store.delete_document_by_path()）。
    """
    from app.rag.documents_store import delete_document_by_path

    index = _get_llamaindex_index()
    try:
        deleted = delete_document_by_path(chatbot_id, path, index)
    except Exception as e:
        print(f"[Documents Error] delete {path} failed: {e}")
        raise HTTPException(status_code=502, detail="刪除知識庫文件時發生錯誤，請稍後再試。")
    if not deleted:
        raise HTTPException(status_code=404, detail=f"查無路徑 {path}，請確認路徑是否正確。")
    try:
        accounts_store.record_audit(
            account["id"], action="delete_document", target_type="kb_document", target_id=path,
            detail={"chatbot_id": chatbot_id},
        )
    except Exception as e:
        print(f"[Audit Error] delete_document {path} failed to record: {e}")
    return {"status": "deleted", "path": path}


# ---- 公司（商家服務）管理：/api/admin/chatbots ----


@app.post("/api/admin/chatbots", response_model=ChatbotInfo)
def create_chatbot(req: ChatbotCreateRequest, account: dict = Depends(auth.require_session)):
    """
    任何已登入帳號都能新增企業服務（商家自助開通，不用平台方手動加入），建立後一律自動綁定
    建立者（不分 tenant／platform 角色）：讓一個商家帳號可以自己開多個 chatbot_id；
    管理者帳號建立公司時也綁定，讓「管理者帳號本來就是這家公司的創建者」這件事在公司設定頁
    的協作帳號清單裡看得到、也能正常增減——管理者角色本來就對所有公司有存取權（不靠這個
    綁定），這裡綁定純粹是為了在「這家公司」的視角下如實記錄跟顯示創建者。
    """
    chatbot = accounts_store.create_chatbot(
        req.name, req.mcp_url, req.welcome_message, req.quick_replies, req.mcp_token,
        mcp_trigger_name=req.mcp_trigger_name,
    )
    accounts_store.bind_chatbot(account["id"], chatbot["id"], role="primary")
    accounts_store.record_audit(
        account["id"], action="create_chatbot", target_type="chatbot", target_id=chatbot["id"],
        # 稽核紀錄只記「有沒有設定金鑰」，不記金鑰內容
        detail={"name": req.name, "mcp_token_set": bool(req.mcp_token)},
    )
    return ChatbotInfo(**chatbot)


@app.get("/api/admin/chatbots", response_model=ChatbotListResponse)
def list_chatbots(account: dict = Depends(auth.require_session)):
    """回傳呼叫者可見的公司清單：platform 角色看全部，tenant 角色只看自己綁定的。"""
    chatbots = accounts_store.list_chatbots_visible_to(account)
    return ChatbotListResponse(chatbots=[ChatbotInfo(**c) for c in chatbots])


@app.put("/api/admin/chatbots/{chatbot_id}", response_model=ChatbotInfo)
def update_chatbot(
    chatbot_id: str, req: ChatbotUpdateRequest, account: dict = Depends(auth.require_chatbot_access)
):
    """
    更新公司資訊（name／mcp_url／mcp_trigger_name／welcome_message／quick_replies／rag_top_k／rerank_enabled）：platform 帳號或綁定
    這家公司的商家帳號都能改，對應「公司資訊頁面可設定 MCP URL、聊天機器人開頭語、
    開場快速提問」的需求。
    """
    if req.rerank_enabled and not reranker.is_supported():
        # 這台伺服器（例如 Cloud Run 正式環境）不能 rerank：拒絕開啟，避免資料庫裡留下一個
        # 「已開啟但永遠不會生效」的設定。關閉（false）不受影響，任何環境都能關。
        raise HTTPException(status_code=400, detail="這個環境不支援重排序（rerank），無法開啟。")
    chatbot = accounts_store.update_chatbot(
        chatbot_id, req.name, req.mcp_url, req.welcome_message, req.quick_replies, req.mcp_token,
        rag_top_k=req.rag_top_k, rerank_enabled=req.rerank_enabled,
        mcp_trigger_name=req.mcp_trigger_name,
        line_channel_id=req.line_channel_id,
        line_channel_secret=req.line_channel_secret,
        line_channel_access_token=req.line_channel_access_token,
        facebook_page_id=req.facebook_page_id,
        facebook_app_secret=req.facebook_app_secret,
        facebook_page_access_token=req.facebook_page_access_token,
        facebook_verify_token=req.facebook_verify_token,
        instagram_business_id=req.instagram_business_id,
        instagram_access_token=req.instagram_access_token,
        instagram_app_secret=req.instagram_app_secret,
    )
    if chatbot is None:
        raise HTTPException(status_code=404, detail="查無這家公司。")
    accounts_store.record_audit(
        account["id"], action="update_chatbot", target_type="chatbot", target_id=chatbot_id,
        detail={
            "name": req.name, "mcp_url": req.mcp_url, "welcome_message": req.welcome_message,
            "quick_replies": req.quick_replies,
            "rag_top_k": req.rag_top_k, "rerank_enabled": req.rerank_enabled,
            "mcp_trigger_name": req.mcp_trigger_name,
            # 金鑰內容絕不寫進稽核紀錄，只記這次有沒有動到它（None＝沒改、空字串＝清除）
            "mcp_token_changed": req.mcp_token is not None,
        },
    )
    return ChatbotInfo(**chatbot)


@app.get("/api/admin/chatbots/{chatbot_id}/mcp-token", response_model=McpTokenResponse)
def get_chatbot_mcp_token(chatbot_id: str, account: dict = Depends(auth.require_chatbot_access)):
    """
    讓有權限的帳號（platform 角色或綁定這家公司的商家帳號）查看這家公司的 MCP 金鑰。
    金鑰不放進 ChatbotInfo／列表回應，只有這支端點回傳明文，並且每次查看都寫入稽核紀錄。
    """
    chatbot = accounts_store.get_chatbot(chatbot_id)
    if chatbot is None:
        raise HTTPException(status_code=404, detail="查無這家公司。")
    accounts_store.record_audit(
        account["id"], action="reveal_mcp_token", target_type="chatbot", target_id=chatbot_id,
    )
    return McpTokenResponse(mcp_token=accounts_store.get_chatbot_mcp_token(chatbot_id))


@app.delete("/api/admin/chatbots/{chatbot_id}")
def delete_chatbot(chatbot_id: str, account: dict = Depends(auth.require_chatbot_access)):
    """
    硬刪除公司：platform 角色或綁定這家公司的商家帳號都能刪除（比照 update_chatbot 的權限
    模型）——商家自助建立公司後，理當也能自己刪除，不用另外找平台方。連同該公司的 RAG
    文件記錄與向量 chunk 一起清掉（見 documents_store.purge_chatbot()），chatbot_accounts
    綁定靠 ON DELETE CASCADE 自動清。
    """
    from app.rag.documents_store import purge_chatbot

    index = _get_llamaindex_index()
    deleted = accounts_store.delete_chatbot(chatbot_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="查無這家公司。")
    try:
        purge_chatbot(chatbot_id, index)
    except Exception as e:
        # 公司本身已經刪除成功；RAG 資料清理失敗只印 log，不讓整個刪除請求回錯誤
        # （避免呼叫端誤以為公司沒刪成功而重試，造成後續 accounts_store.delete_chatbot 再次回 404 的困惑）。
        print(f"[Chatbot Delete Error] purge_chatbot {chatbot_id} failed: {e}")
    accounts_store.record_audit(
        account["id"], action="delete_chatbot", target_type="chatbot", target_id=chatbot_id,
    )
    return {"status": "deleted", "chatbot_id": chatbot_id}


# ---- 帳號管理：/api/admin/accounts（主帳號/主開發者新增次帳號/次開發者） ----


def _can_manage_account_for(actor: dict, req: AccountCreateRequest) -> bool:
    """
    新增/移除帳號的權限判斷：
    - 新增 platform_secondary：僅限 platform_primary。
    - 新增/綁定 tenant_*（某 chatbot 的協作帳號）：呼叫者要是這家公司的 primary
      （不是「任何有綁定的帳號」——secondary 看得到協作帳號清單，但不能增減，比照
      「主商家帳號可以增加減少協作商家帳號」這個規則；platform 角色永遠可以）。
    """
    if req.role == "platform_primary":
        return False  # 不開放透過 API 新增第二個 platform_primary，避免權限模型混亂
    if req.role == "platform_secondary":
        return actor["role"] == "platform_primary"
    # tenant_primary / tenant_secondary：req.role 只用來決定這家公司的 chatbot_role
    # （primary／secondary），不是帳號的全域角色，見下面 create_account()。
    if not req.chatbot_id:
        return False
    return accounts_store.is_chatbot_primary(actor, req.chatbot_id)


@app.post("/api/admin/accounts", response_model=AccountInfo)
def create_account(req: AccountCreateRequest, actor: dict = Depends(auth.require_session)):
    """
    req.role 對 tenant_* 只用來決定「這家公司」的身分（tenant_primary → chatbot_accounts.role
    = 'primary'，tenant_secondary → 'secondary'），不會拿來覆寫帳號的全域角色（accounts.role）：
    一個帳號可以是 A 公司的 primary、同時是 B 公司的 secondary，全域角色只在帳號第一次被建立
    （這個 email 在系統裡完全沒出現過）時才需要決定。

    email 已經是系統帳號時（不管全域角色、不管目前綁定哪些公司）：對 tenant_* 請求，直接把
    這個既有帳號綁定/更新成這家公司的協作帳號，不回錯誤——這是刻意的設計，讓同一個人可以
    同時是自己公司的主帳號、又是別人公司的協作帳號。對 platform_secondary 請求維持原本行為
    （管理者帳號一定要是全新 email，不支援「把既有商家帳號升成管理者」這種操作）。
    """
    if not _can_manage_account_for(actor, req):
        raise HTTPException(status_code=403, detail="沒有權限新增這個角色的帳號。")
    existing = accounts_store.get_account_by_email(req.email)
    if req.role in accounts_store.TENANT_ROLES and req.chatbot_id:
        chatbot_role = "primary" if req.role == "tenant_primary" else "secondary"
        if existing is not None:
            accounts_store.bind_chatbot(existing["id"], req.chatbot_id, role=chatbot_role)
            accounts_store.record_audit(
                actor["id"], action="bind_existing_account", target_type="account", target_id=existing["id"],
                detail={"email": req.email, "chatbot_id": req.chatbot_id, "chatbot_role": chatbot_role},
            )
            return AccountInfo(**existing)
        account = accounts_store.create_account(req.email, req.role, actor["id"])
        accounts_store.bind_chatbot(account["id"], req.chatbot_id, role=chatbot_role)
        accounts_store.record_audit(
            actor["id"], action="create_account", target_type="account", target_id=account["id"],
            detail={"email": req.email, "role": req.role, "chatbot_id": req.chatbot_id},
        )
        return AccountInfo(**account)

    # platform_secondary：維持原本「email 必須是全新的」限制
    if existing is not None:
        raise HTTPException(status_code=400, detail="這個 email 已經是系統帳號了。")
    account = accounts_store.create_account(req.email, req.role, actor["id"])
    accounts_store.record_audit(
        actor["id"], action="create_account", target_type="account", target_id=account["id"],
        detail={"email": req.email, "role": req.role, "chatbot_id": req.chatbot_id},
    )
    return AccountInfo(**account)


@app.get("/api/admin/accounts", response_model=AccountListResponse)
def list_accounts(chatbot_id: str | None = Query(default=None), actor: dict = Depends(auth.require_session)):
    """
    帶 chatbot_id：回傳這家公司綁定的商家帳號（公司設定頁「管理帳號」用），呼叫者要對這家
    公司有存取權，比照 update_chatbot／audit-log 的權限模式；不含管理者帳號，天生就不會
    混進其他公司的協作帳號。
    不帶 chatbot_id：回傳所有管理者帳號（platform_primary／platform_secondary，「管理者
    帳號」頁籤用），僅限 platform 角色呼叫，商家帳號沒有理由要看到管理者帳號清單。
    """
    if chatbot_id:
        if not accounts_store.account_has_chatbot_access(actor, chatbot_id):
            raise HTTPException(status_code=403, detail="沒有這家公司的存取權限。")
        accounts = accounts_store.list_accounts_for_chatbot(chatbot_id)
    else:
        if actor["role"] not in accounts_store.PLATFORM_ROLES:
            raise HTTPException(status_code=403, detail="此操作僅限平台維運帳號。")
        accounts = accounts_store.list_platform_accounts()
    return AccountListResponse(accounts=[AccountInfo(**a) for a in accounts])


@app.delete("/api/admin/accounts/{account_id}")
def delete_account(
    account_id: str, chatbot_id: str | None = Query(default=None), actor: dict = Depends(auth.require_session)
):
    """
    帶 chatbot_id：只把這個帳號從**這家公司**移除協作關係（unbind_chatbot），不刪除帳號
    本身——一個帳號可能同時是別家公司的主帳號/協作帳號，整個刪掉會連帶砍掉那些完全無關的
    關係。呼叫者要是這家公司的 primary（或 platform）才能移除，對應「主商家帳號可以增加
    減少協作商家帳號」。移除後該帳號只是存取不到這家公司，session 不受影響（他可能還在管
    別家公司），不是「立刻無法登入」。

    不帶 chatbot_id：刪除整個帳號（目前只有「管理者帳號」頁籤在用，移除 platform_secondary），
    連帶清掉所有 chatbot_accounts 綁定跟 sessions（ON DELETE CASCADE）。
    """
    target = accounts_store.get_account_by_id(account_id)
    if target is None:
        raise HTTPException(status_code=404, detail="查無這個帳號。")

    if chatbot_id:
        if not accounts_store.is_chatbot_primary(actor, chatbot_id):
            raise HTTPException(status_code=403, detail="沒有權限移除這家公司的協作帳號。")
        accounts_store.unbind_chatbot(account_id, chatbot_id)
        accounts_store.record_audit(
            actor["id"], action="unbind_account_from_chatbot", target_type="account", target_id=account_id,
            detail={"email": target["email"], "chatbot_id": chatbot_id},
        )
        return {"status": "unbound", "account_id": account_id, "chatbot_id": chatbot_id}

    if target["role"] == "platform_primary":
        raise HTTPException(status_code=403, detail="不能透過 API 刪除 platform_primary 帳號。")
    if target["role"] == "platform_secondary":
        if actor["role"] != "platform_primary":
            raise HTTPException(status_code=403, detail="沒有權限刪除這個帳號。")
    else:
        # tenant_* 帳號：呼叫者要對這個帳號目前綁定的任一家公司有存取權才能整個刪
        chatbots = accounts_store.list_chatbots_visible_to(target)
        if actor["role"] not in accounts_store.PLATFORM_ROLES and not any(
            accounts_store.account_has_chatbot_access(actor, c["id"]) for c in chatbots
        ):
            raise HTTPException(status_code=403, detail="沒有權限刪除這個帳號。")
    target_chatbots = accounts_store.list_chatbots_visible_to(target) if target["role"] in accounts_store.TENANT_ROLES else []
    accounts_store.delete_account(account_id)
    accounts_store.record_audit(
        actor["id"], action="delete_account", target_type="account", target_id=account_id,
        detail={
            "email": target["email"],
            # 只記第一家，稽核頁面用這個欄位做 chatbot_id 過濾；帳號同時綁多家公司是少數情況，
            # 這裡不為了這個邊角案例把 detail 改成陣列、多寫一套查詢邏輯。
            "chatbot_id": target_chatbots[0]["id"] if target_chatbots else None,
        },
    )
    return {"status": "deleted", "account_id": account_id}


# ---- 稽核紀錄：/api/admin/audit-log（依 chatbot_id 查這家公司相關的異動紀錄） ----


@app.get("/api/admin/audit-log", response_model=AuditLogListResponse)
def get_audit_log(chatbot_id: str = Query(...), _account: dict = Depends(auth.require_chatbot_access)):
    """
    查一家公司的稽核紀錄：權限比照 /api/admin/summary，只有 platform 帳號或綁定這家公司的
    帳號才能看。內容涵蓋公司異動、RAG 文件上傳/刪除、這家公司協作帳號的新增/移除。
    """
    entries = accounts_store.list_audit_log_for_chatbot(chatbot_id)
    return AuditLogListResponse(entries=[AuditLogEntry(**e) for e in entries])


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, _client_id: str = Depends(_require_client_id)):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)
    _check_chatbot_rate_limit(_client_id)

    text = req.message.strip()
    history = [{"role": h.role, "content": h.content} for h in req.history]
    history = history[-(settings.MAX_HISTORY_TURNS * 2):]
    try:
        # X-Client-ID（_client_id）現在就是 chatbots 表的 chatbot_id（見
        # sourcecode/chat-widget/README.md 的 data-client-id 說明）；沒對應到任何公司時
        # 檢索合理地回傳空結果（不是錯誤），不影響其他訂單分流邏輯。
        response = await _handle_chat(text, history, req.provider, chatbot_id=_client_id)
    except Exception as e:
        # 任何未預期的例外（金鑰失效、首次建索引逾時等）都要回傳正常的 200 回應，
        # 讓 FastAPI/CORSMiddleware 有機會處理，避免請求整個掛掉變成 Cloud Run
        # 的 502/503（那種回應不是應用程式產生的，不會帶 CORS 標頭，前端只會看到 CORS 錯誤）。
        print(f"[Chat Error] {e}")
        response = ChatResponse(type="text", text="系統暫時發生錯誤，請稍後再試或聯繫真人客服（0800-123-456）。")

    try:
        log_text = response.text or ""
        log_chat(
            message=text, response_type=response.type, response_text=log_text, client_ip=client_ip,
            chatbot_id=_client_id,
        )
    except Exception:
        # 對話紀錄失敗不該讓使用者的聊天請求跟著失敗
        pass

    return response


def _lookup_chatbot(chatbot_id: str | None) -> dict | None:
    """
    chatbot_id 來自未經驗證的 X-Client-ID header，可能是 None、空字串，或格式不合法的
    UUID；accounts_store.get_chatbot() 底層是 Postgres 查詢，帶入不合法 UUID 會直接拋
    例外，這裡統一包一層防呆，查不到／格式不對都當作「查無公司」，不能讓呼叫端的請求
    跟著炸掉。widget_config() 與 _handle_chat() 的 @mcp 分流都靠這個函式取得公司資料。
    """
    if not chatbot_id:
        return None
    try:
        return accounts_store.get_chatbot(chatbot_id)
    except Exception:
        return None


async def _handle_chat(
    text: str, history: list, provider: str, chatbot_id: str | None = None
) -> ChatResponse:
    if not text:

        return ChatResponse(type="text", text="請輸入您的問題。")


    # 訊息以「@<MCP 機器人名稱>」開頭（沒設定名稱時是 @MCP）：交給該公司 MCP server 的 tools 處理
    # （LLM 自己選 tool、整理成文字），不走 RAG；其他訊息維持原本的 RAG + LLM。見 app/mcp_chat.py。
    # 查不到公司時用預設名稱，讓 @MCP 仍能得到「尚未開啟」的提示，而不是被當成一般問題。
    chatbot = _lookup_chatbot(chatbot_id)
    mcp_question = parse_mcp_command(
        text, chatbot["mcp_trigger_name"] if chatbot else DEFAULT_MCP_TRIGGER_NAME
    )
    if mcp_question is not None:
        result = await answer_with_mcp(mcp_question, history, provider, chatbot)
        try:
            log_tool_calls(chatbot_id, result.tool_calls)
        except Exception as e:
            # 稽核紀錄寫入失敗不該讓使用者的聊天請求跟著失敗
            print(f"[MCP Tool Log Error] {e}")
        return ChatResponse(type="text", text=result.text)

    agent = get_agent()
    # 讀這家公司在後台設定的 k 與 rerank 偏好；查不到公司（沒帶或不合法的 X-Client-ID）就用系統預設。
    # rerank 偏好只是「想開」，伺服器不支援時（例如 Cloud Run）檢索層會靜默退回一般向量檢索。
    # generate_answer 是同步函式（檢索 + 等線上 LLM 回應，動輒數秒），直接呼叫會佔住 event loop，
    # 讓同一實例上其他使用者的請求排隊；丟到執行緒池執行才能真正並行處理多位使用者。
    answer, retrieved = await asyncio.to_thread(
        agent.generate_answer,
        text, history=history, provider=provider, chatbot_id=chatbot_id,
        top_k=chatbot["rag_top_k"] if chatbot else None,
        use_rerank=bool(chatbot and chatbot["rerank_enabled"]),
    )
    if not retrieved:
        # 沒有實際檢索結果（查無資訊、provider 未設定或呼叫失敗）：這是提示/錯誤訊息，不是
        # 根據知識庫生成的產品/政策回答，依 contracts.md 的分類該用 type: text，且不該帶無關的 source。
        return ChatResponse(type="text", text=answer)
    top_source = retrieved[0]["topic"]
    return ChatResponse(type="product", text=answer, source=top_source, sources=retrieved)

# LINE Messaging API
app.include_router(create_line_router(_handle_chat))
# Meta 平台（Facebook 粉專 + Instagram 私訊，共用同一個 webhook 端點）
app.include_router(create_meta_router(_handle_chat))
