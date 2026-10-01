"""
RAG 重排序（rerank）：向量檢索先撈一批候選 chunk（預設 20 筆），再用 Qwen3-Reranker-0.6B
（ONNX INT8，YesNo 版）依「跟問題有多相關」重新排序，只留前 k 筆交給 LLM。

為什麼要做：向量相似度只看兩段文字「語意像不像」，排序容易被措辭相近但答非所問的 chunk 干擾；
reranker 把「問題 + 單一候選」放進同一個 prompt，讓模型直接判斷「這段有沒有回答問題」（輸出
yes／no），判斷更準，但成本高（每個候選都要跑一次模型），所以只對向量檢索撈出的少量候選做。

執行方式：用 onnxruntime 在同一個 Python 行程內載入模型（跟 app/rag/onnx_embedding.py 同樣的做法），
不需要編譯任何東西、沒有子行程；模型檔第一次啟用時由 huggingface_hub 下載到 Hugging Face 快取。
模型：n24q02m/Qwen3-Reranker-0.6B-ONNX 的 onnx/model_yesno_quantized.onnx，這是官方
Qwen/Qwen3-Reranker-0.6B（Apache-2.0）轉成 ONNX 並做動態 INT8 量化的社群轉檔，不是 Qwen 官方發布。
必須用 YesNo 版：完整版模型會輸出「每個 token × 整個詞表」的 logits，推論時要吃到約 12 GB 記憶體；
YesNo 版只輸出最後一個 token 的 [no, yes] 兩個 logit，約 600 MB。prompt 樣板與打分公式對照
Qwen 官方模型卡（https://huggingface.co/Qwen/Qwen3-Reranker-0.6B）。

每個候選各跑一次（batch=1）：這個 ONNX 沒有 position_ids 輸入，批次時的 padding 會讓分數依
批次組成而改變，單筆執行分數才穩定；代價是延遲隨候選數線性增加。

失敗處理：模型下載不到、推論出錯、超過時間預算等任何錯誤都不能讓聊天中斷，rerank_chunks()
一律退回原本向量檢索的排序，見該函式說明。

正式環境（Cloud Run）不啟用，見 is_supported()。
"""
import importlib.util
import math
import os
import threading
import time
from typing import Optional

import numpy as np

from app.config import settings

# 限制一次最多 rerank 幾筆候選：每筆都要跑一次模型，延遲隨筆數線性增加。
MAX_CANDIDATES = 100

# 使用者文字裡不能出現的對話樣板 token：移除它們，避免有人在問題或知識庫文件裡塞
# <|im_end|> 之類的字串，提早結束 user 段落、偽造 assistant 回答來操縱排序（prompt injection）。
_SPECIAL_TOKEN_STRINGS = ("<|im_start|>", "<|im_end|>", "<|endoftext|>")

_SYSTEM_PROMPT = (
    "<|im_start|>system\n"
    "Judge whether the Document meets the requirements based on the Query and the Instruct "
    'provided. Note that the answer can only be "yes" or "no".<|im_end|>\n'
    "<|im_start|>user\n"
)
_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

# YesNo 版模型輸出 (batch, 2) 的兩個 logit 位置：索引 0 是 no、索引 1 是 yes。已用真實模型驗證
# （相關文件的 yes logit 明顯高於 no，不相關則相反）。
_NO_INDEX = 0
_YES_INDEX = 1


class RerankError(Exception):
    """rerank 過程的任何失敗；呼叫端（rerank_chunks）會接住並退回向量檢索的排序。"""


def _sanitize(text: str) -> str:
    for tok in _SPECIAL_TOKEN_STRINGS:
        text = text.replace(tok, "")
    return text


def format_prompt(query: str, doc: str, instruction: str) -> str:
    """組出單一「問題 + 候選」的 prompt（Qwen3-Reranker 官方格式）。"""
    return (
        f"{_SYSTEM_PROMPT}<Instruct>: {_sanitize(instruction)}\n"
        f"<Query>: {_sanitize(query)}\n<Document>: {_sanitize(doc)}{_SUFFIX}"
    )


def logits_to_score(no_logit: float, yes_logit: float) -> float:
    """P(yes) = softmax([no, yes])[yes] = sigmoid(yes - no)，範圍 0～1，越高越相關。"""
    diff = yes_logit - no_logit
    # 分開處理正負，避免 exp() 在極端 logit 下溢位
    if diff >= 0:
        return 1.0 / (1.0 + math.exp(-diff))
    e = math.exp(diff)
    return e / (1.0 + e)


