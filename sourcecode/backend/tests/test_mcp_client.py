"""
測試 app/mcp_client.py（通用 MCP client）。

用進程內的 ASGI MCP server 取代真的公司 MCP server（把 create_mcp_http_client 換成走 ASGI 的
httpx2 client），所以不需要啟動 corp-backend、也不會連到任何真實服務。
"""
import asyncio
import time
from contextlib import asynccontextmanager

import httpx2
import pytest
from mcp.server.mcpserver import MCPServer
from mcp.shared.exceptions import MCPError
from mcp_types import INTERNAL_ERROR, ToolAnnotations

from app import mcp_client
from app.config import settings
from app.mcp_client import McpClientError, open_mcp_session

BASE_URL = "http://localhost:8001/"


class FakeCompanyServer:
    """一家公司的 MCP server；記錄收到的請求 header，並可設定要不要在 HTTP 層拒絕。"""

    def __init__(self):
        self.mcp = MCPServer(name="fake-company")
        self.asgi = self.mcp.streamable_http_app(streamable_http_path="/", json_response=True, stateless_http=True)
        self.seen_headers: list[dict] = []
        self.reject_with: int | None = None

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            self.seen_headers.append({k.decode(): v.decode() for k, v in scope["headers"]})
            if self.reject_with:
                await send({"type": "http.response.start", "status": self.reject_with, "headers": []})
                await send({"type": "http.response.body", "body": b"no"})
                return
        await self.asgi(scope, receive, send)


@asynccontextmanager
async def running_server(monkeypatch):
    server = FakeCompanyServer()

    def _asgi_http_client(headers=None, timeout=None, auth=None):
        return httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=server), headers=headers, timeout=timeout, follow_redirects=True
        )

    monkeypatch.setattr(mcp_client, "create_mcp_http_client", _asgi_http_client)
    async with server.mcp.session_manager.run():
        yield server


async def test_new_server_tool_is_discovered_without_any_client_change(monkeypatch):
    """這次改版的核心目標：server 端新增 tool，client 程式碼不用動，下一次 list_tools() 就看得到。"""
    async with running_server(monkeypatch) as server:

        @server.mcp.tool()
        def search_products(keyword: str) -> str:
            """依關鍵字搜尋產品"""
            return f"找到 {keyword}"

        async with open_mcp_session(BASE_URL, "tok") as session:
            assert [t.name for t in await session.list_tools()] == ["search_products"]

        @server.mcp.tool()
        def check_stock(sku: str) -> str:
            """查詢庫存"""
            return "有貨"

        async with open_mcp_session(BASE_URL, "tok") as session:
            tools = {t.name: t for t in await session.list_tools()}
            assert set(tools) == {"search_products", "check_stock"}
            assert tools["check_stock"].description == "查詢庫存"
            assert tools["check_stock"].input_schema["properties"]["sku"]["type"] == "string"


async def test_call_tool_returns_text_and_sends_bearer_token(monkeypatch):
    async with running_server(monkeypatch) as server:

        @server.mcp.tool()
        def echo(text: str) -> str:
            return f"回音：{text}"

        async with open_mcp_session(BASE_URL, "company-secret") as session:
            result = await session.call_tool("echo", {"text": "你好"})

        assert "回音：你好" in result.text
        assert result.is_error is False
        assert all(h.get("authorization") == "Bearer company-secret" for h in server.seen_headers)


async def test_requests_are_stateless_and_self_describing(monkeypatch):
    async with running_server(monkeypatch) as server:

        @server.mcp.tool()
        def echo(text: str) -> str:
            return text

        async with open_mcp_session(BASE_URL, None) as session:
            await session.list_tools()
            await session.call_tool("echo", {"text": "x"})

        assert server.seen_headers
        assert all("mcp-session-id" not in h for h in server.seen_headers)
        assert all(h.get("mcp-protocol-version") == "2026-07-28" for h in server.seen_headers)
        assert all("authorization" not in h for h in server.seen_headers)  # 沒設金鑰就不帶 header


async def test_write_tools_are_hidden_from_llm_by_default(monkeypatch):
    async with running_server(monkeypatch) as server:

        @server.mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
        def read_thing() -> str:
            return "r"

        @server.mcp.tool()  # 沒標示 annotations 的視為可用
        def unmarked_thing() -> str:
            return "u"

        @server.mcp.tool(annotations=ToolAnnotations(read_only_hint=False))
        def write_thing() -> str:
            return "w"

        @server.mcp.tool(annotations=ToolAnnotations(destructive_hint=True))
        def delete_thing() -> str:
            return "d"

        async with open_mcp_session(BASE_URL, "t") as session:
            assert {t.name for t in await session.list_tools()} == {"read_thing", "unmarked_thing"}

        monkeypatch.setattr(settings, "MCP_ALLOW_WRITE_TOOLS", True)
        async with open_mcp_session(BASE_URL, "t") as session:
            assert {t.name for t in await session.list_tools()} == {
                "read_thing", "unmarked_thing", "write_thing", "delete_thing",
            }


async def test_tool_reported_error_is_returned_to_llm_not_raised(monkeypatch):
    """tool 自己回報的業務錯誤要讓 LLM 看得到、能轉述給使用者，不能當成連線失敗。"""
    async with running_server(monkeypatch) as server:

        @server.mcp.tool()
        def find_order(order_id: str) -> str:
            raise MCPError(code=INTERNAL_ERROR, message=f"查無訂單 {order_id}")

        async with open_mcp_session(BASE_URL, "t") as session:
            result = await session.call_tool("find_order", {"order_id": "Z1"})

        assert result.is_error is True
        assert "查無訂單 Z1" in result.text


