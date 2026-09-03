"""
政策類文件（保固/退換貨/運送付款/FAQ）的通用 markdown 拆分 parser。

跟 product_parser.py 不同：這些文件沒有「規格條列」那種固定格式，是一般的標題＋段落文章，
所以拆分規則簡單很多——依 H1（文件標題）/ H2（小節標題）切，每個 H2 小節是一個 chunk，
文字前面補上「文件標題－小節標題：」當前綴，讓片段被單獨檢索出來時還看得出上下文。

輸出格式跟 product_parser.parse_products() 一致，共用同一個 topic/category 欄位，
這樣 custom_engine.py / llamaindex_engine.py 才能把兩種文件的 chunk 混在同一個索引裡，
不用寫兩套建索引邏輯。
"""
import re

_H1_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_H2_SPLIT_PATTERN = re.compile(r"(^##\s+.+$)", re.MULTILINE)


def parse_policy_doc(full_text: str, source: str) -> list[dict]:
    """回傳 [{"text":..., "source":..., "topic":..., "category":..., "product_id":...}, ...]"""
    h1_match = _H1_PATTERN.search(full_text)
    doc_title = h1_match.group(1).strip() if h1_match else source

    parts = _H2_SPLIT_PATTERN.split(full_text)
    chunks = []
    # parts[0] 是第一個 ## 之前的內容（H1 標題等），從 parts[1] 開始才是 (標題, 內容) 成對出現
    for i in range(1, len(parts), 2):
        section_title = parts[i].lstrip("#").strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if not body:
            continue
        chunks.append({
            "text": f"{doc_title}－{section_title}：\n{body}",
            "source": source,
            "topic": f"{doc_title}：{section_title}",
            "category": "政策文件",
            "product_id": "",
        })
    return chunks
