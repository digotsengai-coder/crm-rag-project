"""
通用 MCP client：連到某家公司（chatbots.mcp_url）的 MCP server，列出它目前有哪些 tool、呼叫指定的 tool。

刻意不認識任何特定 tool（沒有 get_order 之類寫死的名稱）：server 新增 tool 之後，下一次
list_tools() 就會看到，backend 不用改；由 LLM 依 tool 的說明與參數格式自己決定要不要用
（見 app/providers.py 的 tool loop）。

使用 2026-07-28 無狀態協定：不做 initialize 握手，每個請求自帶協定版本與 client 資訊，
所以每個聊天請求開一段短連線、用完就關，不需要維護任何 session。每家公司帶自己的
Bearer 金鑰（chatbots.mcp_token）。
"""
import json
import logging
from urllib.parse import urlsplit, urlunsplit
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import httpx2
from mcp.client import Client
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client
from mcp.shared.exceptions import MCPError
from mcp_types import Implementation

from app.config import settings

logger = logging.getLogger("backend.mcp_client")

# 固定用 2026-07-28 無狀態協定；不用 mode="auto"，它會先多送一次 server/discover，
# 而這裡每個聊天請求都是一段短連線，等於每次多一趟往返。
MCP_PROTOCOL_MODE = "2026-07-28"
MCP_CLIENT_INFO = Implementation(name="crm-backend", version="1.0.0")


# SDK 把「HTTP 層失敗」（401 金鑰無效、503 服務未就緒、5xx 等任何非 2xx 且回應內容不是
# JSON-RPC 錯誤）統一轉成這個固定訊息的 MCPError，HTTP 狀態碼本身會遺失；tool 自己主動
# raise 的 MCPError（業務錯誤）訊息則是 tool 自訂的。用這個訊息區分兩者，
# 有測試鎖定這個行為（tests/test_mcp_client.py），SDK 改了訊息時測試會失敗提醒。
_SDK_HTTP_FAILURE_MESSAGE = "Server returned an error response"


class McpClientError(Exception):
    """連不上、逾時、被拒絕（401／503）等「MCP server 目前無法使用」的情況，呼叫端回友善訊息給使用者。"""


@dataclass(frozen=True)
class McpTool:
    name: str
    description: str
    # JSON Schema（server 用 Python 型別註解自動產生），交給 LLM 決定要帶什麼參數
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class McpToolResult:
    text: str
    is_error: bool = False


def normalize_mcp_url(mcp_url: str) -> str:
    """
    路徑結尾補上 "/"。corp-backend 把 MCP app mount 在 "/mcp"，沒有結尾斜線的請求會先被轉址到 "/mcp/"。
    在 Cloud Run 上這個轉址的 Location 會是 http://（HTTPS 在前端終止，程式看到的是 http），
    client 跟著轉到 http 後又被 Cloud Run 前端再轉一次，POST 與金鑰在過程中失效，最後整個請求失敗
    （本機沒有 HTTPS 前端所以不會發生）。直接用帶斜線的網址就完全不會轉址，公司設定填 /mcp 或 /mcp/ 都可以。
    """
    parts = urlsplit(mcp_url.strip())
    if parts.path and not parts.path.endswith("/"):
        parts = parts._replace(path=parts.path + "/")
    return urlunsplit(parts)


def _open_transport(mcp_url: str, mcp_token: str | None):
    """
    建立到公司 MCP server 的 transport。獨立成函式，測試才能把它換成進程內的 ASGI app。
    `create_mcp_http_client()` 預設開啟 follow_redirects，作為 URL 沒帶斜線時的保底；
    但主要靠 normalize_mcp_url() 事先補上斜線避開轉址（轉址在 Cloud Run 上會壞掉，見該函式說明）。
    """
    headers = {"Authorization": f"Bearer {mcp_token}"} if mcp_token else None
    http_client = create_mcp_http_client(
        headers=headers,
        timeout=httpx2.Timeout(settings.MCP_TIMEOUT_SECONDS),
    )
    return streamable_http_client(normalize_mcp_url(mcp_url), http_client=http_client)


def _is_exposed_to_llm(tool) -> bool:
    """
    預設不把明確標示「會寫入」的 tool 給 LLM：聊天訊息是不受信任的輸入，可能被拿來誘導
    LLM 呼叫寫入／刪除類 tool。annotations 只是 server 自己宣告的提示（沒標示的視為可用），
    真正的權限邊界是 server 端拆分與認證（見 corp-backend/app/mcp_server.py），這裡是多一層防護。
    """
    if settings.MCP_ALLOW_WRITE_TOOLS:
        return True
    annotations = getattr(tool, "annotations", None)
    if annotations is None:
        return True
    if annotations.destructive_hint:
        return False
    return annotations.read_only_hint is not False


