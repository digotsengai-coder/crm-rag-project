"""
期間提問摘要：給管理者看指定週期內使用者都在問什麼的功能。

流程：
1. 從 chat_log 撈出指定日期區間的所有提問（含 response_text，用來輔助判斷「需商家關注」）
2. 問題數量較多時先分批各自分類，避免一次把所有問題塞進 LLM context
   （本地小模型 context 有限，問題一多會爆或品質變差；線上模型 context 較大，
   批次可以拉高，但太大一批品質仍會下降，所以線上模型用 _SUMMARY_BATCH_SIZE_ONLINE，
   本地模型用 SUMMARY_BATCH_SIZE）
3. 每批由 LLM 分成三類，輸出結構化 JSON：
   - categories：跟業務相關、能歸納出重複主題的問題，統計次數（前端畫長條圖用）
   - meaningless_questions：測試訊息、亂打字、與業務無關的閒聊，純備查
   - needs_merchant_attention：問題合理但太獨特無法歸類，或機器人明顯答不出來，逐字列出原文
4. 有多批的話，categories 再做一次 LLM 彙總（合併相似主題、加總次數、產生總結文字）；
   meaningless_questions / needs_merchant_attention 是純 Python 串接，不再經過 LLM，
   避免 LLM 摘要/改寫掉逐字列出的原始問題內容
5. 以「@<MCP 機器人名稱>」開頭的訊息是走 MCP tool 的指令，不走 RAG，內容不代表「查無答案」也不是亂打，
   所以在送 LLM 分類之前就獨立成 mcp_questions，不會進入 categories／無意義／需商家關注
6. needs_merchant_attention 額外用 app.agent.NO_INFO_ANSWER 訊號輔助判斷：只要那則提問
   當時機器人回的是「查無此資訊」，不管 LLM 怎麼分類都強制併入這個清單（dedup），
   不完全依賴 LLM 自己判斷「答不出來」

這是 map-reduce 的簡化版本，資料量大時可以再拆更細；目前先滿足小型客服場景。

LLM 選擇：優先用有設定金鑰的線上 provider（依 _SUMMARY_PROVIDER_PRIORITY 順序），
都沒有設定才 fallback 用本地模型。這樣線上環境（例如只裝了線上 API 依賴、沒裝 torch 的部署）
只要設定好任一組線上金鑰，就不會走到本地模型、也不會因為 torch 沒裝而出錯。
"""
import json

from app import accounts_store
from app.accounts_store import DEFAULT_MCP_TRIGGER_NAME
from app.agent import NO_INFO_ANSWER
from app.chat_log import get_messages_for_range
from app.mcp_chat import parse_mcp_command
from app.providers import generate_with_provider, is_configured

SUMMARY_BATCH_SIZE = 30
_SUMMARY_BATCH_SIZE_ONLINE = 100
_SUMMARY_PROVIDER_PRIORITY = ["google", "anthropic", "openai", "xai"]

_BATCH_SYSTEM_PROMPT = (
    "你是客服數據分析助理，負責幫管理者整理顧客提問紀錄。"
    "請閱讀以下顧客提問清單，把每一則問題分類到以下三種之一：\n"
    "1. categories：跟商品、訂單、客服政策等業務相關，且能歸納出重複主題的問題；"
    "每個主題要列出屬於它的「原始問題文字」（逐字，不要改寫），一則問題只能屬於一個主題\n"
    "2. meaningless_questions：測試訊息、亂打字、無實質語意內容，或與業務完全無關的閒聊"
    "（例如問天氣、問機器人是誰做的）\n"
    "3. needs_merchant_attention：問題本身合理且與業務相關，但太獨特無法歸類到常見主題，"
    "或明顯是顧客沒得到滿意答案的個案；這一類請把「原始問題文字」逐字列出，不要摘要或改寫\n\n"
    "請只輸出 JSON，不要有其他文字或說明，格式如下：\n"
    '{"categories": [{"name": "主題名稱", "questions": ["原文", ...]}], '
    '"meaningless_questions": ["原文", ...], "needs_merchant_attention": ["原文", ...]}'
)

_REDUCE_SYSTEM_PROMPT = (
    "你是客服數據分析助理。以下是同一天內、分批整理出來的多份主題分類統計（JSON 陣列），"
    "請把相同或相似的主題合併，並寫一段簡短總結說明這段期間顧客最關心的重點。\n"
    "merged_from 要逐字列出被合併進來的原始主題名稱（沒有合併就只列它自己）。\n"
    "請只輸出 JSON，不要有其他文字或說明，格式如下：\n"
    '{"categories": [{"name": "合併後主題名稱", "merged_from": ["原始主題名稱", ...]}], "summary": "一段文字總結"}'
)


