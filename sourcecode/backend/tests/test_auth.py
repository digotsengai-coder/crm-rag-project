"""
測試多租戶帳號：Google 登入、session、RBAC（require_session/require_platform_role/
require_chatbot_access）、/api/admin/chatbots、/api/admin/accounts。

Google ID token 驗證用 monkeypatch app.auth.verify_google_id_token 繞過（pytest 沒辦法真的
拿到一個有效的 Google ID token），只測我們自己這一段登入/session/RBAC 邏輯。
"""
import pytest
from fastapi.testclient import TestClient

from app import accounts_store
from app.main import app, _chatbot_request_log, _request_log


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _request_log.clear()
    _chatbot_request_log.clear()
    yield
    _request_log.clear()
    _chatbot_request_log.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_google_login_unknown_email_self_registers_as_tenant_primary(client, monkeypatch):
    """未知 email 首次登入要自動建立 tenant_primary 帳號（商家自助註冊），不是回 403。"""
    email = "nobody_pytest@example.com"
    monkeypatch.setattr("app.auth.verify_google_id_token", lambda token: email)

    resp = client.post("/api/auth/google", json={"id_token": "fake-token"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["account"]["email"] == email
    assert body["account"]["role"] == "tenant_primary"
    assert body["token"]

    account = accounts_store.get_account_by_email(email)
    assert account is not None
    accounts_store.delete_account(account["id"])


def test_google_login_known_email_returns_session_token(client, monkeypatch, platform_account):
    monkeypatch.setattr("app.auth.verify_google_id_token", lambda token: platform_account["email"])

    resp = client.post("/api/auth/google", json={"id_token": "fake-token"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["account"]["email"] == platform_account["email"]
    assert body["account"]["role"] == "platform_primary"
    assert body["token"]

    # 拿到的 token 應該能直接用在 /api/auth/me
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["account"]["email"] == platform_account["email"]


def test_me_without_authorization_header_returns_401(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_invalid_token_returns_401(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_logout_revokes_session(client, platform_account):
    token = accounts_store.create_session(platform_account["id"])
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    logout_resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200

    after_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert after_resp.status_code == 401


def test_delete_account_immediately_revokes_its_sessions():
    """移除帳號要立刻讓對方的 session 失效（不是等 token 自然過期），靠 ON DELETE CASCADE。"""
    account = accounts_store.create_account("pytest_revoke_target@example.com", "platform_secondary", None)
    token = accounts_store.create_session(account["id"])
    assert accounts_store.get_account_by_session(token) is not None

    accounts_store.delete_account(account["id"])

    assert accounts_store.get_account_by_session(token) is None


class TestChatbotAccess:
    """require_chatbot_access：platform 帳號可跨公司、tenant 帳號跨公司會 403、同公司可通過。"""

    def test_platform_account_can_access_any_chatbot(self, client, platform_token, test_chatbot):
        resp = client.get(
            "/api/admin/documents",
            params={"chatbot_id": test_chatbot["id"]},
            headers={"Authorization": f"Bearer {platform_token}"},
        )
        assert resp.status_code == 200

    def test_tenant_account_without_binding_gets_403(self, client, test_chatbot):
        tenant = accounts_store.create_account("pytest_tenant_unbound@example.com", "tenant_primary", None)
        token = accounts_store.create_session(tenant["id"])
        try:
            resp = client.get(
                "/api/admin/documents",
                params={"chatbot_id": test_chatbot["id"]},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403
        finally:
            accounts_store.delete_account(tenant["id"])

    def test_tenant_account_with_binding_can_access(self, client, test_chatbot):
        tenant = accounts_store.create_account("pytest_tenant_bound@example.com", "tenant_primary", None)
        accounts_store.bind_chatbot(tenant["id"], test_chatbot["id"])
        token = accounts_store.create_session(tenant["id"])
        try:
            resp = client.get(
                "/api/admin/documents",
                params={"chatbot_id": test_chatbot["id"]},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
        finally:
            accounts_store.delete_account(tenant["id"])

    def test_missing_authorization_header_returns_401_not_403(self, client, test_chatbot):
        """完全沒帶 token：應該是 401（沒登入），不是 403（有登入但沒權限），錯誤語意要分清楚。"""
        resp = client.get("/api/admin/documents", params={"chatbot_id": test_chatbot["id"]})
        assert resp.status_code == 401


class TestChatbotsApi:
    def test_tenant_account_can_self_create_chatbot_and_gets_bound(self, client, test_chatbot):
        """商家帳號自助新增企業服務：建立成功、且自動綁定成為這家新公司的帳號。"""
        tenant = accounts_store.create_account("pytest_tenant_create@example.com", "tenant_primary", None)
        accounts_store.bind_chatbot(tenant["id"], test_chatbot["id"])
        token = accounts_store.create_session(tenant["id"])
        try:
            resp = client.post(
                "/api/admin/chatbots",
                json={"name": "商家自建的公司"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            new_chatbot_id = resp.json()["id"]
            assert accounts_store.account_has_chatbot_access(tenant, new_chatbot_id)
        finally:
            accounts_store.delete_chatbot(resp.json()["id"])
            accounts_store.delete_account(tenant["id"])

    def test_platform_account_creates_chatbot_and_lists_it(self, client, platform_token):
        create_resp = client.post(
            "/api/admin/chatbots",
            json={"name": "Pytest 測試商家", "mcp_url": "https://example.com/mcp"},
            headers={"Authorization": f"Bearer {platform_token}"},
        )
        assert create_resp.status_code == 200
        chatbot = create_resp.json()
        assert chatbot["name"] == "Pytest 測試商家"
        assert chatbot["mcp_url"] == "https://example.com/mcp"

        try:
            list_resp = client.get(
                "/api/admin/chatbots", headers={"Authorization": f"Bearer {platform_token}"}
            )
            assert list_resp.status_code == 200
            ids = [c["id"] for c in list_resp.json()["chatbots"]]
            assert chatbot["id"] in ids
        finally:
            accounts_store.delete_chatbot(chatbot["id"])

    def test_tenant_account_only_sees_bound_chatbots(self, client, test_chatbot):
        other = accounts_store.create_chatbot("Pytest 不該看到的公司", None)
        tenant = accounts_store.create_account("pytest_tenant_visibility@example.com", "tenant_primary", None)
        accounts_store.bind_chatbot(tenant["id"], test_chatbot["id"])
        token = accounts_store.create_session(tenant["id"])
        try:
            resp = client.get("/api/admin/chatbots", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            ids = {c["id"] for c in resp.json()["chatbots"]}
            assert test_chatbot["id"] in ids
            assert other["id"] not in ids
        finally:
            accounts_store.delete_account(tenant["id"])
            accounts_store.delete_chatbot(other["id"])

    def test_bound_tenant_can_delete_own_chatbot(self, client, test_chatbot):
        """商家帳號能刪除自己綁定的公司（自助建立公司後也要能自助刪除）。"""
        tenant = accounts_store.create_account("pytest_tenant_delete@example.com", "tenant_primary", None)
        accounts_store.bind_chatbot(tenant["id"], test_chatbot["id"])
        token = accounts_store.create_session(tenant["id"])
        try:
            resp = client.delete(
                f"/api/admin/chatbots/{test_chatbot['id']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert accounts_store.get_chatbot(test_chatbot["id"]) is None
        finally:
            accounts_store.delete_account(tenant["id"])

    def test_unbound_tenant_cannot_delete_chatbot(self, client, test_chatbot):
        tenant = accounts_store.create_account("pytest_tenant_delete_denied@example.com", "tenant_primary", None)
        token = accounts_store.create_session(tenant["id"])
        try:
            resp = client.delete(
                f"/api/admin/chatbots/{test_chatbot['id']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403
        finally:
            accounts_store.delete_account(tenant["id"])


class TestAuditLogApi:
    def test_bound_tenant_sees_chatbot_audit_entries(self, client, test_chatbot):
        tenant = accounts_store.create_account("pytest_tenant_audit@example.com", "tenant_primary", None)
        accounts_store.bind_chatbot(tenant["id"], test_chatbot["id"])
        token = accounts_store.create_session(tenant["id"])
        accounts_store.record_audit(
            tenant["id"], action="update_chatbot", target_type="chatbot", target_id=test_chatbot["id"],
            detail={"name": "改名測試"},
        )
        try:
            resp = client.get(
                f"/api/admin/audit-log?chatbot_id={test_chatbot['id']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            entries = resp.json()["entries"]
            assert any(e["action"] == "update_chatbot" for e in entries)
        finally:
            accounts_store.delete_account(tenant["id"])

    def test_unbound_tenant_cannot_see_chatbot_audit_entries(self, client, test_chatbot):
        tenant = accounts_store.create_account("pytest_tenant_audit_denied@example.com", "tenant_primary", None)
        token = accounts_store.create_session(tenant["id"])
        try:
            resp = client.get(
                f"/api/admin/audit-log?chatbot_id={test_chatbot['id']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403
        finally:
            accounts_store.delete_account(tenant["id"])


class TestListAccountsApi:
    """GET /api/admin/accounts：帶 chatbot_id 查這家公司的協作帳號（不含管理者帳號），
    不帶則查全部管理者帳號（僅限 platform 角色）。"""

    def test_chatbot_scoped_list_excludes_unbound_platform_accounts(
        self, client, test_chatbot, platform_account
    ):
        """一般管理者帳號沒被綁定這家公司時，天生不會出現在協作帳號清單裡。"""
        tenant = accounts_store.create_account("pytest_accounts_chatbot_scope@example.com", "tenant_primary", None)
        accounts_store.bind_chatbot(tenant["id"], test_chatbot["id"])
        token = accounts_store.create_session(tenant["id"])
        try:
            resp = client.get(
                f"/api/admin/accounts?chatbot_id={test_chatbot['id']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            emails = [a["email"] for a in resp.json()["accounts"]]
            assert tenant["email"] in emails
            assert platform_account["email"] not in emails
        finally:
            accounts_store.delete_account(tenant["id"])

    def test_platform_account_that_created_chatbot_appears_in_its_account_list(
        self, client, platform_token, platform_account
    ):
        """管理者帳號自己建立公司時要自動綁定，讓這家公司的協作帳號清單能正常顯示、
        正常增減這個「創建者」（不受一般管理者帳號不綁定公司的預設行為影響）。"""
        create_resp = client.post(
            "/api/admin/chatbots",
            json={"name": "Pytest 管理者建立的公司"},
            headers={"Authorization": f"Bearer {platform_token}"},
        )
        assert create_resp.status_code == 200
        chatbot_id = create_resp.json()["id"]
        try:
            resp = client.get(
                f"/api/admin/accounts?chatbot_id={chatbot_id}",
                headers={"Authorization": f"Bearer {platform_token}"},
            )
            assert resp.status_code == 200
            emails = [a["email"] for a in resp.json()["accounts"]]
            assert platform_account["email"] in emails
        finally:
            accounts_store.delete_chatbot(chatbot_id)

    def test_chatbot_scoped_list_excludes_other_chatbots_accounts(self, client, test_chatbot):
        other_chatbot = accounts_store.create_chatbot("Pytest 其他公司", None)
        tenant_a = accounts_store.create_account("pytest_accounts_a@example.com", "tenant_primary", None)
        tenant_b = accounts_store.create_account("pytest_accounts_b@example.com", "tenant_primary", None)
        accounts_store.bind_chatbot(tenant_a["id"], test_chatbot["id"])
        accounts_store.bind_chatbot(tenant_b["id"], other_chatbot["id"])
        token_a = accounts_store.create_session(tenant_a["id"])
        try:
            resp = client.get(
                f"/api/admin/accounts?chatbot_id={test_chatbot['id']}",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert resp.status_code == 200
            emails = [a["email"] for a in resp.json()["accounts"]]
            assert tenant_a["email"] in emails
            assert tenant_b["email"] not in emails
        finally:
            accounts_store.delete_account(tenant_a["id"])
            accounts_store.delete_account(tenant_b["id"])
            accounts_store.delete_chatbot(other_chatbot["id"])

    def test_unbound_tenant_cannot_list_chatbot_accounts(self, client, test_chatbot):
        tenant = accounts_store.create_account("pytest_accounts_unbound@example.com", "tenant_primary", None)
        token = accounts_store.create_session(tenant["id"])
        try:
            resp = client.get(
                f"/api/admin/accounts?chatbot_id={test_chatbot['id']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403
        finally:
            accounts_store.delete_account(tenant["id"])

    def test_no_chatbot_id_lists_platform_accounts_only(self, client, platform_token, platform_account, test_chatbot):
        tenant = accounts_store.create_account("pytest_accounts_platform_list@example.com", "tenant_primary", None)
        accounts_store.bind_chatbot(tenant["id"], test_chatbot["id"])
        try:
            resp = client.get(
                "/api/admin/accounts", headers={"Authorization": f"Bearer {platform_token}"}
            )
            assert resp.status_code == 200
            accounts = resp.json()["accounts"]
            assert all(a["role"] in ["platform_primary", "platform_secondary"] for a in accounts)
            assert any(a["email"] == platform_account["email"] for a in accounts)
            assert tenant["email"] not in [a["email"] for a in accounts]
        finally:
            accounts_store.delete_account(tenant["id"])

    def test_no_chatbot_id_requires_platform_role(self, client):
        tenant = accounts_store.create_account("pytest_accounts_tenant_no_scope@example.com", "tenant_primary", None)
        token = accounts_store.create_session(tenant["id"])
        try:
            resp = client.get("/api/admin/accounts", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
        finally:
            accounts_store.delete_account(tenant["id"])


class TestPerChatbotRole:
    """同一個帳號在不同公司可以有不同身分（primary／secondary），見
    accounts_store.bind_chatbot() / get_chatbot_role() / is_chatbot_primary()。"""

    def test_primary_in_one_chatbot_can_be_secondary_in_another(self, client, test_chatbot):
        other_chatbot = accounts_store.create_chatbot("Pytest 第二家公司", None)
        owner = accounts_store.create_account("pytest_multi_role_owner@example.com", "tenant_primary", None)
        accounts_store.bind_chatbot(owner["id"], test_chatbot["id"], role="primary")
        other_primary = accounts_store.create_account("pytest_multi_role_other_owner@example.com", "tenant_primary", None)
        accounts_store.bind_chatbot(other_primary["id"], other_chatbot["id"], role="primary")
        token = accounts_store.create_session(other_primary["id"])
        try:
            # other_primary（other_chatbot 的 primary）把已存在的 owner 帳號綁成 other_chatbot 的協作帳號
            resp = client.post(
                "/api/admin/accounts",
                json={"email": owner["email"], "role": "tenant_secondary", "chatbot_id": other_chatbot["id"]},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

            assert accounts_store.get_chatbot_role(owner["id"], test_chatbot["id"]) == "primary"
            assert accounts_store.get_chatbot_role(owner["id"], other_chatbot["id"]) == "secondary"

            me_resp = client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {accounts_store.create_session(owner['id'])}"}
            )
            roles_by_chatbot = {c["id"]: c["your_role"] for c in me_resp.json()["chatbots"]}
            assert roles_by_chatbot[test_chatbot["id"]] == "primary"
            assert roles_by_chatbot[other_chatbot["id"]] == "secondary"
        finally:
            accounts_store.delete_account(owner["id"])
            accounts_store.delete_account(other_primary["id"])
            accounts_store.delete_chatbot(other_chatbot["id"])

    def test_secondary_cannot_add_accounts_to_chatbot(self, client, test_chatbot):
        secondary = accounts_store.create_account("pytest_secondary_no_manage@example.com", "tenant_secondary", None)
        accounts_store.bind_chatbot(secondary["id"], test_chatbot["id"], role="secondary")
        token = accounts_store.create_session(secondary["id"])
        try:
            resp = client.post(
                "/api/admin/accounts",
                json={
                    "email": "pytest_should_not_be_added@example.com",
                    "role": "tenant_secondary",
                    "chatbot_id": test_chatbot["id"],
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403
        finally:
            accounts_store.delete_account(secondary["id"])

    def test_delete_with_chatbot_id_only_unbinds_not_deletes_account(self, client, test_chatbot):
        other_chatbot = accounts_store.create_chatbot("Pytest 另一家公司", None)
        primary = accounts_store.create_account("pytest_unbind_primary@example.com", "tenant_primary", None)
        accounts_store.bind_chatbot(primary["id"], test_chatbot["id"], role="primary")
        collaborator = accounts_store.create_account("pytest_unbind_target@example.com", "tenant_secondary", None)
        accounts_store.bind_chatbot(collaborator["id"], test_chatbot["id"], role="secondary")
        accounts_store.bind_chatbot(collaborator["id"], other_chatbot["id"], role="secondary")
        token = accounts_store.create_session(primary["id"])
        try:
            resp = client.delete(
                f"/api/admin/accounts/{collaborator['id']}?chatbot_id={test_chatbot['id']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            # 帳號本身沒被刪除，另一家公司的綁定也還在
            assert accounts_store.get_account_by_id(collaborator["id"]) is not None
            assert accounts_store.get_chatbot_role(collaborator["id"], test_chatbot["id"]) is None
            assert accounts_store.get_chatbot_role(collaborator["id"], other_chatbot["id"]) == "secondary"
        finally:
            accounts_store.delete_account(primary["id"])
            accounts_store.delete_account(collaborator["id"])
            accounts_store.delete_chatbot(other_chatbot["id"])


def test_verify_google_id_token_tolerates_small_clock_skew(monkeypatch):
    """本機時鐘比 Google 慢幾秒不該讓登入失敗（真實發生過：Token used too early）。"""
    from google.oauth2 import id_token as google_id_token

    from app import auth

    captured = {}

    def fake_verify(token, request, audience=None, clock_skew_in_seconds=0):
        captured["skew"] = clock_skew_in_seconds
        return {"email": "someone@example.com"}

    monkeypatch.setattr(google_id_token, "verify_oauth2_token", fake_verify)

    assert auth.verify_google_id_token("fake-token") == "someone@example.com"
    assert captured["skew"] == auth.GOOGLE_TOKEN_CLOCK_SKEW_SECONDS >= 5
