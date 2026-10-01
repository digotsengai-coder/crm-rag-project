"""
測試 MCP 的 Host header 檢查（SDK 內建的 DNS rebinding 防護）在不同部署環境下的設定。

真實發生過的問題：部署到 Cloud Run 後，Host 是 *.run.app，不在 SDK 預設只放行 localhost 的名單裡，
所以所有「已通過金鑰認證」的 MCP 請求都被回 421 "Invalid Host header"，backend 顯示「暫時無法連線」。
本機測試都用 localhost，所以一直沒抓到。這裡用 https://<run.app 網域> 當 base_url 重現並驗證修正。
"""
import asyncio

import httpx2 as httpx
import pytest
from mcp.server.mcpserver import MCPServer

from app import main
from app.config import settings

CLOUD_RUN_HOST = "crm-squard-stage-corp-backend-821217334800.europe-west1.run.app"


def _rpc():
    meta = {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientInfo": {"name": "test", "version": "0"},
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    return {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": meta}}


def _status(transport_security, base_url: str) -> int:
    """用指定的 transport_security 建一個全新的 MCP app，從指定的 Host 打一次 tools/list。"""
    server = MCPServer(name="host-check")

    @server.tool()
    def ping() -> str:
        return "pong"

    app = server.streamable_http_app(
        streamable_http_path="/", json_response=True, stateless_http=True, transport_security=transport_security
    )

    async def run():
        async with server.session_manager.run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url=base_url) as client:
                response = await client.post(
                    "/",
                    json=_rpc(),
                    headers={
                        "content-type": "application/json",
                        "accept": "application/json, text/event-stream",
                        "mcp-protocol-version": "2026-07-28",
                        "mcp-method": "tools/list",
                    },
                )
                return response.status_code

    return asyncio.run(run())


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.setattr(settings, "MCP_ALLOWED_HOSTS", None)


def test_default_config_still_rejects_non_localhost_hosts():
    """重現原本的問題：沒有任何設定時（SDK 預設），Cloud Run 網域會被 421 擋下。"""
    security = main.build_mcp_transport_security()

    assert security is None  # 本機維持 SDK 預設
    assert _status(security, f"https://{CLOUD_RUN_HOST}") == 421


def test_default_config_allows_localhost():
    assert _status(main.build_mcp_transport_security(), "http://localhost:8001") == 200


def test_on_cloud_run_the_host_check_is_disabled(monkeypatch):
    """修正：在 Cloud Run 上（有 K_SERVICE）Cloud Run 網域不再被擋，邊界改由 Bearer 金鑰把關。"""
    monkeypatch.setenv("K_SERVICE", "crm-squard-stage-corp-backend")

    security = main.build_mcp_transport_security()

    assert security is not None and security.enable_dns_rebinding_protection is False
    assert _status(security, f"https://{CLOUD_RUN_HOST}") == 200


def test_allowed_hosts_setting_restricts_to_listed_hosts(monkeypatch):
    monkeypatch.setattr(settings, "MCP_ALLOWED_HOSTS", CLOUD_RUN_HOST)
    monkeypatch.setenv("K_SERVICE", "crm-squard-stage-corp-backend")  # 有明確清單時，優先於「Cloud Run 就停用」

    security = main.build_mcp_transport_security()

    assert security.enable_dns_rebinding_protection is True
    assert _status(security, f"https://{CLOUD_RUN_HOST}") == 200
    assert _status(security, "https://evil.example.com") == 421  # 不在清單的 Host 仍被擋
    assert _status(security, "http://localhost:8001") == 200  # 保留 localhost 方便本機測試


def test_allowed_hosts_accepts_comma_separated_list_with_spaces(monkeypatch):
    monkeypatch.setattr(settings, "MCP_ALLOWED_HOSTS", " a.run.app , b.run.app ")

    security = main.build_mcp_transport_security()

    assert "a.run.app" in security.allowed_hosts and "b.run.app" in security.allowed_hosts
