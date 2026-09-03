"""
「LlamaIndex」RAG 引擎：用 LlamaIndex 的 VectorStoreIndex 取代自訂的 Chroma + 手寫檢索邏輯，
跟 custom_engine.py 提供同一種介面 retrieve(query, top_k)，方便用 RAG_ENGINE 設定切換。

語意拆分（每個產品的介紹/規格/彩蛋各自一個片段）仍然沿用 product_parser.py 的邏輯，
因為那是這份文件格式特有的知識，跟「用哪套框架做向量索引/檢索」是兩件事；
這裡示範的是 LlamaIndex 版本的索引建立、持久化、查詢流程，而不是重新發明語意拆分規則。

索引持久化在 settings.LLAMAINDEX_PERSIST_DIR；若知識庫內容有更動，需要手動刪除該目錄以重建索引，
跟 custom 引擎的 CHROMA_PERSIST_DIR 是同樣的機制、只是分開存放，兩套引擎的索引檔互不影響。
"""
import os

from llama_index.core import Settings as LlamaSettings
from llama_index.core import StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.schema import TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.config import settings
from app.documents import load_source_text, SOURCE_NAME
from app.rag.product_parser import parse_products


def _get_embed_model():
    # e5 系列模型需要 "query: " / "passage: " 前綴才能發揮非對稱檢索的效果，
    # HuggingFaceEmbedding 的 query_instruction/text_instruction 剛好對應這兩個前綴。
    return HuggingFaceEmbedding(
        model_name=settings.EMBEDDING_MODEL_NAME,
        query_instruction="query: ",
        text_instruction="passage: ",
    )


def _build_nodes() -> list[TextNode]:
    chunks = parse_products(load_source_text(), source=SOURCE_NAME)
    return [
        TextNode(
            text=c["text"],
            id_=f"{c['product_id'] or c['product_name']}-{i}",
            metadata={
                "source": c["source"],
                "product_name": c["product_name"],
                "category": c["category"],
                "product_id": c["product_id"],
            },
        )
        for i, c in enumerate(chunks)
    ]


class LlamaIndexRetriever:
    name = "llamaindex"

    def __init__(self):
        LlamaSettings.embed_model = _get_embed_model()
        LlamaSettings.llm = None  # 這裡只用 LlamaIndex 做檢索，生成交給 app/providers.py 統一處理

        persist_dir = settings.LLAMAINDEX_PERSIST_DIR
        if os.path.isdir(persist_dir) and os.listdir(persist_dir):
            storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
            self.index = load_index_from_storage(storage_context)
        else:
            self.index = VectorStoreIndex(_build_nodes())
            self.index.storage_context.persist(persist_dir=persist_dir)

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        retriever = self.index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query)
        retrieved = []
        for n in nodes:
            meta = n.node.metadata
            # LlamaIndex 的 score 是「相似度」（越高越相關），custom 引擎的 distance 是「距離」
            # （越低越相關）。統一轉成 distance，讓 agent.py 的 NO_INFO_DISTANCE_THRESHOLD
            # 判斷邏輯兩套引擎共用；但兩套引擎的分數尺度本來就不同，門檻值不能直接共用同一個數字
            # （見 app/config.py 的 RAG_NO_INFO_THRESHOLDS）。
            score = n.score if n.score is not None else 0.0
            retrieved.append({
                "text": n.node.get_content(),
                "source": meta.get("source", ""),
                "product_name": meta.get("product_name", ""),
                "category": meta.get("category", ""),
                "distance": 1 - score,
            })
        return retrieved
