"""
「LlamaIndex」RAG 引擎：用 LlamaIndex 的 VectorStoreIndex + pgvector（PostgreSQL）取代原本
的本地磁碟 persist，換取 LlamaIndex 原生的 insert_nodes/delete_ref_doc 增量更新能力，讓
app/rag/documents_store.py 能做單一文件的新增/刪除/更新，不用整批重建索引。
提供統一檢索介面 retrieve(query, top_k)，見 app/rag/engine.py。

語意拆分（產品的介紹/規格/彩蛋、政策文件的各小節）沿用 app/rag/product_parser.py /
app/rag/policy_parser.py 的純函式規則，「怎麼切」是文件格式特有的知識，跟「用哪套框架做
向量索引/檢索」是兩件事；app/rag/documents_store.py 負責把 parser 輸出的 chunk 包成
LlamaIndex 的 TextNode 並寫進 pgvector。

索引資料存在 settings.RAG_PG_* 指定的 PostgreSQL（pgvector extension），服務啟動時若該
table 是空的，會由 documents_store.seed_if_empty() 自動把 app/data/ 下既有的知識庫文件灌入
（一次性、冪等）；之後要新增/刪除/更新單一文件改走 /api/admin/documents 系列 API，不用再
手動清資料重建索引。
"""
from llama_index.core import Settings as LlamaSettings
from llama_index.core import VectorStoreIndex
from llama_index.core.vector_stores import FilterOperator, MetadataFilter, MetadataFilters
from llama_index.vector_stores.postgres import PGVectorStore

from app.config import settings

# intfloat/multilingual-e5-base 輸出 768 維，PGVectorStore 建表時的向量欄位維度要對齊這個數字
EMBED_DIM = 768


def _get_embed_model():
    # EMBEDDING_BACKEND=onnx_int8（預設）：繞過 llama-index 官方的 optimum 整合套件
    # （跟這個專案其他套件的 transformers 版本要求硬衝突，無解，見 onnx_embedding.py 開頭
    # 說明），改用 onnxruntime 直接跑 int8 量化版本，檔案小、記憶體佔用低，且 onnxruntime
    # 本身沒有 MPS 執行緒安全的問題（下面 HuggingFaceEmbedding 那個坑不適用）。
    if settings.EMBEDDING_BACKEND == "onnx_int8":
        from app.rag.onnx_embedding import OnnxInt8Embedding

        return OnnxInt8Embedding()

    # EMBEDDING_BACKEND=huggingface：原本的 fp32 版本，保留當作 int8 版本出問題時的退路。
    # e5 系列模型需要 "query: " / "passage: " 前綴才能發揮非對稱檢索的效果，
    # HuggingFaceEmbedding 的 query_instruction/text_instruction 剛好對應這兩個前綴。
    #
    # device 強制指定 "cpu"：不指定時 torch 在 Apple Silicon 上會自動選用 MPS（GPU）後端，
    # 但 PyTorch 的 MPS 後端不是執行緒安全的——FastAPI 用 threadpool 並行處理多個請求時，
    # 兩個請求同時呼叫 embedding 會讓 MPS 內部共用的 MetalShaderLibrary 雜湊表在多執行緒下
    # 被同時寫入而損毀，導致整個 process SIGSEGV 直接崩潰（曾在批次上傳測試中重現）。
    # 這個模型不大，CPU 推論速度可接受，用 CPU 換取穩定性。
    #
    # import 留在這裡（不搬到檔案最上面）：HuggingFaceEmbedding 會連帶載入 torch/transformers，
    # 實測光 import 就吃掉數百 MB 記憶體，onnx_int8（預設）完全用不到，搬到頂層會讓每次
    # get_retriever() 第一次被呼叫（不管哪個 EMBEDDING_BACKEND）都白白背這個記憶體開銷。
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    return HuggingFaceEmbedding(
        model_name=settings.EMBEDDING_MODEL_NAME,
        query_instruction="query: ",
        text_instruction="passage: ",
        device="cpu",
    )


