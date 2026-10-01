"""
測試 MCP endpoint 的權限拆分與 Bearer 認證。

用進程內的 ASGI 直接呼叫真正的 app.main.app（不啟動 uvicorn、不連 Firebase），
請求格式跟 backend client 的 2026-07-28 無狀態協定一致：每個請求自帶 _meta 與版本 header。
"""
import asyncio
import threading

import httpx2 as httpx
import pytest

from app import main
from app.config import settings

READ_KEY = "test-read-key"
ADMIN_KEY = "test-admin-key"

# transport security 只放行帶 port 的 localhost，所以 base_url 要帶 port
BASE_URL = "http://localhost:8001"

READ_ONLY_TOOLS = {"search_order", "get_latest_promotions"}
ADMIN_TOOLS = {"get_order", "list_orders", "create_order", "update_order", "delete_order"}


@pytest.fixture(scope="module")
def running_app():
    """
    整個模組只啟動一次 app 的 lifespan：StreamableHTTPSessionManager.run() 每個實例只能呼叫一次，
    而 app.main.app 是模組層級的單例。lifespan 放在背景執行緒的 event loop，測試把請求送進同一個 loop。
    """
    loop = asyncio.new_event_loop()
    started = threading.Event()
    stop = {}

    async def serve():
        stop["event"] = asyncio.Event()
        async with main.app.router.lifespan_context(main.app):
            started.set()
            await stop["event"].wait()

    # 測試不需要真的初始化 Firebase（fixture 在 monkeypatch 之外，這裡直接換掉再還原）
    original_init = main.initialize_firebase
    main.initialize_firebase = lambda: None
    thread = threading.Thread(target=lambda: loop.run_until_complete(serve()), daemon=True)
    thread.start()
    assert started.wait(timeout=10), "app lifespan 沒有在 10 秒內啟動"
    try:
        yield loop
    finally:
        loop.call_soon_threadsafe(stop["event"].set)
        thread.join(timeout=10)
        main.initialize_firebase = original_init
        loop.close()


@pytest.fixture(autouse=True)
def _configure_keys(monkeypatch):
    monkeypatch.setattr(settings, "MCP_API_KEY", READ_KEY)
    monkeypatch.setattr(settings, "MCP_ADMIN_API_KEY", ADMIN_KEY)


