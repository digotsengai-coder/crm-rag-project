"""
向量資料庫（Chroma）：對應提案流程「查詢 RAG 資料庫」。

使用 chromadb.PersistentClient 將索引存到 settings.CHROMA_PERSIST_DIR，
服務重啟後會直接讀取既有索引，不需要重新 embed；
只有在該目錄底下沒有資料（例如第一次啟動）時才會建立索引。
若 documents.py 的知識庫內容有更動，需要手動刪除 CHROMA_PERSIST_DIR 目錄以重建索引。
"""
import chromadb
from app.config import settings
from app.documents import load_source_text, SOURCE_NAME
from app.rag.product_parser import parse_products
from app.rag.embedding import embed_passages

_collection = None


def _get_client():
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)


def build_index():
    global _collection
    client = _get_client()
    collection = client.get_or_create_collection(name="product_kb")

    chunks = parse_products(load_source_text(), source=SOURCE_NAME)
    all_texts = [c["text"] for c in chunks]
    all_metadatas = [
        {
            "source": c["source"],
            "product_name": c["product_name"],
            "category": c["category"],
            "product_id": c["product_id"],
        }
        for c in chunks
    ]
    all_ids = [f"{c['product_id'] or c['product_name']}-{i}" for i, c in enumerate(chunks)]

    embeddings = embed_passages(all_texts)
    collection.add(ids=all_ids, embeddings=embeddings, documents=all_texts, metadatas=all_metadatas)

    _collection = collection
    return collection


def get_collection():
    global _collection
    if _collection is not None:
        return _collection

    client = _get_client()
    collection = client.get_or_create_collection(name="product_kb")
    if collection.count() > 0:
        _collection = collection
        return _collection

    return build_index()