def _result_to_text(result) -> str:
    """tool 結果轉成給 LLM 看的文字：優先用結構化內容，否則串接文字區塊；超過上限截斷。"""
    if result.structured_content is not None:
        text = json.dumps(result.structured_content, ensure_ascii=False)
    else:
        text = "\n".join(block.text for block in result.content if getattr(block, "text", None))
    limit = settings.MCP_TOOL_RESULT_MAX_CHARS
    if len(text) > limit:
        text = text[:limit] + f"…（內容過長，已截斷，共 {len(text)} 字）"
    return text


def _leaf_exceptions(exc: BaseException):
    """展開 anyio TaskGroup 巢狀的 ExceptionGroup，只留下真正的原因。"""
    if isinstance(exc, BaseExceptionGroup):
        for inner in exc.exceptions:
            yield from _leaf_exceptions(inner)
    else:
        yield exc


def _http_failure_error() -> McpClientError:
    return McpClientError("MCP server 回應錯誤（金鑰無效、服務未就緒或內部錯誤）")


class McpSession:
    """一次聊天請求內共用的連線：先 list_tools() 再依 LLM 的決定 call_tool()。"""

    def __init__(self, client: Client):
        self._client = client

    async def list_tools(self) -> list[McpTool]:
        try:
            result = await self._client.list_tools()
        except MCPError as e:
            if e.message == _SDK_HTTP_FAILURE_MESSAGE:
                raise _http_failure_error() from e
            raise McpClientError(f"列出 MCP tools 失敗：{e.message}") from e
        return [
            McpTool(name=t.name, description=t.description or "", input_schema=t.input_schema or {})
            for t in result.tools
            if _is_exposed_to_llm(t)
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any] | None) -> McpToolResult:
        """
        tool 本身回報的失敗（找不到資料、參數錯誤、tool 主動 raise MCPError 等）包成 is_error=True
        的結果回給 LLM，讓它能用自然語言告訴使用者；連線層級的失敗才會往外拋 McpClientError。
        """
        try:
            result = await self._client.call_tool(name, arguments or {})
        except MCPError as e:
            if e.message == _SDK_HTTP_FAILURE_MESSAGE:
                raise _http_failure_error() from e
            return McpToolResult(text=f"工具執行失敗：{e.message}", is_error=True)
        return McpToolResult(text=_result_to_text(result), is_error=bool(result.is_error))


@asynccontextmanager
async def open_mcp_session(mcp_url: str, mcp_token: str | None):
    """
    開一段到公司 MCP server 的短連線。無狀態模式下進入 Client 不會送任何請求，連線失敗
    （連不上、逾時、被拒絕）要到第一次請求時才會出現，而且 anyio 會把原因包成巢狀的
    ExceptionGroup 在離開時拋出，這裡統一展開並轉成 McpClientError，呼叫端只需要處理一種例外。

    但呼叫端自己在 with 區塊內丟出的例外（例如 LLM provider 沒設金鑰）不是 MCP 通訊問題，
    必須原樣往外拋，不能被誤標成「連線失敗」。區分方式：先記下 with 區塊內拋出的例外——
    一般的 Exception（且不是 McpClientError）就是呼叫端自己的錯誤；連線失敗時 with 區塊內看到的
    是 CancelledError（anyio 取消了正在等待的請求）或本模組已轉成 McpClientError 的例外。
    """
    client = Client(
        _open_transport(mcp_url, mcp_token),
        mode=MCP_PROTOCOL_MODE,
        client_info=MCP_CLIENT_INFO,
        read_timeout_seconds=settings.MCP_TIMEOUT_SECONDS,
    )
    body_error: BaseException | None = None
    try:
        async with client:
            try:
                yield McpSession(client)
            except BaseException as e:
                body_error = e
                raise
    except Exception as e:
        if isinstance(body_error, Exception) and not isinstance(body_error, McpClientError):
            raise body_error from None
        leaves = list(_leaf_exceptions(e))
        for leaf in leaves:
            if isinstance(leaf, McpClientError):
                raise leaf from None
        logger.warning(f"MCP 通訊失敗 url={mcp_url}: {[repr(x) for x in leaves]}")
        raise McpClientError("無法與 MCP server 通訊：" + "；".join(str(x) or type(x).__name__ for x in leaves)) from e
