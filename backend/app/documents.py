"""
知識庫來源（對應提案 #1「顧客查詢產品資訊」的 RAG 知識庫）。

兩類文件都放在 app/data/：
- products_20_quirky.md：20 項產品的行銷文案，用 product_parser.py 的專用規則拆分
  （這份文件有固定的規格條列格式，需要對應的細緻拆分規則）
- warranty_policy.md / return_policy.md / shipping_payment.md / faq.md：保固、退換貨、
  運送付款、常見問題等政策類文件，用 policy_parser.py 的通用 markdown 標題拆分規則

get_all_chunks() 把兩類文件的 chunk 合併成一份清單，是 custom_engine.py 跟 llamaindex_engine.py
建索引時共用的唯一資料來源——兩套引擎都呼叫同一個函式，不會有邏輯不一致的風險。
之後要再加知識庫文件，只要照現有格式新增檔案、在 _POLICY_FILES 加一行即可。
"""
from pathlib import Path

from app.rag.product_parser import parse_products
from app.rag.policy_parser import parse_policy_doc

_DATA_DIR = Path(__file__).parent / "data"

_PRODUCT_FILE = _DATA_DIR / "products_20_quirky.md"

_POLICY_FILES = [
    _DATA_DIR / "warranty_policy.md",
    _DATA_DIR / "return_policy.md",
    _DATA_DIR / "shipping_payment.md",
    _DATA_DIR / "faq.md",
]


def get_all_chunks() -> list[dict]:
    chunks = parse_products(_PRODUCT_FILE.read_text(encoding="utf-8"), source=_PRODUCT_FILE.name)
    for path in _POLICY_FILES:
        chunks.extend(parse_policy_doc(path.read_text(encoding="utf-8"), source=path.name))
    return chunks
