"""
知識庫來源（對應提案 #1「顧客查詢產品資訊」的 RAG 知識庫）。

兩類文件都放在 app/data/：
- products_20_quirky.md：20 項產品的行銷文案，用 product_parser.py 的專用規則拆分
  （這份文件有固定的規格條列格式，需要對應的細緻拆分規則）
- warranty_policy.md / return_policy.md / shipping_payment.md / faq.md：保固、退換貨、
  運送付款、常見問題等政策類文件，用 policy_parser.py 的通用 markdown 標題拆分規則

llamaindex 引擎改用 pgvector 後，索引灌入改讀下方 get_seed_sources()，供
app/rag/documents_store.py 的 seed_if_empty() 逐一讀檔解析（原本整批呼叫的
get_all_chunks() 是給已移除的線上 online_engine.py 建索引用，custom 引擎也已退休，
兩者都不再需要，一併移除）。
之後要再加知識庫文件，只要照現有格式新增檔案、在 _POLICY_FILES 加一行即可。
"""
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"

_PRODUCT_FILE = _DATA_DIR / "products_20_quirky.md"

_POLICY_FILES = [
    _DATA_DIR / "warranty_policy.md",
    _DATA_DIR / "return_policy.md",
    _DATA_DIR / "shipping_payment.md",
    _DATA_DIR / "faq.md",
]


def get_seed_sources() -> list[dict]:
    """
    回傳知識庫種子文件的來源清單，供 app/rag/documents_store.py 的 seed_if_empty()
    在 pgvector table 是空的時候（例如第一次接上新資料庫）逐一讀檔灌入索引。

    category 這裡指的是「該用哪個 parser 解析」（product/policy），
    跟 chunk 內容的 category 欄位（例如產品分類、"政策文件"）是不同語意，不要混用。
    """
    sources = [{"source": _PRODUCT_FILE.name, "category": "product", "path": _PRODUCT_FILE}]
    sources.extend(
        {"source": path.name, "category": "policy", "path": path} for path in _POLICY_FILES
    )
    return sources
