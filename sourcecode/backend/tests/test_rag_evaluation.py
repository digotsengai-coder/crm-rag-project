"""
app/rag/evaluation.py 的指標計算測試：全部用手造的 retrieved/relevant_sources，
不連真實 pgvector，純驗證數學算對，見 app/rag/evaluation.py 開頭說明。
"""
import math

import pytest

from app.rag.evaluation import (
    evaluate_case,
    evaluate_dataset,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


def test_precision_at_k_counts_hits_within_top_k():
    retrieved = ["a", "b", "c", "d"]
    relevant = {"a", "c", "z"}

    assert precision_at_k(retrieved, relevant, k=4) == 0.5  # a, c 命中，共 4 筆
    assert precision_at_k(retrieved, relevant, k=2) == 0.5  # a 命中，共 2 筆


def test_precision_at_k_uses_actual_count_when_fewer_than_k():
    retrieved = ["a"]
    relevant = {"a"}

    assert precision_at_k(retrieved, relevant, k=5) == 1.0  # 分母用實際 1 筆，不是 5


def test_precision_at_k_empty_retrieved_is_zero():
    assert precision_at_k([], {"a"}, k=5) == 0.0


def test_recall_at_k_counts_fraction_of_relevant_found():
    retrieved = ["a", "x", "c"]
    relevant = {"a", "b", "c"}

    assert recall_at_k(retrieved, relevant, k=3) == pytest.approx(2 / 3)
    assert recall_at_k(retrieved, relevant, k=1) == pytest.approx(1 / 3)


def test_recall_at_k_empty_relevant_is_zero():
    assert recall_at_k(["a"], set(), k=5) == 0.0


def test_mrr_uses_first_hit_rank():
    assert mrr(["x", "y", "a"], {"a"}) == pytest.approx(1 / 3)
    assert mrr(["a", "x"], {"a"}) == 1.0
    assert mrr(["x", "y"], {"a"}) == 0.0


def test_ndcg_at_k_perfect_ranking_is_one():
    retrieved = ["a", "b", "x"]
    relevant = {"a", "b"}

    assert ndcg_at_k(retrieved, relevant, k=3) == pytest.approx(1.0)


def test_ndcg_at_k_penalizes_lower_rank_hits():
    relevant = {"a"}
    top = ndcg_at_k(["a", "x"], relevant, k=2)
    bottom = ndcg_at_k(["x", "a"], relevant, k=2)

    assert top == pytest.approx(1.0)
    assert bottom == pytest.approx(1 / math.log2(3))
    assert bottom < top


def test_ndcg_at_k_no_hits_is_zero():
    assert ndcg_at_k(["x", "y"], {"a"}, k=2) == 0.0


def test_duplicate_source_chunks_do_not_inflate_scores_above_one():
    # 同一份文件被切成多個 chunk，檢索結果連續出現好幾次同一個 source（真實案例：
    # faq.md 的不同小節都命中同一題 query）；去重前 NDCG 會累加超過 1。
    retrieved = ["faq.md", "faq.md", "faq.md", "faq.md", "faq.md"]
    relevant = {"faq.md"}

    assert precision_at_k(retrieved, relevant, k=5) == 1.0
    assert recall_at_k(retrieved, relevant, k=5) == 1.0
    assert mrr(retrieved, relevant) == 1.0
    assert ndcg_at_k(retrieved, relevant, k=5) == pytest.approx(1.0)


def test_evaluate_case_combines_all_metrics():
    retrieved = [
        {"source": "faq.md", "text": "..."},
        {"source": "shipping_payment.md", "text": "..."},
    ]

    result = evaluate_case(retrieved, relevant_sources=["faq.md"], k=2)

    assert result["precision_at_k"] == 0.5
    assert result["recall_at_k"] == 1.0
    assert result["mrr"] == 1.0
    assert result["ndcg_at_k"] == pytest.approx(1.0)
    assert result["retrieved_sources"] == ["faq.md", "shipping_payment.md"]


def test_evaluate_dataset_averages_across_cases():
    fake_results = {
        "退貨政策是什麼？": [{"source": "return_policy.md"}],
        "運費怎麼算？": [{"source": "faq.md"}],  # 標註答案是 shipping_payment.md，這題沒命中
    }

    def fake_retrieve(query: str) -> list[dict]:
        return fake_results[query]

    dataset = [
        {"query": "退貨政策是什麼？", "relevant_sources": ["return_policy.md"]},
        {"query": "運費怎麼算？", "relevant_sources": ["shipping_payment.md"]},
    ]

    report = evaluate_dataset(dataset, fake_retrieve, k=1)

    assert report["case_count"] == 2
    assert report["averages"]["precision_at_k"] == pytest.approx(0.5)
    assert report["averages"]["recall_at_k"] == pytest.approx(0.5)
    assert report["averages"]["mrr"] == pytest.approx(0.5)
    assert [c["query"] for c in report["cases"]] == ["退貨政策是什麼？", "運費怎麼算？"]


def test_evaluate_dataset_empty_dataset_returns_zero_averages():
    report = evaluate_dataset([], lambda q: [], k=5)

    assert report["case_count"] == 0
    assert report["averages"] == {
        "precision_at_k": 0.0,
        "recall_at_k": 0.0,
        "mrr": 0.0,
        "ndcg_at_k": 0.0,
    }

