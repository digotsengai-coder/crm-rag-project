"""
產品知識庫來源（對應提案 #1「顧客查詢產品資訊」的 RAG 知識庫）。

原本是寫死在程式碼裡的模擬文件（家電規格手冊/保固政策/FAQ），
現在改成讀取真實的產品行銷文案檔案 app/data/products_20_quirky.md（20 項產品）。
之後要換其他產品資料，把 SOURCE_FILE 換成別的 .md/.txt 檔案路徑即可；
這份文件的語意拆分邏輯在 app/rag/product_parser.py。
"""
from pathlib import Path

SOURCE_FILE = Path(__file__).parent / "data" / "products_20_quirky.md"
SOURCE_NAME = SOURCE_FILE.name


def load_source_text() -> str:
    return SOURCE_FILE.read_text(encoding="utf-8")
