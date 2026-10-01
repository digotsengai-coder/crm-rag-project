"""
向量化（Embedding）：對應提案流程「Agent 將 input 向量化」。

使用 intfloat/multilingual-e5-base，e5 系列模型慣例：
- 文件片段（要被檢索的內容）前面加 "passage: "
- 使用者查詢前面加 "query: "
這樣可以讓模型用「非對稱」方式分別學習「段落表示」與「查詢表示」，提升檢索效果。

模型只在第一次呼叫時載入（lazy loading），避免 FastAPI 啟動時卡住太久。
"""
from sentence_transformers import SentenceTransformer
from app.config import settings

_embedder: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _embedder


def embed_passages(texts: list[str]) -> list[list[float]]:
    embedder = get_embedder()
    prefixed = [f"passage: {t}" for t in texts]
    return embedder.encode(prefixed, normalize_embeddings=True).tolist()


def embed_query(text: str) -> list[float]:
    embedder = get_embedder()
    return embedder.encode([f"query: {text}"], normalize_embeddings=True).tolist()[0]
