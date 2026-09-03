"""
向量資料庫（Chroma）：對應提案流程「查詢 RAG 資料庫」。

使用 chromadb.PersistentClient 將索引存到 settings.CHROMA_PERSIST_DIR，
服務重啟後會直接讀取既有索引，不需要重新 embed；
只有在該目錄底下沒有資料（例如第一次啟動）時才會建立索引。
若 documents.py 的知識庫內容有更動，需要手動刪除 CHROMA_PERSIST_DIR 目錄以重建索引。
"""
import chromadb
from app.config import settings
from app.documents import documents
from app.rag.chunking import split_into_chunks
from app.rag.embedding import embed_passages

_collection = None


def _get_client():
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)


def build_index():
    global _collection
    client = _get_client()
    collection = client.get_or_create_collection(name="product_kb")

    all_chunks, all_metadatas, all_ids = [], [], []
    for doc_name, doc_text in documents.items():
        for i, c in enumerate(split_into_chunks(doc_text)):
            all_chunks.append(c)
            all_metadatas.append({"source": doc_name, "chunk_index": i})
            all_ids.append(f"{doc_name}-{i}")

    embeddings = embed_passages(all_chunks)
    collection.add(ids=all_ids, embeddings=embeddings, documents=all_chunks, metadatas=all_metadatas)

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