def _get_vector_store() -> PGVectorStore:
    return PGVectorStore.from_params(
        host=settings.RAG_PG_HOST,
        port=str(settings.RAG_PG_PORT),
        database=settings.RAG_PG_DATABASE,
        user=settings.RAG_PG_USER,
        password=settings.RAG_PG_PASSWORD,
        table_name=settings.RAG_PG_TABLE,
        embed_dim=EMBED_DIM,
    )


class LlamaIndexRetriever:
    name = "llamaindex"

    def __init__(self):
        LlamaSettings.embed_model = _get_embed_model()
        LlamaSettings.llm = None  # 這裡只用 LlamaIndex 做檢索，生成交給 app/providers.py 統一處理

        self.vector_store = _get_vector_store()
        # from_vector_store() 直接掛載既有向量資料，不會重新 embed（跟舊版
        # load_index_from_storage() 對本地磁碟 persist 的效果相同，只是後端換成 pgvector）
        self.index = VectorStoreIndex.from_vector_store(
            self.vector_store, embed_model=LlamaSettings.embed_model
        )

        # 延遲 import 避免循環 import（documents_store.py 也會用到本模組建立的 index 型別）
        from app.rag.documents_store import seed_if_empty
        seed_if_empty(self.index)

    def retrieve(
        self, query: str, top_k: int | None = None, chatbot_id: str | None = None, use_rerank: bool = False
    ) -> list[dict]:
        """
        chatbot_id：多租戶 RAG 隔離的強制過濾條件（見 app/rag/documents_store.py 的
        chatbot_id 隔離說明）。用 LlamaIndex 的 MetadataFilters 帶進 retriever，讓 pgvector
        在 SQL 層面就篩掉其他公司的向量，不是查出來後再用程式碼過濾（避免因為
        similarity_top_k 篩選發生在過濾之前，導致其他公司的資料擠掉真正該回傳的結果）。
        chatbot_id 為 None（呼叫端還沒有公司概念）時维持舊行為，不加過濾條件。

        top_k：最後回傳幾筆，None 用系統預設 settings.RAG_DEFAULT_TOP_K（5）。
        use_rerank：這家公司有沒有在後台開啟 rerank。true 且這台伺服器支援時（reranker.is_supported()），
        先用向量檢索撈 RERANK_CANDIDATES 筆候選（同樣帶 chatbot_id 過濾），交給 reranker 重排後只回傳
        前 top_k 筆；不支援（例如 Cloud Run）或 reranker 載入失敗時，靜默退回一般的向量檢索 top_k，
        不報錯。見 app/rag/reranker.py。
        """
        # 延遲 import：不支援 rerank 的部署不需要載入 reranker 模組
        from app.rag.reranker import get_candidate_count, get_reranker, rerank_chunks

        top_k = top_k or settings.RAG_DEFAULT_TOP_K
        reranker = get_reranker() if use_rerank else None
        fetch_k = max(get_candidate_count(), top_k) if reranker else top_k
        filters = None
        if chatbot_id is not None:
            filters = MetadataFilters(
                filters=[MetadataFilter(key="chatbot_id", value=chatbot_id, operator=FilterOperator.EQ)]
            )
        retriever = self.index.as_retriever(similarity_top_k=fetch_k, filters=filters)
        nodes = retriever.retrieve(query)
        retrieved = []
        for n in nodes:
            meta = n.node.metadata
            # LlamaIndex 的 score 是「相似度」（越高越相關），統一轉成 distance（越低越相關），
            # 給 agent.py 的 RAG_NO_INFO_THRESHOLD 判斷邏輯使用（見 app/config.py）。
            score = n.score if n.score is not None else 0.0
            retrieved.append({
                "text": n.node.get_content(),
                "source": meta.get("source", ""),
                "topic": meta.get("topic", ""),
                "category": meta.get("category", ""),
                "distance": 1 - score,
            })
        if reranker:
            return rerank_chunks(query, retrieved, reranker, top_k)
        return retrieved
