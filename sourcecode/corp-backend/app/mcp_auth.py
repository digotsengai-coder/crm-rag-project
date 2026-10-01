"""
MCP endpoint 的 Bearer 金鑰驗證（純 ASGI middleware，掛在各個 MCP 子 app 外層）。

MCP 走無狀態 HTTP，每個請求都是獨立的，所以每個請求都要自帶 Authorization header，
不依賴任何 session；這也讓任何一台實例都能獨立驗證，不影響水平擴充。

金鑰用 callable 取得而不是建構時就寫死，是為了每次請求讀最新設定（測試也才能覆寫）。
"""
import hmac
import logging
from collections.abc import Callable

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("corp-backend.mcp")


class BearerAuthMiddleware:
    def __init__(self, app: ASGIApp, get_expected_token: Callable[[], str | None], name: str):
        self.app = app
        self._get_expected_token = get_expected_token
        self._name = name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # lifespan 等非 HTTP 事件直接放行，只有 HTTP 請求需要驗證
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        expected = self._get_expected_token()
        if not expected:
            # 沒設定金鑰時一律拒絕，避免忘了設定就變成公開端點
            logger.error(f"{self._name} 尚未設定 Bearer 金鑰，拒絕所有請求")
            response = JSONResponse({"detail": "MCP endpoint 尚未設定認證金鑰"}, status_code=503)
            await response(scope, receive, send)
            return

        scheme, _, presented = Headers(scope=scope).get("authorization", "").partition(" ")
        # compare_digest 是常數時間比對，避免從回應時間推測金鑰內容
        if scheme.lower() != "bearer" or not hmac.compare_digest(presented.strip().encode(), expected.encode()):
            response = JSONResponse(
                {"detail": "未提供或無效的 Bearer 金鑰"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
