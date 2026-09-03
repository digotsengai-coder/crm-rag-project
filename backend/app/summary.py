"""
當日提問摘要：給管理者看「今天使用者都在問什麼」的功能。

流程：
1. 從 chat_log 撈出指定日期的所有提問原文
2. 問題數量較多時先分批（每批 SUMMARY_BATCH_SIZE 則）各自摘要成主題重點，
   避免一次把所有問題塞進 LLM context（1.5B 模型 context 有限，問題一多會爆或品質變差）
3. 有多批的話，再把每批摘要匯總、做一次「摘要的摘要」，產生最終報告

這是 map-reduce 的簡化版本，資料量大時可以再拆更細；目前先滿足小型客服場景。
"""
from app.chat_log import get_messages_for_date
from app.llm import generate as llm_generate

SUMMARY_BATCH_SIZE = 30

_BATCH_SYSTEM_PROMPT = (
    "你是客服數據分析助理，負責幫管理者整理顧客提問紀錄。"
    "請閱讀以下顧客提問清單，歸納出幾個常見主題與重點，用條列式呈現，"
    "並標註每個主題大約出現幾次。不要逐條複述原始問題，只保留有意義的歸納。"
)

_REDUCE_SYSTEM_PROMPT = (
    "你是客服數據分析助理。以下是同一天內、分批整理出來的多份主題摘要，"
    "請把它們合併成一份最終摘要：相同或相似的主題要合併並加總次數，"
    "用條列式呈現最終結果，並在最後加一行「總結」簡短說明今天顧客最關心的重點。"
)


def _chunk(items: list[str], size: int) -> list[list[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _summarize_batch(questions: list[str]) -> str:
    question_list = "\n".join(f"- {q}" for q in questions)
    messages = [
        {"role": "system", "content": _BATCH_SYSTEM_PROMPT},
        {"role": "user", "content": f"顧客提問清單：\n{question_list}"},
    ]
    return llm_generate(messages, max_new_tokens=400)


def _reduce_summaries(batch_summaries: list[str]) -> str:
    combined = "\n\n".join(f"[第 {i+1} 批摘要]\n{s}" for i, s in enumerate(batch_summaries))
    messages = [
        {"role": "system", "content": _REDUCE_SYSTEM_PROMPT},
        {"role": "user", "content": combined},
    ]
    return llm_generate(messages, max_new_tokens=400)


def summarize_day(date: str) -> dict:
    """date 格式為 YYYY-MM-DD（UTC）。回傳當天提問數量與摘要文字。"""
    questions = get_messages_for_date(date)
    if not questions:
        return {"date": date, "question_count": 0, "summary": "當天沒有使用者提問紀錄。"}

    batches = _chunk(questions, SUMMARY_BATCH_SIZE)
    batch_summaries = [_summarize_batch(b) for b in batches]

    summary = batch_summaries[0] if len(batch_summaries) == 1 else _reduce_summaries(batch_summaries)

    return {"date": date, "question_count": len(questions), "summary": summary}
