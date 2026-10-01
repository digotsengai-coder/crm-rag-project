"""
對話紀錄：把每次 /api/chat 問答存進 Postgres，作為「管理者摘要提問」功能的資料來源。

原本存本機 SQLite 檔，但 Cloud Run 容器檔案系統是暫時的，重啟或重新部署就會清空、多實例也各寫各的；
改用與 pgvector／帳號資料同一個 Postgres（app/db.py 的共用 engine），資料才會持久且跨實例共用。
"""
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.db import get_engine

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS chat_log (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL,
        client_ip TEXT,
        message TEXT NOT NULL,
        response_type TEXT NOT NULL,
        response_text TEXT,
        chatbot_id TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_chat_log_created_at ON chat_log (created_at)",
    "CREATE INDEX IF NOT EXISTS idx_chat_log_chatbot_id ON chat_log (chatbot_id, created_at)",
    # @mcp 對話中 LLM 實際呼叫過的 MCP tool（稽核用：哪家公司、呼叫了哪個 tool、帶了什麼參數）。
    # 只記參數，不記 tool 回傳內容（回傳可能含顧客資料）。arguments 是 JSON 字串。
    """
    CREATE TABLE IF NOT EXISTS mcp_tool_log (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL,
        chatbot_id TEXT,
        tool_name TEXT NOT NULL,
        arguments TEXT NOT NULL,
        is_error INTEGER NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_mcp_tool_log_chatbot_id ON mcp_tool_log (chatbot_id, created_at)",
)

_schema_ready = False


def _ensure_schema() -> None:
    """建表為冪等（IF NOT EXISTS）；每個 process 只跑一次，避免每次寫入都多一趟往返。"""
    global _schema_ready
    if _schema_ready:
        return
    with get_engine().begin() as conn:
        for stmt in _SCHEMA_STATEMENTS:
            conn.execute(text(stmt))
    _schema_ready = True


def init_db():
    _ensure_schema()


def log_chat(
    message: str, response_type: str, response_text: str | None, client_ip: str | None,
    chatbot_id: str | None = None,
):
    """寫入失敗不應該影響聊天功能本身，呼叫端負責 try/except。"""
    _ensure_schema()
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "INSERT INTO chat_log (created_at, client_ip, message, response_type, response_text, chatbot_id) "
                "VALUES (:created_at, :client_ip, :message, :response_type, :response_text, :chatbot_id)"
            ),
            {
                "created_at": datetime.now(timezone.utc),
                "client_ip": client_ip,
                "message": message,
                "response_type": response_type,
                "response_text": response_text,
                "chatbot_id": chatbot_id,
            },
        )


def log_tool_calls(chatbot_id: str | None, tool_calls) -> None:
    """
    記錄一次 @mcp 對話裡 LLM 呼叫過的每個 tool。
    寫入失敗不應該影響聊天功能本身，呼叫端負責 try/except。
    """
    if not tool_calls:
        return
    _ensure_schema()
    now = datetime.now(timezone.utc)
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "INSERT INTO mcp_tool_log (created_at, chatbot_id, tool_name, arguments, is_error) "
                "VALUES (:created_at, :chatbot_id, :tool_name, :arguments, :is_error)"
            ),
            [
                {
                    "created_at": now,
                    "chatbot_id": chatbot_id,
                    "tool_name": c.name,
                    "arguments": json.dumps(c.arguments, ensure_ascii=False),
                    "is_error": int(c.is_error),
                }
                for c in tool_calls
            ],
        )


def get_tool_calls_for_chatbot(chatbot_id: str, limit: int = 100) -> list[dict]:
    _ensure_schema()
    with get_engine().connect() as conn:
        rows = conn.execute(
            text(
                "SELECT created_at, tool_name, arguments, is_error FROM mcp_tool_log "
                "WHERE chatbot_id = :chatbot_id ORDER BY id DESC LIMIT :limit"
            ),
            {"chatbot_id": chatbot_id, "limit": limit},
        ).fetchall()
    return [
        {"created_at": r[0].isoformat(), "tool_name": r[1], "arguments": json.loads(r[2]), "is_error": bool(r[3])}
        for r in rows
    ]


def get_messages_for_range(start_date: str, end_date: str, chatbot_id: str) -> list[dict]:
    """
    取得指定 UTC 日期區間（YYYY-MM-DD，含起日與結束日）、指定公司所有使用者提問，依時間排序。
    chatbot_id 必填——摘要依公司隔離，不提供全域彙總（避免看到其他公司的顧客提問內容）。

    同時回傳 response_text：summary.py 用它判斷機器人當時是不是回「查無此資訊」
    （app.agent.NO_INFO_ANSWER），藉此輔助分類「需商家關注」的問題，不用完全依賴 LLM 自己判斷。
    """
    start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_exclusive = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    _ensure_schema()
    with get_engine().connect() as conn:
        rows = conn.execute(
            text(
                "SELECT message, response_text FROM chat_log "
                "WHERE created_at >= :start AND created_at < :end AND chatbot_id = :chatbot_id "
                "ORDER BY created_at"
            ),
            {"start": start, "end": end_exclusive, "chatbot_id": chatbot_id},
        ).fetchall()
    return [{"message": row[0], "response_text": row[1]} for row in rows]
