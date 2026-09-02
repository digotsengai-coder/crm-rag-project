"""
FastAPI 入口。

單一對話窗設計：前端統一打 /api/chat，後端依訊息內容自動判斷是
「訂單查詢」（#2，比對訂單編號格式）還是「產品問題」（#1，交給 ProductQueryAgent 做 RAG），
對應提案「單一對話框、後端自動判斷」的架構。
"""
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import ChatRequest, ChatResponse
from app.agent import get_agent
from app.orders import get_order

app = FastAPI(title="智慧CRM系統 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 訂單編號格式範例：A12345（1個英文字母 + 5位數字），依實際系統規則調整
ORDER_CODE_PATTERN = re.compile(r"[A-Za-z]\d{5}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/warmup")
def warmup():
    """手動觸發載入 Embedding / LLM 模型，避免第一次聊天時使用者要空等模型下載。"""
    get_agent()
    return {"status": "models loaded"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    text = req.message.strip()
    if not text:
        return ChatResponse(type="text", text="請輸入您的問題。")

    match = ORDER_CODE_PATTERN.search(text.upper())
    if match or "訂單" in text:
        code = match.group(0) if match else "A12345"
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
    answer, retrieved = agent.generate_answer(text)
    top_source = retrieved[0]["source"] if retrieved else None
    return ChatResponse(type="product", text=answer, source=top_source, sources=retrieved)
