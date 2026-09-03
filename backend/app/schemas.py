"""FastAPI 請求/回應格式。前端依 type 欄位決定要 render 哪一種訊息元件。"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    # assistant 回答上限比使用者訊息寬鬆：max_new_tokens=512 的生成結果換算中文字數可能超過 500，
    # 這裡限制的是「回傳的歷史紀錄」本身，不是使用者新輸入（那個仍受 ChatRequest.message 500 字限制）。
    content: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    # 上限 500 字：避免超長輸入把 LLM context 塞爆或拖慢生成速度
    message: str = Field(min_length=1, max_length=500)
    # 前端傳回目前對話中「之前幾輪」的訊息，用來讓機器人記得上下文（例如「那電池呢？」）。
    # 只有產品問答（type == "product"）這條路徑會用到；訂單查詢是規則比對，不需要歷史。
    history: List[HistoryTurn] = Field(default_factory=list, max_length=20)
    # 要用哪個 LLM 回答；local 是本地 1.5B/7B 模型，其餘是線上付費 API（見 app/providers.py）
    provider: Literal["local", "anthropic", "openai", "google", "xai"] = "local"


class SourceRef(BaseModel):
    text: str
    source: str
    product_name: str = ""
    distance: float


class ChatResponse(BaseModel):
    type: str  # "product" | "order" | "text"

    # type == "product" | "text"
    text: Optional[str] = None
    source: Optional[str] = None
    sources: Optional[List[SourceRef]] = None

    # type == "order"
    code: Optional[str] = None
    status: Optional[int] = None
    eta: Optional[str] = None
    items: Optional[str] = None


class DailySummaryResponse(BaseModel):
    date: str
    question_count: int
    summary: str


class ProviderInfo(BaseModel):
    id: str
    label: str
    configured: bool
