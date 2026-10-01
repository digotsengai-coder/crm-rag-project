"""
RAG 檢索引擎入口：目前只有 llamaindex 一套實作（LlamaIndex VectorStoreIndex + pgvector，
本地 embedding），介面：
    retrieve(query: str, top_k: int) -> [{"text","source","topic","category","distance"}]
agent.py 只依賴這個介面，不需要知道背後實作細節。

（原本還有兩套：自製的 "custom" 引擎（Chroma + 手寫檢索）已隨 llamaindex 引擎改用 pgvector
一起退休；線上 "online"/"gemini"（Google Gemini embedding + Chroma）引擎也已移除，RAG
embedding 統一改用 llamaindex 本地 embedding，不再依賴線上 embedding API。）

llamaindex_engine.py 會連帶 import torch/transformers（llama_index.embeddings.huggingface），
即使 EMBEDDING_BACKEND=onnx_int8 也一樣，是個重量級 import（本機實測約 3.5 秒、多吃 ~500MB
記憶體）。get_retriever() 故意把這個 import 留在函式內、不搬到檔案最上面，讓它只在真的有人
問產品問題（第一次呼叫 get_retriever()）時才發生，避免 Cloud Run 容器啟動階段被這個 import
拖慢甚至爆記憶體、卡過健康檢查逾時。
"""
_retriever = None


def get_retriever():
    global _retriever
    if _retriever is None:
        from app.rag.llamaindex_engine import LlamaIndexRetriever

        _retriever = LlamaIndexRetriever()
    return _retriever
