"""
ProductQueryAgent：對應「智慧CRM系統功能提案 #1 顧客查詢產品資訊」流程 01~04。

- receive_query()    -> 01 使用者跟機器人查詢產品內容
- vectorize_query()  -> 02 Agent 將 input 向量化
- retrieve_from_kb() -> 03 查詢 RAG 資料庫
- generate_answer()  -> 04 根據 RAG 查詢結果給 LLM 回答（整合 01~03 的完整流程入口）
"""
from app.config import settings
from app.rag.engine import get_retriever
from app.llm import get_llm
from app.providers import generate_with_provider, ProviderNotConfigured, is_configured, key_prefix

# 判斷「這個環境要不要預熱本地模型」的依據：跟 summary.py 的 fallback 邏輯一致，
# 只要有任一組線上 provider 金鑰，就代表這個環境本來就打算走線上 API，不需要（也可能沒裝 torch）
# 預熱本地模型；完全沒有線上金鑰時才預熱，確保本機測試 fallback 到本地模型時不用臨時等模型載入。
_ONLINE_PROVIDERS = ["google", "anthropic", "openai", "xai"]

SYSTEM_PROMPT = (
    "你是客服機器人，請根據提供的資訊片段回答顧客問題（可能是產品規格，也可能是保固、退換貨、"
    "運送付款等政策說明），不可使用片段以外的知識自行編造內容。"
    "回答時請在句子後方以（相關主題：主題名稱）的格式標註資訊來源。"
    "用繁體中文回答，勿出現簡體中文"
)

# 線上付費模型（Claude/GPT/Gemini/Grok）能力足夠強，可以自己準確判斷「片段裡有沒有答案」，
# 所以額外把「查無資訊」規則加回 system prompt；本地小模型則不用這條規則
# （見下方 NO_INFO_DISTANCE_THRESHOLD 的說明，原因是小模型在這個判斷上會不穩定，改用距離分數處理）。
ONLINE_SYSTEM_PROMPT = SYSTEM_PROMPT + (
    "如果片段中找不到足以回答問題的資訊，請回答「目前查無此資訊，建議聯繫真人客服（0800-123-456）」，不要臆測。"
)

NO_INFO_ANSWER = "目前查無此資訊，建議聯繫真人客服（0800-123-456）。"

# 檢索距離超過這個門檻就直接回「查無此資訊」，不呼叫 LLM——只套用在本地小模型。
#
# 原本是讓 LLM 自己判斷「片段裡有沒有答案」，但實測發現（原本用的 Qwen2.5-1.5B-Instruct）小模型在這個判斷上非常不穩定：
# system prompt 只要多加幾條規則、或換幾個字，同一個問題就會在「查無資訊」跟「正確回答」之間跳來跳去
# （例如把「如果片段」改成「如果產品資訊片段」這種無關痛癢的用字差異，就能讓模型從答對變成拒答）。
# 既然檢索距離分數本身很穩定準確，乾脆用距離分數做這個判斷，不要交給小模型猜。線上付費模型能力夠強，
# 不需要這道保險，讓它們自己判斷反而能處理更多邊緣案例（距離分數判斷是「有沒有相關主題」，
# 不是「有沒有精確答案」）。
#
# 門檻值見 app/config.py 的 RAG_NO_INFO_THRESHOLD（llamaindex 引擎用 1 - 相似度分數）；
# 是用目前 20 項產品的測試資料手動抓出來的經驗值，不是嚴謹算出來的，之後資料量變大或換
# embedding 模型，應該要重新用實際問題校準。


