"""
測試開發用一鍵登入 /api/auth/dev-login 的多重保護。

這個端點是「跳過驗證」的入口，而本機開發用的資料庫可能就是正式環境那一個，所以測試重點是
「什麼情況下一定要拒絕」。全部用 monkeypatch 替換 accounts_store，不會對資料庫寫入；
也不使用 `with TestClient(...)`（不啟動 lifespan），避免連帶動到資料庫。
"""
import pytest
from fastapi.testclient import TestClient

from app import accounts_store
from app.config import settings
from app.main import app

LOOPBACK = ("127.0.0.1", 50000)
FAKE_ACCOUNT = {
    "id": "00000000-0000-0000-0000-000000000001",
    "email": "dev-admin@local.invalid",
    "role": "platform_primary",
    "created_by": None,
    "created_at": "2026-01-01T00:00:00+00:00",
}


class StoreSpy:
    """替換 accounts_store 的函式並記錄呼叫，確認被拒絕時完全沒有碰到帳號資料。"""

    def __init__(self, monkeypatch, existing_account=None):
        self.calls = []
        self.existing = existing_account

        def get_account_by_email(email):
            self.calls.append(("get_account_by_email", email))
            return self.existing

        def create_account(email, role, created_by):
            self.calls.append(("create_account", email, role))
            return {**FAKE_ACCOUNT, "email": email, "role": role}

        def create_session(account_id):
            self.calls.append(("create_session", account_id))
            return "fake-session-token"

        def record_audit(actor, action, target_type, target_id=None, detail=None):
            self.calls.append(("record_audit", action))

        monkeypatch.setattr(accounts_store, "get_account_by_email", get_account_by_email)
        monkeypatch.setattr(accounts_store, "create_account", create_account)
        monkeypatch.setattr(accounts_store, "create_session", create_session)
        monkeypatch.setattr(accounts_store, "record_audit", record_audit)

    def names(self):
        return [c[0] for c in self.calls]


def _client(host_port=LOOPBACK):
    """TestClient 預設的來源是 "testclient"；用一層 ASGI 包裝指定請求的來源 IP。"""

    async def app_with_client_ip(scope, receive, send):
        if scope["type"] == "http":
            scope = {**scope, "client": host_port}
        await app(scope, receive, send)

    return TestClient(app_with_client_ip)


def test_disabled_by_default_returns_404_and_touches_nothing(monkeypatch):
    assert settings.DEV_LOGIN_ENABLED is False  # 預設必須是關閉
    spy = StoreSpy(monkeypatch)

    resp = _client().post("/api/auth/dev-login")

    assert resp.status_code == 404
    assert spy.calls == []


def test_enabled_but_non_loopback_request_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "DEV_LOGIN_ENABLED", True)
    spy = StoreSpy(monkeypatch)

    resp = _client(("203.0.113.9", 50000)).post("/api/auth/dev-login")

    assert resp.status_code == 404
    assert spy.calls == []


def test_enabled_but_running_on_cloud_run_is_always_rejected(monkeypatch):
    """Cloud Run 一定有 K_SERVICE：就算有人誤把 DEV_LOGIN_ENABLED 設成 true，正式環境也必須停用。"""
    monkeypatch.setattr(settings, "DEV_LOGIN_ENABLED", True)
    monkeypatch.setenv("K_SERVICE", "crm-backend")
    spy = StoreSpy(monkeypatch)

    resp = _client().post("/api/auth/dev-login")

    assert resp.status_code == 404
    assert spy.calls == []


def test_enabled_from_loopback_creates_platform_admin_for_reserved_domain(monkeypatch):
    monkeypatch.setattr(settings, "DEV_LOGIN_ENABLED", True)
    monkeypatch.setattr(settings, "DEV_LOGIN_EMAIL", "dev-admin@local.invalid")
    monkeypatch.delenv("K_SERVICE", raising=False)
    spy = StoreSpy(monkeypatch)

    resp = _client().post("/api/auth/dev-login")

    assert resp.status_code == 200
    body = resp.json()
    assert body["token"] == "fake-session-token"
    assert body["account"]["email"] == "dev-admin@local.invalid"
    assert body["account"]["role"] == "platform_primary"
    assert ("create_account", "dev-admin@local.invalid", "platform_primary") in spy.calls
    assert ("record_audit", "dev_login") in spy.calls  # 每次開發登入都要留下稽核紀錄


@pytest.mark.parametrize("email", ["admin@gmail.com", "someone@company.com", "dev@example.com"])
def test_never_creates_an_admin_account_for_a_real_email(monkeypatch, email):
    """admin@gmail.com 是真實存在、不屬於我們的位址：替它建立平台管理員，持有者用 Google 登入就能取得權限。"""
    monkeypatch.setattr(settings, "DEV_LOGIN_ENABLED", True)
    monkeypatch.setattr(settings, "DEV_LOGIN_EMAIL", email)
    monkeypatch.delenv("K_SERVICE", raising=False)
    spy = StoreSpy(monkeypatch, existing_account=None)

    resp = _client().post("/api/auth/dev-login")

    assert resp.status_code == 409
    assert "create_account" not in spy.names()
    assert "create_session" not in spy.names()


def test_existing_account_is_used_as_is_and_its_role_is_never_changed(monkeypatch):
    monkeypatch.setattr(settings, "DEV_LOGIN_ENABLED", True)
    monkeypatch.setattr(settings, "DEV_LOGIN_EMAIL", "admin@gmail.com")
    monkeypatch.delenv("K_SERVICE", raising=False)
    existing = {**FAKE_ACCOUNT, "email": "admin@gmail.com", "role": "tenant_primary"}
    spy = StoreSpy(monkeypatch, existing_account=existing)

    resp = _client().post("/api/auth/dev-login")

    assert resp.status_code == 200
    assert resp.json()["account"]["role"] == "tenant_primary"  # 沒有被升級成管理員
    assert "create_account" not in spy.names()


@pytest.mark.parametrize("suffix", [".invalid", ".local", ".test", ".localhost"])
def test_reserved_domains_are_allowed_to_be_auto_created(monkeypatch, suffix):
    monkeypatch.setattr(settings, "DEV_LOGIN_ENABLED", True)
    monkeypatch.setattr(settings, "DEV_LOGIN_EMAIL", f"admin@dev{suffix}")
    monkeypatch.delenv("K_SERVICE", raising=False)
    spy = StoreSpy(monkeypatch)

    resp = _client().post("/api/auth/dev-login")

    assert resp.status_code == 200
    assert "create_account" in spy.names()
