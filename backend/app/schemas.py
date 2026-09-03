"""FastAPI 請求/回應格式。前端依 type 欄位決定要 render 哪一種訊息元件。"""
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    # 上限 500 字：避免超長輸入把 LLM context 塞爆或拖慢生成速度
    message: str = Field(min_length=1, max_length=500)


class SourceRef(BaseModel):
    text: str
    source: str
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