class ProductQueryAgent:
    def __init__(self):
        self.retriever = get_retriever()
        if not any(is_configured(p) for p in _ONLINE_PROVIDERS):
            # 沒有任何線上金鑰才預熱本地模型；線上 API only 的部署（例如 GCP，沒裝 torch）
            # 一定會有至少一組線上金鑰，完全不會執行到這裡。
            get_llm()

    def receive_query(self, query: str) -> str:
        return query.strip()

    def retrieve_from_kb(
        self, query: str, top_k: int | None = None, chatbot_id: str | None = None, use_rerank: bool = False
    ):
        return self.retriever.retrieve(query, top_k=top_k, chatbot_id=chatbot_id, use_rerank=use_rerank)

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
            f"[片段 {i+1}，主題：{r['topic']}]\n{r['text']}"
            for i, r in enumerate(retrieved_chunks)
        )
        return (
            f"資訊片段：\n{context_text}\n\n"
            f"顧客問題：{query}\n\n"
            f"請根據以上資訊片段回答顧客問題。"
        )

    def generate_answer(
        self,
        query: str,
        history=None,
        provider: str = "google",
        top_k: int | None = None,
        max_new_tokens: int = 2048,
        chatbot_id: str | None = None,
        use_rerank: bool = False,
    ):
        """
        history：之前幾輪對話 [{"role": "user"|"assistant", "content": ...}, ...]，
        用來讓機器人理解「那電池呢？」這種依賴上文的追問。
        provider：要用哪個 LLM 回答，見 app/providers.py 的 PROVIDERS。
        chatbot_id：多租戶 RAG 隔離用，穿透到 retrieve_from_kb() -> retriever.retrieve()，
        見 app/rag/llamaindex_engine.py 的說明。
        top_k：送給 LLM 的片段數，None 用系統預設（settings.RAG_DEFAULT_TOP_K，5）；每家公司
        可在後台調整，由 main.py 讀出來傳入。use_rerank：該公司是否開啟 rerank（伺服器不支援時
        會被靜默忽略）。
        max_new_tokens 預設拉高到 2048（原本 512）：本地小模型 openbmb/MiniCPM5-2B 是
        混合推理模型，app/llm.py 預設用 enable_thinking=False 關掉思考過程直接回答，
        正常情況下用不到這麼多 token；拉高只是留安全餘裕，避免關閉思考失效或換成
        其他推理模型時，答案在生成完畢前被截斷。線上 provider 只是把上限放寬，
        通常會自然結束，不受影響。

        「那電池呢？」這句話本身沒有主詞，單獨拿去向量化檢索會查到不相關的片段
        （例如查成電視遙控器電池而不是掃地機器人電池）。所以檢索用的查詢字串會把
        上一輪使用者的問題也接進來，補上缺的主詞；但送給 LLM 的「顧客問題」欄位
        仍用原始這句話，回答語氣才自然。
        """
        clean_query = self.receive_query(query)
        retrieval_query = self._build_retrieval_query(clean_query, history)
        retrieved_chunks = self.retrieve_from_kb(
            retrieval_query, top_k=top_k, chatbot_id=chatbot_id, use_rerank=use_rerank
        )

        if not retrieved_chunks:
            return NO_INFO_ANSWER, []
        if provider == "local":
            threshold = settings.RAG_NO_INFO_THRESHOLD
            # 取所有 chunk 中最小的距離：沒有 rerank 時第一筆就是最小值，行為不變；
            # 開啟 rerank 後第一筆是 rerank 分數最高的，向量距離不一定最小。
            if min(r["distance"] for r in retrieved_chunks) > threshold:
                return NO_INFO_ANSWER, []

        user_prompt = self._build_prompt(clean_query, retrieved_chunks)
        system_prompt = SYSTEM_PROMPT if provider == "local" else ONLINE_SYSTEM_PROMPT

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history or [])
        messages.append({"role": "user", "content": user_prompt})

        try:
            answer = generate_with_provider(provider, messages, max_new_tokens=max_new_tokens)
        except ProviderNotConfigured as e:
            # 回傳空的 retrieved_chunks（而不是這次真的檢索到的內容）：這則訊息是設定錯誤，
            # 跟檢索結果無關，main.py 依 retrieved 是否為空決定 type，帶著無關的 source 會誤導使用者。
            return str(e), []
        except Exception as e:
            # 線上 API 可能因為網路、額度用盡、key 失效等原因失敗，不該讓整個 /api/chat 500 掉，
            # 但真正的例外內容還是要印出來，不然 Cloud Run log 裡完全查不到失敗原因。
            # 順便印金鑰前 4 碼（不是完整金鑰）方便確認是不是載入到預期的那把 key。
            print(f"[generate_answer Error] provider={provider} key={key_prefix(provider)}: {e!r}")
            return f"呼叫 {provider} 模型時發生錯誤，請稍後再試或改用其他模型。", []

        return answer, retrieved_chunks


_agent: ProductQueryAgent | None = None


def get_agent() -> ProductQueryAgent:
    global _agent
    if _agent is None:
        _agent = ProductQueryAgent()
    return _agent
