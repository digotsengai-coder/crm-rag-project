"""
RAG 引擎切換：依 settings.RAG_ENGINE（"custom" | "llamaindex"）決定用哪一套檢索實作。

兩套引擎（custom_engine.py / llamaindex_engine.py）都提供同一種介面：
    retrieve(query: str, top_k: int) -> [{"text","source","product_name","category","distance"}]
agent.py 只依賴這個介面，不需要知道背後是哪一套，因此可以直接切換 .env 的 RAG_ENGINE 改用另一套，
不用改任何呼叫端程式碼。
"""
from app.config import settings

_retriever = None


def get_retriever():
    global _retriever
    if _retriever is not None:
        return _retriever

    if settings.RAG_ENGINE == "llamaindex":
        from app.rag.llamaindex_engine import LlamaIndexRetriever
        _retriever = LlamaIndexRetriever()
    elif settings.RAG_ENGINE == "custom":
        from app.rag.custom_engine import CustomRetriever
        _retriever = CustomRetriever()
    else:
        raise ValueError(f"未知的 RAG_ENGINE 設定：{settings.RAG_ENGINE}（可用值：custom, llamaindex）")

    return _retriever
