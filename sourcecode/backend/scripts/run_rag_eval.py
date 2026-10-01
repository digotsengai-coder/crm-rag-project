"""
本機驗證用腳本：讀取 app/rag/eval_data/*.json 的標註資料集，對真實 pgvector 跑
app/rag/evaluation.py 的 Recall@K（純向量檢索）與 NDCG@K（開 rerank）評分，印出中文報告。

只給本機手動執行，不是自動化測試：
- 不在 tests/ 底下，pytest 不會收集到這個檔案，不影響任何 CI 或 pre-commit 流程。
- Dockerfile 的 CMD 只跑 uvicorn，cloudbuild.yaml 的部署流程只有 docker build/push/deploy，
  都不會執行這支腳本；即使部署到 Cloud Run，reranker 也會被 app/rag/reranker.py 的
  is_supported() 依 K_SERVICE 環境變數強制關閉，見該檔案說明。
- 會對 .env 指向的資料庫發送真實查詢（唯讀，不寫入）；如果那是共用的正式資料庫（本專案目前
  即是如此，見 backend/README.md「pgvector（Supabase）」一節），執行前請留意這一點。

用法：
    python scripts/run_rag_eval.py app/rag/eval_data/merchant_8432d265.json
    python scripts/run_rag_eval.py app/rag/eval_data/merchant_8432d265.json --k-recall 10 --k-ndcg 3
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.engine import get_retriever
from app.rag.evaluation import evaluate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", help="app/rag/eval_data/ 底下的標註資料集 JSON 路徑")
    parser.add_argument("--k-recall", type=int, default=20, help="Recall@K 的 K（純向量檢索，不開 rerank）")
    parser.add_argument("--k-ndcg", type=int, default=5, help="NDCG@K 的 K（開 rerank）")
    args = parser.parse_args()

    with open(args.dataset, encoding="utf-8") as f:
        data = json.load(f)

    chatbot_id = data["chatbot_id"]
    dataset = [{"query": c["query"], "relevant_sources": c["relevant_sources"]} for c in data["cases"]]
    # 空 relevant_sources 代表題目本身沒有正確答案（例如測試構造型號），
    # Recall/NDCG 對這種題目定義上一律是 0，混進平均值會失真，另外分開列出。
    scoreable = [c for c in dataset if c["relevant_sources"]]
    unscoreable = [c for c in dataset if not c["relevant_sources"]]

    retriever = get_retriever()
    print(f"=== 商家 {chatbot_id}｜{data.get('chatbot_description', '')} ===")
    print(f"共 {len(dataset)} 題，其中 {len(scoreable)} 題可算 Recall/NDCG，{len(unscoreable)} 題無正確答案（另列）\n")

    print(f"--- Recall@{args.k_recall}（純向量檢索，不開 rerank）---")
    recall_fn = lambda q: retriever.retrieve(q, top_k=args.k_recall, chatbot_id=chatbot_id, use_rerank=False)
    recall_report = evaluate_dataset(scoreable, recall_fn, k=args.k_recall)
    for case in recall_report["cases"]:
        mark = "✓" if case["recall_at_k"] == 1.0 else f"未完全命中（{case['recall_at_k']:.2f}）"
        print(f"[{mark}] {case['query']}")
    print(f"\n平均 Recall@{args.k_recall}：{recall_report['averages']['recall_at_k']:.4f}")
    print(f"平均 Precision@{args.k_recall}：{recall_report['averages']['precision_at_k']:.4f}")
    print(f"平均 MRR：{recall_report['averages']['mrr']:.4f}")

    print(f"\n--- NDCG@{args.k_ndcg}（開 rerank）---")
    ndcg_fn = lambda q: retriever.retrieve(q, top_k=args.k_ndcg, chatbot_id=chatbot_id, use_rerank=True)
    ndcg_report = evaluate_dataset(scoreable, ndcg_fn, k=args.k_ndcg)
    for case in ndcg_report["cases"]:
        print(f"[NDCG@{args.k_ndcg}={case['ndcg_at_k']:.2f}] {case['query']}")
        if case["ndcg_at_k"] < 1.0:
            print(f"    → 排序：{case['retrieved_sources']}")
    print(f"\n平均 NDCG@{args.k_ndcg}：{ndcg_report['averages']['ndcg_at_k']:.4f}")

    if unscoreable:
        print(f"\n--- 無正確答案的題目（{len(unscoreable)} 題，檢查會不會誤答）---")
        for case in unscoreable:
            top = retriever.retrieve(case["query"], top_k=5, chatbot_id=chatbot_id, use_rerank=False)
            print(f"問題：{case['query']}")
            for i, chunk in enumerate(top, start=1):
                print(f"  第{i}名 source={chunk['source']}　distance={chunk['distance']:.4f}")


if __name__ == "__main__":
    main()
