"""
「自訂」RAG 引擎：原本就在這個專案裡的做法（product_parser.py 手寫語意拆分 + Chroma + e5 embedding）。
包成統一介面 retrieve(query, top_k) -> [{"text","source","product_name","category","distance"}]，
好讓 app/rag/engine.py 可以跟 llamaindex_engine.py 互換。
"""
from app.rag.vectorstore import get_collection
from app.rag.embedding import embed_query


class CustomRetriever:
    name = "custom"

    def __init__(self):
        self.collection = get_collection()

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        query_embedding = embed_query(query)
        results = self.collection.query(query_embeddings=[query_embedding], n_results=top_k)
        retrieved = []
        for doc, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        ):
            retrieved.append({
                "text": doc,
                "source": meta["source"],
                "product_name": meta.get("product_name", ""),
                "category": meta.get("category", ""),
                "distance": dist,
            })
        return retrieved
