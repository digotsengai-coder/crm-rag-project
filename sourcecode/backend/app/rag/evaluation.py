"""
RAG 檢索品質評分指標：純函式計算 precision@k / recall@k / MRR / NDCG@k，只吃
app/rag/engine.py retrieve() 回傳的 chunk list（用 "source" 欄位判斷是否命中），
不綁定任何特定 retriever 實作或資料庫連線，方便在本機用標註資料集離線跑分、寫測試。

relevance 一律是二元的（命中／沒命中標註的 relevant_sources），沒有分級相關度：
這個專案的知識庫是「一段文字回答一個問題」的片段，不像搜尋引擎有明顯的相關度分級需求。

一份文件（同一個 source）常被切成多個 chunk，檢索結果可能同一個 source 連續出現好幾筆
（例如 faq.md 的不同小節都命中）。指標定義是「文件層級」而非「chunk 層級」的排名品質，
所以 _dedupe_preserve_order() 一律先把 retrieved_sources 依第一次出現的名次去重，同一份
文件只算一次、算在它第一次出現的排名——不去重的話，同一份文件出現越多次，DCG 會重複
累加超過 1（IDCG 的上限），NDCG 也會失真超過 1。

evaluate_dataset() 的 retrieve_fn 由呼叫端注入（型別見 RetrieveFn），不在這裡 import
app.rag.engine：多租戶隔離、rerank 開關、top_k 這些檢索參數都由呼叫端決定，這個模組只管
「檢索結果對不對」。
"""
import math
from typing import Callable, TypedDict

RetrieveFn = Callable[[str], list[dict]]


class EvalCase(TypedDict):
    query: str
    relevant_sources: list[str]


def _sources(retrieved: list[dict]) -> list[str]:
    return [chunk["source"] for chunk in retrieved]


def _dedupe_preserve_order(sources: list[str]) -> list[str]:
    """同一份文件的多個 chunk 只保留第一次出現的名次，其餘捨棄（見模組開頭說明）。"""
    seen: set[str] = set()
    deduped = []
    for s in sources:
        if s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped


def precision_at_k(retrieved_sources: list[str], relevant_sources: set[str], k: int) -> float:
    """前 k 筆（去重後）裡有幾成命中標註的 relevant_sources。不足 k 筆時，
    分母用實際筆數（缺筆不該被當成分母灌水拉低分數，那是檢索筆數不足的問題，不是精準度問題）。"""
    top_k = _dedupe_preserve_order(retrieved_sources)[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for s in top_k if s in relevant_sources)
    return hits / len(top_k)


def recall_at_k(retrieved_sources: list[str], relevant_sources: set[str], k: int) -> float:
    """標註的 relevant_sources 裡，有幾成出現在前 k 筆檢索結果中。"""
    if not relevant_sources:
        return 0.0
    top_k = set(_dedupe_preserve_order(retrieved_sources)[:k])
    hits = len(top_k & relevant_sources)
    return hits / len(relevant_sources)


def mrr(retrieved_sources: list[str], relevant_sources: set[str]) -> float:
    """第一個命中的相關結果排第幾名（去重後的文件名次），分數是 1/rank；整份結果都沒命中則為 0。"""
    for rank, source in enumerate(_dedupe_preserve_order(retrieved_sources), start=1):
        if source in relevant_sources:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved_sources: list[str], relevant_sources: set[str], k: int) -> float:
    """二元相關度的 NDCG@k：DCG 用命中位置（去重後的文件名次）的 log2 折扣加總，除以「所有
    相關項目都排在最前面」時的理想 DCG（IDCG）做正規化，範圍 0～1。relevant_sources 為空、
    或前 k 筆完全沒命中則為 0。"""
    if not relevant_sources:
        return 0.0
    top_k = _dedupe_preserve_order(retrieved_sources)[:k]
    dcg = sum(1.0 / math.log2(rank + 1) for rank, s in enumerate(top_k, start=1) if s in relevant_sources)
    ideal_hits = min(len(relevant_sources), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def evaluate_case(retrieved: list[dict], relevant_sources: list[str], k: int) -> dict:
    """單一 query 的檢索結果對一份標註算出全部指標，供 evaluate_dataset() 彙總，
    也可以直接拿單一 query 的結果單獨呼叫（例如手動除錯某一題為什麼分數低）。"""
    sources = _sources(retrieved)
    relevant = set(relevant_sources)
    return {
        "precision_at_k": precision_at_k(sources, relevant, k),
        "recall_at_k": recall_at_k(sources, relevant, k),
        "mrr": mrr(sources, relevant),
        "ndcg_at_k": ndcg_at_k(sources, relevant, k),
        "retrieved_sources": sources,
    }


def evaluate_dataset(dataset: list[EvalCase], retrieve_fn: RetrieveFn, k: int) -> dict:
    """對整份標註資料集逐題呼叫 retrieve_fn(query)，回傳每題明細與四項指標的平均值。
    dataset 為空時平均值一律回 0.0，不丟例外（呼叫端可能先過濾出空清單，屬正常情況）。"""
    per_case = []
    for case in dataset:
        retrieved = retrieve_fn(case["query"])
        metrics = evaluate_case(retrieved, case["relevant_sources"], k)
        per_case.append({"query": case["query"], **metrics})

    n = len(per_case)
    averages = {
        name: (sum(c[name] for c in per_case) / n if n else 0.0)
        for name in ("precision_at_k", "recall_at_k", "mrr", "ndcg_at_k")
    }
    return {"k": k, "case_count": n, "averages": averages, "cases": per_case}
