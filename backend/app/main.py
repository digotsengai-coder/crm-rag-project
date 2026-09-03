"""
FastAPI 入口。

單一對話窗設計：前端統一打 /api/chat，後端依訊息內容自動判斷是
「訂單查詢」（#2，比對訂單編號格式）還是「產品問題」（#1，交給 ProductQueryAgent 做 RAG），
對應提案「單一對話框、後端自動判斷」的架構。
"""
import re
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import ChatRequest, ChatResponse, DailySummaryResponse, ProviderInfo
from app.agent import get_agent
from app.orders import get_order, init_db as init_orders_db
from app.chat_log import init_db as init_chat_log_db, log_chat
from app.summary import summarize_day
from app.providers import is_configured

PROVIDER_LABELS = {
    "local": "本地 1.5B/7B（免費，速度較慢）",
    "anthropic": "Claude",
    "openai": "GPT",
    "google": "Gemini",
    "xai": "Grok",
}

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時就預載 Embedding / LLM 模型（已快取在本機，只是載入記憶體，不會重新下載），
    # 避免第一位使用者送出訊息時要空等模型載入。
    init_chat_log_db()
    init_orders_db()
    get_agent()
    yield


app = FastAPI(title="智慧CRM系統 API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 訂單編號格式範例：A12345（1個英文字母 + 5位數字），依實際系統規則調整
ORDER_CODE_PATTERN = re.compile(r"[A-Za-z]\d{5}")

# 簡易 rate limit：同一 IP 每 60 秒最多 RATE_LIMIT_MAX_REQUESTS 次 /api/chat 請求。
# 記憶體版實作，僅適合單一服務程序；多台伺服器水平擴充時需改用 Redis 等共用儲存。
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 20
_request_log: dict[str, deque] = defaultdict(deque)


def _check_rate_limit(client_ip: str):
    now = time.time()
    timestamps = _request_log[client_ip]
    while timestamps and now - timestamps[0] > RATE_LIMIT_WINDOW_SECONDS:
        timestamps.popleft()
    if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="請求過於頻繁，請稍後再試。")
    timestamps.append(now)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/warmup")
def warmup():
    """手動觸發載入 Embedding / LLM 模型，避免第一次聊天時使用者要空等模型下載。"""
    get_agent()
    return {"status": "models loaded"}


@app.get("/api/providers", response_model=list[ProviderInfo])
def list_providers():
    """前端聊天視窗用來畫「選擇回答模型」下拉選單，含每個 provider 有沒有設定 key。"""
    return [
        ProviderInfo(id=pid, label=label, configured=is_configured(pid))
        for pid, label in PROVIDER_LABELS.items()
    ]


@app.get("/api/admin/summary", response_model=DailySummaryResponse)
def admin_summary(date: str | None = None):
    """
    管理者查看指定日期（預設今天，UTC）使用者提問的主題摘要。

    注意：目前沒有任何身分驗證，正式上線前必須加上管理者登入/權限檢查，
    否則任何人都能呼叫這支 API 看到顧客提問內容。
    """
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    elif not DATE_PATTERN.match(date):
        raise HTTPException(status_code=400, detail="date 格式須為 YYYY-MM-DD")

    result = summarize_day(date)
    return DailySummaryResponse(**result)


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    text = req.message.strip()
    history = [{"role": h.role, "content": h.content} for h in req.history]
    history = history[-(settings.MAX_HISTORY_TURNS * 2):]
    response = _handle_chat(text, history, req.provider)

    try:
        log_text = response.text if response.text is not None else f"[訂單 {response.code}]"
        log_chat(message=text, response_type=response.type, response_text=log_text, client_ip=client_ip)
    except Exception:
        # 對話紀錄失敗不該讓使用者的聊天請求跟著失敗
        pass

    return response


def _handle_chat(text: str, history: list, provider: str) -> ChatResponse:
    if not text:
        return ChatResponse(type="text", text="請輸入您的問題。")

    match = ORDER_CODE_PATTERN.search(text.upper())
    if match or "訂單" in text:
        if match is None:
            return ChatResponse(
                type="text",
                text="請提供訂單編號（例如 A12345）以便查詢，格式為 1 個英文字母加 5 位數字。",
            )
        code = match.group(0)
        order = get_order(code)
        if order is None:
            return ChatResponse(
                type="text",
                text=f"查無訂單編號 {code}，請確認編號是否正確，或聯繫真人客服（0800-123-456）。",
            )
        return ChatResponse(
            type="order",
            code=code,
            status=order["status"],
            eta=order["eta"],
            items=order["items"],
        )

    agent = get_agent()
    answer, retrieved = agent.generate_answer(text, history=history, provider=provider)
    top_source = retrieved[0]["topic"] if retrieved else None
    return ChatResponse(type="product", text=answer, source=top_source, sources=retrieved)
