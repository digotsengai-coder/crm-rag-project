"""
向量資料庫（Chroma）：對應提案流程「查詢 RAG 資料庫」。

使用記憶體版 Chroma client，服務重啟後會重新建立索引（重跑一次即可）；
正式上線可改用 chromadb.PersistentClient(path=...) 做持久化。
"""
import chromadb
from app.documents import documents
from app.rag.chunking import split_into_chunks
from app.rag.embedding import embed_passages

_collection = None


def build_index():
    global _collection
    client = chromadb.Client()
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
    if _collection is None:
        _collection = build_index()
    return _collection
