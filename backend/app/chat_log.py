"""
對話紀錄：把每次 /api/chat 問答存進 SQLite，作為未來「管理者摘要當日提問」功能的資料來源。

先用 SQLite（單檔案，不需要額外服務），流量大到需要多台伺服器共用時再換 Postgres 等方案。
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    client_ip TEXT,
    message TEXT NOT NULL,
    response_type TEXT NOT NULL,
    response_text TEXT
);
CREATE INDEX IF NOT EXISTS idx_chat_log_created_at ON chat_log (created_at);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(settings.CHAT_LOG_DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        conn.commit()


def log_chat(message: str, response_type: str, response_text: str | None, client_ip: str | None):
    """寫入失敗不應該影響聊天功能本身，呼叫端負責 try/except。"""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO chat_log (created_at, client_ip, message, response_type, response_text) "
            "VALUES (?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), client_ip, message, response_type, response_text),
        )
        conn.commit()


def get_messages_for_date(date: str) -> list[str]:
    """取得指定日期（YYYY-MM-DD，UTC）當天所有使用者提問的原始文字，依時間排序。"""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT message FROM chat_log WHERE created_at LIKE ? ORDER BY created_at",
            (f"{date}%",),
        ).fetchall()
    return [row[0] for row in rows]
