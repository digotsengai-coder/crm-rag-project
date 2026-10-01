"""
共用 Postgres（pgvector 所在的同一個資料庫）SQLAlchemy engine。

原本 app/rag/documents_store.py 自己有一份私有的 _get_engine()；多租戶帳號相關的
app/accounts_store.py 需要連到同一個資料庫（chatbots/accounts/... 跟 kb_documents 同庫），
把 engine 建立邏輯搬來這裡共用，避免兩個模組各自維護一份連線池設定（也避免兩個 process
內 engine 造成不必要的連線數）。
"""
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL

from app.config import settings

_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """整個 process 共用同一個 Engine（含連線池），不要每次呼叫都重新建立。"""
    global _engine
    if _engine is None:
        # 用 URL.create() 組連線字串（不是手動 f-string 拼接）：Supabase 的 pooler
        # user 名稱帶了「.」（例如 postgres.xxxxx），密碼也可能含特殊字元，URL.create()
        # 會自動做必要的 URL 編碼，手動拼字串遇到這些字元會組出錯誤的連線字串。
        # sslmode=require：Supabase（以及大多數雲端 Postgres）要求 TLS 連線，本機
        # docker pgvector 沒有這個限制但加上通常也相容，不用依環境切換。
        url = URL.create(
            "postgresql+psycopg2",
            username=settings.RAG_PG_USER,
            password=settings.RAG_PG_PASSWORD,
            host=settings.RAG_PG_HOST,
            port=settings.RAG_PG_PORT,
            database=settings.RAG_PG_DATABASE,
            query={"sslmode": "require"},
        )
        _engine = create_engine(url)
    return _engine
