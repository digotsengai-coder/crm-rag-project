"""
訂單資料（對應提案 #2「顧客查詢訂單」的資料來源）。

原本是寫死在程式碼裡的 MOCK_ORDERS dict，現在改成存在 SQLite（orders.db），
啟動時若資料庫是空的會自動灌入幾筆範例資料。
之後要接真實訂單系統／ERP，只要把 get_order() 內部改成呼叫外部 API 或查詢正式資料庫即可，
main.py 呼叫 get_order() 的介面完全不需要改。

status 對應前端時間軸的階段索引：
  0 = 已下單, 1 = 備貨出貨, 2 = 配送中, 3 = 已送達
"""
import sqlite3
from contextlib import contextmanager

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    code TEXT PRIMARY KEY,
    status INTEGER NOT NULL,
    eta TEXT NOT NULL,
    items TEXT NOT NULL
);
"""

# 範例資料，模擬真實訂單系統裡會有的紀錄
_SEED_ORDERS = [
    ("A12345", 2, "8月28日", "智慧掃地機器人 R5 Pro ×1"),
    ("B98231", 0, "9月5日", "智慧冷氣 A8（1.5噸）×1"),
    ("C55210", 3, "已送達", "智慧電視 V6 55吋 ×1"),
    ("D77102", 1, "9月8日", "智慧掃地機器人 R5 Pro ×2、智慧電視 V6 43吋 ×1"),
    ("E30044", 2, "9月4日", "智慧冷氣 A8（2.2噸）×1"),
]


@contextmanager
def _connect():
    conn = sqlite3.connect(settings.ORDERS_DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO orders (code, status, eta, items) VALUES (?, ?, ?, ?)",
                _SEED_ORDERS,
            )
        conn.commit()


def get_order(code: str):
    with _connect() as conn:
        row = conn.execute(
            "SELECT status, eta, items FROM orders WHERE code = ?",
            (code.upper(),),
        ).fetchone()
    if row is None:
        return None
    status, eta, items = row
    return {"status": status, "eta": eta, "items": items}