async def test_long_tool_result_is_truncated(monkeypatch):
    monkeypatch.setattr(settings, "MCP_TOOL_RESULT_MAX_CHARS", 100)
    async with running_server(monkeypatch) as server:

        @server.mcp.tool()
        def big() -> str:
            return "字" * 5000

        async with open_mcp_session(BASE_URL, "t") as session:
            result = await session.call_tool("big", {})

        assert len(result.text) < 200
        assert "已截斷" in result.text


@pytest.mark.parametrize("status", [401, 503])
async def test_http_level_rejection_raises_client_error(monkeypatch, status):
    """金鑰無效（401）、服務未就緒（503）：屬於連線問題，不是 tool 業務錯誤，要拋 McpClientError。"""
    async with running_server(monkeypatch) as server:
        server.reject_with = status

        with pytest.raises(McpClientError):
            async with open_mcp_session(BASE_URL, "wrong") as session:
                await session.list_tools()


async def test_http_level_rejection_on_call_tool_raises_client_error(monkeypatch):
    async with running_server(monkeypatch) as server:

        @server.mcp.tool()
        def echo(text: str) -> str:
            return text

        with pytest.raises(McpClientError):
            async with open_mcp_session(BASE_URL, "t") as session:
                await session.list_tools()
                server.reject_with = 401  # 中途金鑰被撤銷
                await session.call_tool("echo", {"text": "x"})


async def test_sdk_http_failure_message_is_what_we_detect():
    """鎖定 SDK 行為：mcp_client 靠這個固定訊息區分「HTTP 失敗」與「tool 自己的業務錯誤」。"""
    import inspect
    from mcp.client import streamable_http

    assert mcp_client._SDK_HTTP_FAILURE_MESSAGE in inspect.getsource(streamable_http)


async def test_connection_refused_raises_client_error():
    with pytest.raises(McpClientError):
        async with open_mcp_session("http://localhost:9/mcp", "t") as session:
            await session.list_tools()


async def test_slow_tool_call_times_out_quickly_and_is_reported_to_llm(monkeypatch):
    """卡住的 tool 不能拖住整個聊天請求：逾時後以「工具執行失敗」回給 LLM，讓它告訴使用者暫時查不到。"""
    monkeypatch.setattr(settings, "MCP_TIMEOUT_SECONDS", 0.3)
    async with running_server(monkeypatch) as server:

        @server.mcp.tool()
        async def slow() -> str:
            await asyncio.sleep(3)
            return "late"

        started = time.monotonic()
        async with open_mcp_session(BASE_URL, "t") as session:
            result = await session.call_tool("slow", {})
        elapsed = time.monotonic() - started

        assert result.is_error is True
        assert "timed out" in result.text
        assert elapsed < 2, f"應該在逾時設定（0.3 秒）附近就中斷，實際等了 {elapsed:.1f} 秒"


async def test_caller_own_error_inside_session_is_raised_unchanged(monkeypatch):
    """呼叫端 with 區塊內自己的錯誤（不是 MCP 通訊問題）必須原樣拋出，不能被誤標成 McpClientError。"""

    class CallerError(Exception):
        pass

    async with running_server(monkeypatch):
        with pytest.raises(CallerError) as excinfo:
            async with open_mcp_session(BASE_URL, "t") as session:
                await session.list_tools()  # 連線本身是好的
                raise CallerError("呼叫端自己的錯誤")

        assert type(excinfo.value) is CallerError
        assert not isinstance(excinfo.value, McpClientError)


async def test_caller_own_error_before_any_request_is_raised_unchanged(monkeypatch):
    """就算還沒送出任何 MCP 請求，呼叫端的錯誤也一樣要原樣拋出（真實 bug：Gemini 沒設金鑰）。"""
    async with running_server(monkeypatch):
        with pytest.raises(ValueError):
            async with open_mcp_session(BASE_URL, "t"):
                raise ValueError("尚未設定金鑰")


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://svc-123.europe-west1.run.app/mcp", "https://svc-123.europe-west1.run.app/mcp/"),
        ("https://svc-123.europe-west1.run.app/mcp/", "https://svc-123.europe-west1.run.app/mcp/"),  # 已有斜線不重複加
        ("http://localhost:8001/mcp", "http://localhost:8001/mcp/"),
        ("  https://h.run.app/mcp  ", "https://h.run.app/mcp/"),  # 前後空白
        ("https://h.run.app/mcp?x=1", "https://h.run.app/mcp/?x=1"),  # 保留查詢字串
        ("https://h.run.app/a/b", "https://h.run.app/a/b/"),
        ("https://h.run.app", "https://h.run.app"),  # 沒有路徑就不動
    ],
)
def test_normalize_mcp_url_adds_trailing_slash(url, expected):
    """真實問題：沒有結尾斜線會先被轉址到錯誤的 http://（Cloud Run），請求就失敗；補斜線可完全避開轉址。"""
    assert mcp_client.normalize_mcp_url(url) == expected


def test_transport_is_opened_with_the_normalized_url(monkeypatch):
    seen = {}

    def fake_streamable_http_client(url, http_client=None):
        seen["url"] = url
        return object()

    monkeypatch.setattr(mcp_client, "streamable_http_client", fake_streamable_http_client)

    mcp_client._open_transport("https://svc.run.app/mcp", "tok")

    assert seen["url"] == "https://svc.run.app/mcp/"
