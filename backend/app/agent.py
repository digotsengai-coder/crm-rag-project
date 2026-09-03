"""
ProductQueryAgent：對應「智慧CRM系統功能提案 #1 顧客查詢產品資訊」流程 01~04。

- receive_query()    -> 01 使用者跟機器人查詢產品內容
- vectorize_query()  -> 02 Agent 將 input 向量化
- retrieve_from_kb() -> 03 查詢 RAG 資料庫
- generate_answer()  -> 04 根據 RAG 查詢結果給 LLM 回答（整合 01~03 的完整流程入口）
"""
from app.rag.vectorstore import get_collection
from app.rag.embedding import embed_query
from app.llm import get_llm, generate as llm_generate

SYSTEM_PROMPT = (
    "你是官方線上智慧客服機器人，負責回答顧客關於產品規格、保固與常見問題的疑問。"
    "請務必只根據下方提供的「產品資訊片段」回答問題，不可使用片段以外的知識自行編造內容。"
    "如果產品資訊片段中找不到足以回答問題的資訊，請明確回答「目前查無此資訊，建議聯繫真人客服（0800-123-456）」，不要臆測。"
    "回答時請在句子後方以（來源：文件名稱）的格式標註引用的文件。"
)


class ProductQueryAgent:
    def __init__(self, system_prompt: str = SYSTEM_PROMPT):
        self.collection = get_collection()
        get_llm()  # 建構時就把 LLM 一併載入，讓 get_agent() 真正做到完整預載
        self.system_prompt = system_prompt

    def receive_query(self, query: str) -> str:
        return query.strip()

    def vectorize_query(self, query: str):
        return embed_query(query)

    def retrieve_from_kb(self, query_embedding, top_k: int = 3):
        results = self.collection.query(query_embeddings=[query_embedding], n_results=top_k)
        retrieved = []
        for doc, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        ):
            retrieved.append({"text": doc, "source": meta["source"], "distance": dist})
        return retrieved

    def _build_retrieval_query(self, query: str, history) -> str:
        if not history:
            return query
        last_user_turn = next(
            (h["content"] for h in reversed(history) if h.get("role") == "user"),
            None,
        )
        if not last_user_turn:
            return query
        return f"{last_user_turn} {query}"

    def _build_prompt(self, query: str, retrieved_chunks) -> str:
        context_text = "\n\n".join(
            f"[片段 {i+1}，來源：{r['source']}]\n{r['text']}"
            for i, r in enumerate(retrieved_chunks)
        )
        return (
            f"產品資訊片段：\n{context_text}\n\n"
            f"顧客問題：{query}\n\n"
            f"請根據以上產品資訊片段回答顧客問題。"
        )

    def generate_answer(self, query: str, history=None, top_k: int = 3, max_new_tokens: int = 512):
        """
        history：之前幾輪對話 [{"role": "user"|"assistant", "content": ...}, ...]，
        用來讓機器人理解「那電池呢？」這種依賴上文的追問。

        「那電池呢？」這句話本身沒有主詞，單獨拿去向量化檢索會查到不相關的片段
        （例如查成電視遙控器電池而不是掃地機器人電池）。所以檢索用的查詢字串會把
        上一輪使用者的問題也接進來，補上缺的主詞；但送給 LLM 的「顧客問題」欄位
        仍用原始這句話，回答語氣才自然。
        """
        clean_query = self.receive_query(query)
        retrieval_query = self._build_retrieval_query(clean_query, history)
        query_embedding = self.vectorize_query(retrieval_query)
        retrieved_chunks = self.retrieve_from_kb(query_embedding, top_k=top_k)
        user_prompt = self._build_prompt(clean_query, retrieved_chunks)

        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history or [])
        messages.append({"role": "user", "content": user_prompt})
        answer = llm_generate(messages, max_new_tokens=max_new_tokens)

        return answer, retrieved_chunks


_agent: ProductQueryAgent | None = None


def get_agent() -> ProductQueryAgent:
    global _agent
    if _agent is None:
        _agent = ProductQueryAgent()
    return _agent
