"""
測試每家公司的 MCP 金鑰（chatbots.mcp_token）：
- 金鑰不會出現在任何列表／一般回應，只有專用端點能讀出，且要有這家公司的存取權。
- 稽核紀錄只記「有沒有動到金鑰」，不記金鑰內容。
"""
import json

import pytest
from fastapi.testclient import TestClient

from app import accounts_store
from app.main import app

SECRET = "pytest-mcp-secret-value-123"


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_token_is_never_in_list_or_me_responses(client, platform_token, test_chatbot):
    resp = client.put(
        f"/api/admin/chatbots/{test_chatbot['id']}", json={"mcp_token": SECRET}, headers=_auth(platform_token)
    )
    assert resp.status_code == 200
    assert resp.json()["has_mcp_token"] is True

    list_resp = client.get("/api/admin/chatbots", headers=_auth(platform_token))
    me_resp = client.get("/api/auth/me", headers=_auth(platform_token))

    for response in (resp, list_resp, me_resp):
        assert SECRET not in response.text
        assert '"mcp_token"' not in response.text  # 連欄位名稱都不該出現（has_mcp_token 是不同的鍵）
    mine = next(c for c in list_resp.json()["chatbots"] if c["id"] == test_chatbot["id"])
    assert mine["has_mcp_token"] is True


def test_reveal_endpoint_returns_token_for_authorized_account(client, platform_token, test_chatbot):
    client.put(f"/api/admin/chatbots/{test_chatbot['id']}", json={"mcp_token": SECRET}, headers=_auth(platform_token))

    resp = client.get(f"/api/admin/chatbots/{test_chatbot['id']}/mcp-token", headers=_auth(platform_token))

    assert resp.status_code == 200
    assert resp.json() == {"mcp_token": SECRET}


def test_reveal_endpoint_forbidden_for_unbound_tenant(client, test_chatbot):
    accounts_store.update_chatbot(test_chatbot["id"], None, None, mcp_token=SECRET)
    tenant = accounts_store.create_account("pytest_token_unbound@example.com", "tenant_primary", None)
    token = accounts_store.create_session(tenant["id"])
    try:
        resp = client.get(f"/api/admin/chatbots/{test_chatbot['id']}/mcp-token", headers=_auth(token))
        assert resp.status_code == 403
        assert SECRET not in resp.text
    finally:
        accounts_store.delete_account(tenant["id"])


def test_reveal_endpoint_requires_login(client, test_chatbot):
    resp = client.get(f"/api/admin/chatbots/{test_chatbot['id']}/mcp-token")

    assert resp.status_code == 401


def test_bound_tenant_can_reveal_own_token(client, test_chatbot):
    accounts_store.update_chatbot(test_chatbot["id"], None, None, mcp_token=SECRET)
    tenant = accounts_store.create_account("pytest_token_bound@example.com", "tenant_primary", None)
    accounts_store.bind_chatbot(tenant["id"], test_chatbot["id"])
    token = accounts_store.create_session(tenant["id"])
    try:
        resp = client.get(f"/api/admin/chatbots/{test_chatbot['id']}/mcp-token", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["mcp_token"] == SECRET
    finally:
        accounts_store.delete_account(tenant["id"])


def test_update_without_token_keeps_existing_and_empty_string_clears(client, platform_token, test_chatbot):
    chatbot_id = test_chatbot["id"]
    accounts_store.update_chatbot(chatbot_id, None, None, mcp_token=SECRET)

    # 只改名稱、沒帶 mcp_token：金鑰維持不變
    client.put(f"/api/admin/chatbots/{chatbot_id}", json={"name": "改個名字"}, headers=_auth(platform_token))
    assert accounts_store.get_chatbot_mcp_token(chatbot_id) == SECRET

    # 空字串代表清除
    resp = client.put(f"/api/admin/chatbots/{chatbot_id}", json={"mcp_token": ""}, headers=_auth(platform_token))
    assert resp.json()["has_mcp_token"] is False
    assert accounts_store.get_chatbot_mcp_token(chatbot_id) is None


def test_get_chatbot_mcp_token_is_none_when_never_set(test_chatbot):
    assert accounts_store.get_chatbot_mcp_token(test_chatbot["id"]) is None


def test_audit_log_records_actions_but_never_the_token_value(client, platform_token, test_chatbot):
    chatbot_id = test_chatbot["id"]
    client.put(f"/api/admin/chatbots/{chatbot_id}", json={"mcp_token": SECRET}, headers=_auth(platform_token))
    client.get(f"/api/admin/chatbots/{chatbot_id}/mcp-token", headers=_auth(platform_token))

    entries = accounts_store.list_audit_log_for_chatbot(chatbot_id)

    actions = {e["action"] for e in entries}
    assert {"update_chatbot", "reveal_mcp_token"} <= actions
    assert SECRET not in json.dumps(entries, default=str)
    update_entry = next(e for e in entries if e["action"] == "update_chatbot")
    assert update_entry["detail"]["mcp_token_changed"] is True