class OnnxQwen3Reranker:
    """Qwen3-Reranker-0.6B YesNo ONNX：每個候選跑一次，回傳 P(yes)。"""

    # 同時進行的 rerank 呼叫數。每次呼叫會連續跑數十次模型、吃滿 CPU，不限制的話多個聊天請求
    # 同時進來只會互相拖慢，全部都超過時間預算。
    _semaphore = threading.BoundedSemaphore(settings.RERANK_MAX_CONCURRENCY)

    def __init__(self, model_path: str, tokenizer_path: str):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        options = ort.SessionOptions()
        if settings.RERANK_ONNX_THREADS > 0:
            options.intra_op_num_threads = settings.RERANK_ONNX_THREADS
        self._session = ort.InferenceSession(
            model_path, sess_options=options, providers=["CPUExecutionProvider"]
        )
        self._input_names = {i.name for i in self._session.get_inputs()}
        self._tok = Tokenizer.from_file(tokenizer_path)
        self._tok.no_padding()
        self._tok.no_truncation()

    def _truncate(self, text: str, max_tokens: int) -> str:
        ids = self._tok.encode(text, add_special_tokens=False).ids
        if len(ids) <= max_tokens:
            return text
        return self._tok.decode(ids[:max_tokens])

    def _score_one(self, prompt: str) -> float:
        ids = np.array([self._tok.encode(prompt, add_special_tokens=False).ids], dtype=np.int64)
        feed = {"input_ids": ids}
        if "attention_mask" in self._input_names:
            feed["attention_mask"] = np.ones_like(ids)
        if "token_type_ids" in self._input_names:
            feed["token_type_ids"] = np.zeros_like(ids)
        try:
            logits = np.asarray(self._session.run(None, feed)[0])
        except Exception as e:
            raise RerankError(f"onnxruntime 推論失敗：{e!r}") from e
        if logits.ndim != 2 or logits.shape[1] != 2:
            raise RerankError(f"預期輸出 (batch, 2)，實際 {logits.shape}；是否用了完整詞表版的模型？")
        return logits_to_score(float(logits[0, _NO_INDEX]), float(logits[0, _YES_INDEX]))

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        """回傳與 documents 同順序的相關度分數（P(yes)，0～1，越高越相關）。"""
        if not documents:
            return []
        if len(documents) > MAX_CANDIDATES:
            raise RerankError(f"候選數 {len(documents)} 超過上限 {MAX_CANDIDATES}")

        query = self._truncate(query, settings.RERANK_MAX_QUERY_TOKENS)
        deadline = time.monotonic() + settings.RERANK_TIMEOUT_SECONDS
        scores = []
        with self._semaphore:
            for doc in documents:
                # 時間預算：超過就整批放棄（退回向量排序），不要讓聊天請求無限等下去
                if time.monotonic() > deadline:
                    raise RerankError(f"超過時間預算 {settings.RERANK_TIMEOUT_SECONDS} 秒")
                doc = self._truncate(doc, settings.RERANK_MAX_DOC_TOKENS)
                scores.append(self._score_one(format_prompt(query, doc, settings.RERANK_INSTRUCTION)))
        return scores


_reranker: Optional[OnnxQwen3Reranker] = None
_reranker_init_failed = False
_init_lock = threading.Lock()


def get_candidate_count() -> int:
    """向量檢索要撈幾筆候選給 reranker（不超過 MAX_CANDIDATES）。"""
    return min(settings.RERANK_CANDIDATES, MAX_CANDIDATES)


def is_supported() -> bool:
    """
    這台伺服器能不能做 rerank。條件缺一不可：
    1. RERANK_ENABLED=true（總開關，預設關閉）。
    2. 不在 Cloud Run 上：Cloud Run 一定會設 K_SERVICE。正式環境不啟用 reranker（沒有 GPU、也不把
       模型打包進映像檔），所以就算有人誤設 RERANK_ENABLED=true 也一律停用（跟 DEV_LOGIN_ENABLED
       同樣的防護做法，見 app/main.py）。
    3. onnxruntime 與 tokenizers 都裝了，否則開了也只會每次載入失敗再退回。

    為什麼不能只靠「後台頁面不讓人勾」：本機與正式環境共用同一個資料庫，開發時在本機勾選
    rerank 會存進資料庫，正式環境也讀得到那個值，所以「支援與否」必須由伺服器端自己判斷。
    """
    if not settings.RERANK_ENABLED:
        return False
    if os.getenv("K_SERVICE"):
        return False
    return all(importlib.util.find_spec(m) is not None for m in ("onnxruntime", "tokenizers"))


def get_reranker() -> Optional[OnnxQwen3Reranker]:
    """
    這台伺服器不支援 rerank（見 is_supported()），或載入失敗（模型檔下載不到、ONNX 檔損毀）時回傳
    None，呼叫端就走原本的純向量檢索。載入失敗只會印一次錯誤，之後不再重試，避免每個聊天請求都
    重複下載／失敗；修正設定後要重啟服務才會再試。
    """
    global _reranker, _reranker_init_failed
    if not is_supported():
        return None
    if _reranker is not None or _reranker_init_failed:
        return _reranker
    with _init_lock:
        if _reranker is not None or _reranker_init_failed:
            return _reranker
        try:
            # 延遲 import：不支援 rerank 的部署完全不會載入這些
            from huggingface_hub import hf_hub_download

            _reranker = OnnxQwen3Reranker(
                model_path=hf_hub_download(repo_id=settings.RERANK_MODEL_REPO, filename=settings.RERANK_MODEL_FILE),
                tokenizer_path=hf_hub_download(repo_id=settings.RERANK_MODEL_REPO, filename="tokenizer.json"),
            )
        except Exception as e:
            _reranker_init_failed = True
            print(f"[rerank Error] reranker 載入失敗，改用純向量檢索：{e!r}")
    return _reranker


def rerank_chunks(query: str, chunks: list[dict], reranker: OnnxQwen3Reranker, top_n: int) -> list[dict]:
    """
    依 reranker 分數重排 chunks（向量檢索的結果），回傳前 top_n 筆，每筆多一個 rerank_score。
    原本的 distance（向量距離）保留不動：agent.py 的「查無資料」門檻是用向量距離校準的，
    reranker 分數（P(yes)，0～1）是另一種尺度，不能直接拿來套同一個門檻。

    任何失敗都退回向量檢索的前 top_n 筆（沒有 rerank_score），不讓聊天中斷。
    """
    if len(chunks) <= 1:
        return chunks
    try:
        scores = reranker.rerank(query, [c["text"] for c in chunks])
    except Exception as e:
        print(f"[rerank Error] 改用向量檢索排序：{e!r}")
        return chunks[:top_n]
    ranked = sorted(zip(chunks, scores), key=lambda pair: pair[1], reverse=True)
    return [{**chunk, "rerank_score": score} for chunk, score in ranked[:top_n]]