def _chunk(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _pick_provider() -> str:
    for provider in _SUMMARY_PROVIDER_PRIORITY:
        if is_configured(provider):
            return provider
    return "local"


# 拉高到 1500（原本 400）：fallback 用的本地小模型 openbmb/MiniCPM5-2B 預設用
# enable_thinking=False 關掉思考過程，正常用不到這麼多，拉高只是留安全餘裕
# （見 app/agent.py 的 generate_answer() 同樣理由）。
_SUMMARY_MAX_NEW_TOKENS = 1500

_EMPTY_BATCH_RESULT = {"categories": [], "meaningless_questions": [], "needs_merchant_attention": []}


def _parse_json_response(raw: str) -> dict | None:
    """
    LLM 常會把 JSON 包在 ```json ... ``` 裡，先剝掉再解析。
    解析失敗回傳 None，呼叫端要有 fallback，不能讓整個摘要請求掛掉。
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _normalize_categories(raw_categories: list, batch_questions: list[str]) -> list[dict]:
    """
    只保留「確實出現在這批輸入」的問題原文（擋掉 LLM 改寫或編造），count 以實際問題數為準；
    LLM 沒列出問題時退回它自己給的 count，讓統計不會消失。
    """
    valid = set(batch_questions)
    result = []
    for c in raw_categories:
        if not isinstance(c, dict) or not c.get("name"):
            continue
        questions = _dedup_keep_order([q for q in (c.get("questions") or []) if isinstance(q, str) and q in valid])
        count = len(questions) or int(c.get("count") or 0)
        result.append({"name": c["name"], "count": count, "questions": questions})
    return result


def _classify_batch(questions: list[str], provider: str) -> dict:
    question_list = "\n".join(f"- {q}" for q in questions)
    messages = [
        {"role": "system", "content": _BATCH_SYSTEM_PROMPT},
        {"role": "user", "content": f"顧客提問清單：\n{question_list}"},
    ]
    raw = generate_with_provider(provider, messages, max_new_tokens=_SUMMARY_MAX_NEW_TOKENS)
    parsed = _parse_json_response(raw)
    if parsed is None:
        # 解析失敗：不要讓這批問題憑空消失，全部歸進一個「未分類」主題，
        # 至少 question_count 對得上、管理者知道有資料但分類失敗。
        print(f"[Summary] 批次分類 JSON 解析失敗，原始輸出：{raw[:200]}")
        return {
            "categories": [{"name": "未分類（分類失敗）", "count": len(questions), "questions": list(questions)}],
            "meaningless_questions": [],
            "needs_merchant_attention": [],
        }
    return {
        "categories": _normalize_categories(parsed.get("categories") or [], questions),
        "meaningless_questions": parsed.get("meaningless_questions") or [],
        "needs_merchant_attention": parsed.get("needs_merchant_attention") or [],
    }


def _reduce_categories(batch_categories: list[list[dict]], provider: str) -> tuple[list[dict], str]:
    # 只把主題名稱與次數送給 LLM 合併；問題原文由 Python 依 merged_from 對回去，
    # LLM 不經手原文，避免被摘要或改寫。
    stats = [[{"name": c["name"], "count": c["count"]} for c in batch] for batch in batch_categories]
    combined = json.dumps(stats, ensure_ascii=False)
    messages = [
        {"role": "system", "content": _REDUCE_SYSTEM_PROMPT},
        {"role": "user", "content": f"各批次的主題分類統計：\n{combined}"},
    ]
    raw = generate_with_provider(provider, messages, max_new_tokens=_SUMMARY_MAX_NEW_TOKENS)
    parsed = _parse_json_response(raw)
    flattened = [c for batch in batch_categories for c in batch]
    if parsed is None:
        print(f"[Summary] 彙總 JSON 解析失敗，原始輸出：{raw[:200]}")
        # fallback：不合併相似主題，直接把各批類別攤平回傳，至少不丟資料。
        return flattened, "彙總摘要時發生格式錯誤，以下為未合併的分類統計。"

    by_name: dict[str, dict] = {}
    for c in flattened:
        entry = by_name.setdefault(c["name"], {"count": 0, "questions": []})
        entry["count"] += c["count"]
        entry["questions"] = _dedup_keep_order(entry["questions"] + c["questions"])

    merged, used = [], set()
    for m in parsed.get("categories") or []:
        if not isinstance(m, dict) or not m.get("name"):
            continue
        sources = [n for n in (m.get("merged_from") or [m["name"]]) if n in by_name and n not in used]
        if not sources:
            continue
        used.update(sources)
        questions = _dedup_keep_order([q for n in sources for q in by_name[n]["questions"]])
        count = len(questions) or sum(by_name[n]["count"] for n in sources)
        merged.append({"name": m["name"], "count": count, "questions": questions})
    # LLM 漏掉的原始主題不能憑空消失，原樣補回。
    for name, entry in by_name.items():
        if name not in used:
            merged.append({"name": name, **entry})
    return merged, parsed.get("summary") or ""


def _dedup_keep_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def summarize_period(start_date: str, end_date: str, chatbot_id: str) -> dict:
    """日期格式為 YYYY-MM-DD（UTC）。回傳指定公司在此區間的提問摘要。"""
    rows = get_messages_for_range(start_date, end_date, chatbot_id)
    if not rows:
        return {
            "start_date": start_date,
            "end_date": end_date,
            "question_count": 0,
            "summary": "這個週期沒有使用者提問紀錄。",
        }

    # 觸發名稱是各公司自訂的（查不到公司時用預設名稱，與 /api/chat 的分流一致）。
    chatbot = accounts_store.get_chatbot(chatbot_id)
    trigger_name = chatbot["mcp_trigger_name"] if chatbot else DEFAULT_MCP_TRIGGER_NAME
    mcp_questions = [
        r["message"] for r in rows if parse_mcp_command(r["message"], trigger_name) is not None
    ]
    normal_rows = [r for r in rows if parse_mcp_command(r["message"], trigger_name) is None]

    questions = [r["message"] for r in normal_rows]
    # 機器人當時回「查無此資訊」的提問：不管 LLM 怎麼分類，都強制併入「需商家關注」。
    no_info_questions = [
        r["message"] for r in normal_rows if (r["response_text"] or "").strip() == NO_INFO_ANSWER
    ]

    # 全部都是 MCP 訊息時沒有需要分類的提問，不必呼叫 LLM。
    if not questions:
        return {
            "start_date": start_date,
            "end_date": end_date,
            "question_count": len(rows),
            "categories": [],
            "meaningless_questions": [],
            "needs_merchant_attention": [],
            "mcp_questions": _dedup_keep_order(mcp_questions),
            "summary": "這個週期的提問都是 MCP 指令，沒有能歸納出常見主題的一般提問。",
        }

    provider = _pick_provider()
    batch_size = _SUMMARY_BATCH_SIZE_ONLINE if provider != "local" else SUMMARY_BATCH_SIZE
    batches = _chunk(questions, batch_size)
    batch_results = [_classify_batch(b, provider) for b in batches] if batches else [_EMPTY_BATCH_RESULT]

    meaningless_questions = _dedup_keep_order(
        [q for r in batch_results for q in r["meaningless_questions"]]
    )
    needs_merchant_attention = _dedup_keep_order(
        [q for r in batch_results for q in r["needs_merchant_attention"]] + no_info_questions
    )
    # 強制列表優先：一則問題不該同時出現在「無意義」跟「需商家關注」——後者訊號更明確可信。
    meaningless_questions = [q for q in meaningless_questions if q not in needs_merchant_attention]

    batch_category_lists = [r["categories"] for r in batch_results]
    if len(batch_results) == 1:
        categories, summary = batch_category_lists[0], _default_summary(batch_category_lists[0])
    else:
        categories, summary = _reduce_categories(batch_category_lists, provider)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "question_count": len(rows),
        "categories": categories,
        "meaningless_questions": meaningless_questions,
        "needs_merchant_attention": needs_merchant_attention,
        "mcp_questions": _dedup_keep_order(mcp_questions),
        "summary": summary,
    }


def _default_summary(categories: list[dict]) -> str:
    """只有一批時不需要呼叫 LLM 做彙總，直接用分類統計拼出一句總結。"""
    if not categories:
        return "這段期間沒有能歸納出常見主題的提問。"
    top = sorted(categories, key=lambda c: c.get("count", 0), reverse=True)[:3]
    names = "、".join(c.get("name", "") for c in top)
    return f"這段期間顧客最關心的主題是：{names}。"
