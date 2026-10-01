"""
測試共用設定。

兩個重點：
1. 把 backend 目錄加進 sys.path 並 chdir 過去，讓 `import app...` 這類相對路徑的行為，跟 `run_dev.sh`（cd 進 backend 再啟動）一致，
   不管實際從哪個目錄執行 pytest 都一樣。
2. 對話紀錄（chat_log）已改存 Postgres，與帳號／pgvector 測試共用同一個資料庫，
   跑測試前需確認 RAG_PG_* 連得上。
"""
import os
import sys
import uuid
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

os.chdir(BACKEND_DIR)

# 多租戶帳號測試共用 helper：直接透過 accounts_store 建帳號/session（不透過真的 Google
# 登入流程——pytest 沒辦法真的拿到一個有效的 Google ID token，Google 驗證本身用
# monkeypatch app.auth.verify_google_id_token 在 test_auth.py 個別測試），
# 跟 documents_api／chatbots／accounts 測試共用同一套 fixture，統一在這裡定義避免重複。


def _unique_email(prefix: str = "pytest") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture
def platform_account():
    """建立一個 platform_primary 帳號，測試結束後刪除（連帶清掉 session，見 accounts_store）。"""
    from app import accounts_store

    account = accounts_store.create_account(_unique_email("platform"), "platform_primary", None)
    yield account
    accounts_store.delete_account(account["id"])


@pytest.fixture
def platform_token(platform_account):
    """platform_account 的登入 session token，供 Authorization: Bearer 使用。"""
    from app import accounts_store

    return accounts_store.create_session(platform_account["id"])


@pytest.fixture
def test_chatbot(request):
    """
    建立一家測試用公司，測試結束後硬刪除（含清掉該公司的 RAG 文件記錄與向量 chunk）。

    支援用 @pytest.mark.parametrize 或 indirect fixture 的方式帶入 mcp_url（需要一家
    「有設定 mcp_url」的公司時）；沒有額外參數時預設 mcp_url=None，對應「公司沒開 MCP 功能」的情境。
    """
    from app import accounts_store
    from app.rag.documents_store import purge_chatbot
    from app.rag.engine import get_retriever

    mcp_url = getattr(request, "param", None)
    chatbot = accounts_store.create_chatbot(f"Pytest Chatbot {uuid.uuid4().hex[:8]}", mcp_url)
    yield chatbot
    accounts_store.delete_chatbot(chatbot["id"])
    try:
        purge_chatbot(chatbot["id"], get_retriever().index)
    except Exception:
        pass