def _rpc(method: str, params: dict | None = None) -> dict:
    meta = {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientInfo": {"name": "test", "version": "0"},
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    return {"jsonrpc": "2.0", "id": 1, "method": method, "params": {**(params or {}), "_meta": meta}}


def _request(loop, method: str, path: str, *, body: dict | None = None, token: str | None = None):
    async def run():
        headers = {"accept": "application/json, text/event-stream"}
        if body is not None:
            headers.update({"content-type": "application/json", "mcp-protocol-version": "2026-07-28", "mcp-method": body["method"]})
            if body["method"] == "tools/call":
                # 2026-07-28 規定 tools/call 的 tool 名稱要同時放在 header，且必須與 body 一致
                headers["mcp-name"] = body["params"]["name"]
        if token is not None:
            headers["authorization"] = f"Bearer {token}"
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
            return await client.request(method, path, json=body, headers=headers)

    return asyncio.run_coroutine_threadsafe(run(), loop).result(timeout=15)


def _tool_names(response) -> set[str]:
    return {t["name"] for t in response.json()["result"]["tools"]}


def test_read_endpoint_exposes_only_read_only_tools(running_app):
    response = _request(running_app, "POST", "/mcp/", body=_rpc("tools/list"), token=READ_KEY)

    assert response.status_code == 200
    assert _tool_names(response) == READ_ONLY_TOOLS


def test_order_lookup_by_id_alone_is_not_exposed_on_read_endpoint(running_app):
    """只憑訂單編號就能撈整筆訂單的 tool 不能放在聊天 LLM 連得到的 endpoint（會被逐筆枚舉）。"""
    response = _request(running_app, "POST", "/mcp/", body=_rpc("tools/list"), token=READ_KEY)

    names = _tool_names(response)
    assert "get_order" not in names and "list_orders" not in names
    assert "search_order" in names  # 要求「訂單編號＋電話」都符合的版本才放在這


def test_admin_endpoint_exposes_list_and_write_tools(running_app):
    response = _request(running_app, "POST", "/mcp-admin/", body=_rpc("tools/list"), token=ADMIN_KEY)

    assert response.status_code == 200
    assert _tool_names(response) == ADMIN_TOOLS


def test_write_tools_cannot_be_called_through_read_endpoint(running_app):
    """即使 LLM 猜到寫入 tool 的名字，唯讀 endpoint 也不認得、不會執行。"""
    body = _rpc("tools/call", {"name": "delete_order", "arguments": {"order_id": "X"}})
    response = _request(running_app, "POST", "/mcp/", body=body, token=READ_KEY)

    result = response.json()["result"]
    assert result["isError"] is True
    assert "Unknown tool" in result["content"][0]["text"]


def test_same_call_is_recognized_on_admin_endpoint(running_app, monkeypatch):
    """對照組：同一個 tool 名稱在管理 endpoint 是存在的，證明上面的「Unknown tool」真的是拆分造成的。"""
    from app import mcp_server

    monkeypatch.setattr(mcp_server.crud, "delete_document", lambda collection_name, doc_id: False)
    body = _rpc("tools/call", {"name": "delete_order", "arguments": {"order_id": "X"}})
    response = _request(running_app, "POST", "/mcp-admin/", body=body, token=ADMIN_KEY)

    result = response.json()["result"]
    assert "Unknown tool" not in str(result)


@pytest.mark.parametrize("path", ["/mcp/", "/mcp-admin/"])
def test_missing_token_is_rejected(running_app, path):
    response = _request(running_app, "POST", path, body=_rpc("tools/list"), token=None)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("path", ["/mcp/", "/mcp-admin/"])
def test_wrong_token_is_rejected(running_app, path):
    response = _request(running_app, "POST", path, body=_rpc("tools/list"), token="wrong-key")

    assert response.status_code == 401


def test_read_key_cannot_access_admin_endpoint(running_app):
    response = _request(running_app, "POST", "/mcp-admin/", body=_rpc("tools/list"), token=READ_KEY)

    assert response.status_code == 401


def test_admin_key_cannot_access_read_endpoint(running_app):
    """兩把金鑰互不通用：管理金鑰外洩也不能拿來當作聊天用的唯讀金鑰，反之亦然。"""
    response = _request(running_app, "POST", "/mcp/", body=_rpc("tools/list"), token=ADMIN_KEY)

    assert response.status_code == 401


@pytest.mark.parametrize("path,attr", [("/mcp/", "MCP_API_KEY"), ("/mcp-admin/", "MCP_ADMIN_API_KEY")])
def test_endpoint_fails_closed_when_key_not_configured(running_app, monkeypatch, path, attr):
    monkeypatch.setattr(settings, attr, None)

    # 就算帶了「空字串」也不能通過
    response = _request(running_app, "POST", path, body=_rpc("tools/list"), token="")

    assert response.status_code == 503


def test_rest_endpoints_are_unaffected_by_mcp_auth(running_app):
    response = _request(running_app, "GET", "/health")

    assert response.status_code == 200


def test_latest_promotions_returns_current_promotions_on_read_endpoint(running_app, monkeypatch):
    """聊天 LLM 問活動時能拿到 PROMOTIONS 的內容（預設全館 9 折）；換活動只需改 PROMOTIONS。"""
    from app import mcp_server

    body = _rpc("tools/call", {"name": "get_latest_promotions", "arguments": {}})
    response = _request(running_app, "POST", "/mcp/", body=body, token=READ_KEY)

    result = response.json()["result"]
    assert result.get("isError") is not True
    assert "全館 9 折" in str(result)

    monkeypatch.setattr(mcp_server, "PROMOTIONS", [{"title": "夏日特賣", "description": "第二件 5 折"}])
    response = _request(running_app, "POST", "/mcp/", body=body, token=READ_KEY)
    assert "夏日特賣" in str(response.json()["result"])
