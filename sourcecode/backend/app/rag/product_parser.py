"""
產品行銷文案（products_20_quirky.md）專用的語意拆分 parser。

這份文件是 markdown 格式：`---` 分隔 20 個產品區塊，每個區塊有標題、行銷段落、`- **規格：** 內容` 條列，
外加一個「🔮 奇特彩蛋」條列，文末還有一份「產品對應總表」給 product_id。

拆分原則（語意單位 = 一個 chunk）：
- 行銷介紹段落 -> 一個 chunk（適合「介紹一下 XX」這種開放式問題）
- 每一條規格 -> 各自一個 chunk（適合問特定規格，例如「續航多久」）
- 奇特彩蛋 -> 一個 chunk（適合「有什麼特別/隱藏功能」）
每個 chunk 文字前面都補上「產品名稱（分類）— 」當前綴，讓 chunk 被單獨檢索出來時，
LLM 也知道在講哪個產品；metadata 額外帶 topic / category / product_id，方便未來篩選。
topic 欄位是通用命名（跟政策文件 policy_parser.py 共用同一套 chunk 格式），這裡的值就是產品名稱。
"""
import re

_HEADER_PATTERN = re.compile(
    r"^##\s*\d+\.\s*(?P<name_en>[^（]+)（(?P<name_zh>[^）]+)）\s*—\s*(?P<category>.+)$",
    re.MULTILINE,
)
_QUIRKY_PATTERN = re.compile(r"^-\s*🔮\s*\*\*奇特彩蛋：\*\*\s*(?P<content>.+)$", re.MULTILINE)
_SPEC_PATTERN = re.compile(r"^-\s*\*\*(?P<label>[^*]+?)：\*\*\s*(?P<content>.+)$", re.MULTILINE)
_TABLE_ROW_PATTERN = re.compile(
    r"^\|\s*\d+\s*\|\s*(?P<name_en>[^|]+?)\s*\|\s*(?P<category>[^|]+?)\s*\|\s*(?P<product_id>\d+)\s*\|$",
    re.MULTILINE,
)


def _parse_product_id_map(full_text: str) -> dict:
    """從文末的「產品對應總表」解析 英文產品名稱 -> product_id。"""
    return {
        m.group("name_en").strip(): m.group("product_id").strip()
        for m in _TABLE_ROW_PATTERN.finditer(full_text)
    }


def parse_products(full_text: str, source: str) -> list[dict]:
    """回傳 [{"text":..., "source":..., "topic":..., "category":..., "product_id":...}, ...]"""
    id_map = _parse_product_id_map(full_text)

    # 用 --- 切出每個產品區塊（第一段是檔案開頭的說明文字，最後一段是總表，都不是產品內容）
    blocks = re.split(r"^---\s*$", full_text, flags=re.MULTILINE)

    chunks = []
    for block in blocks:
        header_match = _HEADER_PATTERN.search(block)
        if not header_match:
            continue  # 不是產品區塊（開頭說明或文末總表），略過

        name_en = header_match.group("name_en").strip()
        name_zh = header_match.group("name_zh").strip()
        category = header_match.group("category").strip()
        topic = f"{name_en}（{name_zh}）"
        product_id = id_map.get(name_en)
        prefix = f"{name_en}（{name_zh}，{category}）— "

        def add_chunk(text: str):
            chunks.append({
                "text": prefix + text.strip(),
                "source": source,
                "topic": topic,
                "category": category,
                "product_id": product_id or "",
            })

        # 行銷介紹段落：標題行之後、第一個條列符號之前的那段文字
        after_header = block[header_match.end():]
        intro_match = re.match(r"\s*(?P<intro>[^\n]+(?:\n(?!-)[^\n]+)*)", after_header)
        if intro_match:
            intro = intro_match.group("intro").strip()
            if intro:
                add_chunk(intro)

        # 規格條列（排除奇特彩蛋那一行，它有自己的格式）
        for spec_match in _SPEC_PATTERN.finditer(block):
            add_chunk(f"{spec_match.group('label').strip()}：{spec_match.group('content').strip()}")

        # 奇特彩蛋
        quirky_match = _QUIRKY_PATTERN.search(block)
        if quirky_match:
            add_chunk(f"特別功能：{quirky_match.group('content').strip()}")

    return chunks
