"""
每家公司的 RAG 檢索設定（chatbots.rag_top_k／rerank_enabled）：
- 預設 k=5、rerank 關閉。
- 後台可以調整 k；rerank 只有在「伺服器支援」時才能開啟，關閉任何環境都允許。
- 聊天流程會把公司的設定傳給 agent；資料庫裡存了 rerank=true 但伺服器不支援（例如 Cloud Run）
  時，檢索層靜默退回一般向量檢索，見 test_reranker.py。
"""
import pytest
from fastapi.testclient import TestClient

from app import accounts_store
from app.main import app
from app.rag import reranker


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _put(client, token, chatbot_id, body):
    return client.put(f"/api/admin/chatbots/{chatbot_id}", json=body, headers=_auth(token))


def test_new_chatbot_defaults_to_k5_and_rerank_off(test_chatbot):
    assert test_chatbot["rag_top_k"] == 5
    assert test_chatbot["rerank_enabled"] is False


def test_update_rag_top_k_is_persisted_and_returned(client, platform_token, test_chatbot):
    resp = _put(client, platform_token, test_chatbot["id"], {"rag_top_k": 8})

    assert resp.status_code == 200
    assert resp.json()["rag_top_k"] == 8
    assert accounts_store.get_chatbot(test_chatbot["id"])["rag_top_k"] == 8
    listed = client.get("/api/admin/chatbots", headers=_auth(platform_token)).json()["chatbots"]
    assert next(c for c in listed if c["id"] == test_chatbot["id"])["rag_top_k"] == 8


@pytest.mark.parametrize("bad", [0, -1, 11, 100])
def test_rag_top_k_out_of_range_is_rejected(client, platform_token, test_chatbot, bad):
    resp = _put(client, platform_token, test_chatbot["id"], {"rag_top_k": bad})

    assert resp.status_code == 422


def test_update_without_rag_fields_keeps_them(client, platform_token, test_chatbot):
    _put(client, platform_token, test_chatbot["id"], {"rag_top_k": 7})

    resp = _put(client, platform_token, test_chatbot["id"], {"name": "Pytest Renamed"})

    assert resp.status_code == 200
    assert resp.json()["rag_top_k"] == 7


def test_enabling_rerank_is_rejected_when_server_does_not_support_it(client, platform_token, test_chatbot, monkeypatch):
    monkeypatch.setattr(reranker, "is_supported", lambda: False)

    resp = _put(client, platform_token, test_chatbot["id"], {"rerank_enabled": True})

    assert resp.status_code == 400
    assert accounts_store.get_chatbot(test_chatbot["id"])["rerank_enabled"] is False


def test_rerank_can_be_enabled_then_disabled_when_supported(client, platform_token, test_chatbot, monkeypatch):
    monkeypatch.setattr(reranker, "is_supported", lambda: True)

    on = _put(client, platform_token, test_chatbot["id"], {"rerank_enabled": True})
    assert on.status_code == 200 and on.json()["rerank_enabled"] is True
    assert on.json()["rerank_available"] is True

    off = _put(client, platform_token, test_chatbot["id"], {"rerank_enabled": False})
    assert off.status_code == 200 and off.json()["rerank_enabled"] is False


def test_disabling_rerank_is_always_allowed_even_if_server_cannot_rerank(client, platform_token, test_chatbot, monkeypatch):
    # 本機與正式共用資料庫：本機開啟後，在不支援的環境仍要能把它關掉
    accounts_store.update_chatbot(test_chatbot["id"], None, None, rerank_enabled=True)
    monkeypatch.setattr(reranker, "is_supported", lambda: False)

    resp = _put(client, platform_token, test_chatbot["id"], {"rerank_enabled": False})

    assert resp.status_code == 200
    assert resp.json()["rerank_enabled"] is False
    assert resp.json()["rerank_available"] is False


def test_rerank_available_is_reported_in_me_response(client, platform_token, test_chatbot, monkeypatch):
    monkeypatch.setattr(reranker, "is_supported", lambda: False)

    me = client.get("/api/auth/me", headers=_auth(platform_token)).json()

    assert all(c["rerank_available"] is False for c in me["chatbots"])


def test_chat_passes_chatbot_settings_to_agent(client, test_chatbot, monkeypatch):
    from app import main as main_module

    accounts_store.update_chatbot(test_chatbot["id"], None, None, rag_top_k=7, rerank_enabled=True)
    seen = {}

    class FakeAgent:
        def generate_answer(self, text, history=None, provider="google", chatbot_id=None, top_k=None, use_rerank=False):
            seen.update(top_k=top_k, use_rerank=use_rerank, chatbot_id=chatbot_id)
            return "ok", []

    monkeypatch.setattr(main_module, "get_agent", lambda: FakeAgent())

    resp = client.post(
        "/api/chat",
        json={"message": "無線滑鼠支援多少 DPI？", "history": [], "provider": "google"},
        headers={"X-Client-ID": test_chatbot["id"]},
    )

    assert resp.status_code == 200
    assert seen == {"top_k": 7, "use_rerank": True, "chatbot_id": test_chatbot["id"]}


def test_chat_uses_defaults_when_chatbot_not_found(client, monkeypatch):
    from app import main as main_module

    seen = {}

    class FakeAgent:
        def generate_answer(self, text, history=None, provider="google", chatbot_id=None, top_k=None, use_rerank=False):
            seen.update(top_k=top_k, use_rerank=use_rerank)
            return "ok", []

    monkeypatch.setattr(main_module, "get_agent", lambda: FakeAgent())

    resp = client.post(
        "/api/chat",
        json={"message": "hi", "history": [], "provider": "google"},
        headers={"X-Client-ID": "not-a-uuid"},
    )

    assert resp.status_code == 200
    # top_k=None → 檢索層用系統預設 5；rerank 關閉
    assert seen == {"top_k": None, "use_rerank": False}
