from contextlib import AsyncExitStack, asynccontextmanager
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.firebase_client import initialize_firebase
from app.mcp_auth import BearerAuthMiddleware
from mcp.server.transport_security import TransportSecuritySettings

from app.mcp_server import mcp, mcp_admin
from app.routers import firestore, health, orders, products

# 設定 Logging 格式與層級
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("corp-backend")

# streamable_http_app() 要先呼叫一次，session_manager 才會被建立起來，
# 後面 lifespan 裡才能透過 session_manager.run() 啟動它。
#
# v1（FastMCP）時 json_response/stateless_http 是建構子參數；v2（MCPServer）的建構子
# 不再接受這些參數，改成呼叫 streamable_http_app() 時才指定。streamable_http_path="/"
# 是因為下面 app.mount 已經加了 "/mcp"、"/mcp-admin" 前綴，避免變成 "/mcp/mcp"。
def build_mcp_transport_security() -> TransportSecuritySettings | None:
    """
    MCP SDK 的 Host header 檢查（防 DNS rebinding）：這是給「跑在使用者本機、被瀏覽器網頁攻擊」的服務用的。
    - 設了 MCP_ALLOWED_HOSTS：只放行這些 Host（另外保留 localhost 方便本機測試）。
    - 在 Cloud Run 上（有 K_SERVICE）且沒設定：停用。遠端服務的邊界是 Bearer 金鑰（見 app/mcp_auth.py），
      攻擊者的網頁拿不到金鑰；不停用的話 Host 是 *.run.app，所有已通過認證的請求都會被回 421。
    - 其他（本機）：回傳 None，維持 SDK 預設（只放行 localhost）。
    """
    if settings.MCP_ALLOWED_HOSTS:
        hosts = [h.strip() for h in settings.MCP_ALLOWED_HOSTS.split(",") if h.strip()]
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[*hosts, "localhost:*", "127.0.0.1:*"],
        )
    if os.getenv("K_SERVICE"):
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    return None


_MCP_APP_KWARGS = dict(
    streamable_http_path="/", json_response=True, stateless_http=True,
    transport_security=build_mcp_transport_security(),
)
mcp_asgi_app = mcp.streamable_http_app(**_MCP_APP_KWARGS)
mcp_admin_asgi_app = mcp_admin.streamable_http_app(**_MCP_APP_KWARGS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 應用程式生命週期管理：
    - Startup: 初始化 Firebase Admin SDK、啟動兩個 MCP session manager
    - Shutdown: 資源清理

    Starlette 不會自動把 mount 進來的子 app 的 lifespan 串起來，
    所以 MCP session manager 要在這裡手動 run()，不然 stateless HTTP transport 收不到請求。
    """
    logger.info("啟動 Corp Backend FastAPI 服務中...")
    for env_name, value in (("MCP_API_KEY", settings.MCP_API_KEY), ("MCP_ADMIN_API_KEY", settings.MCP_ADMIN_API_KEY)):
        if not value:
            logger.warning(f"{env_name} 未設定：對應的 MCP endpoint 會拒絕所有請求（503）")
    try:
        initialize_firebase()
    except Exception as e:
        logger.warning(f"Startup 時 Firebase 初始化警告: {e}")
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        await stack.enter_async_context(mcp_admin.session_manager.run())
        yield
    logger.info("Corp Backend FastAPI 服務關閉中...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Corp Backend REST API 服務，提供 GCP Firebase Firestore 資料庫之 CRUD 操作與管理介面。",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 設定跨來源資源共享 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(health.router)
app.include_router(firestore.router, prefix=settings.API_V1_STR)
app.include_router(orders.router, prefix=settings.API_V1_STR)
app.include_router(products.router, prefix=settings.API_V1_STR)

# MCP server，跟上面的 REST API 並存，共用同一份 app/crud.py。
# 依權限拆成兩個 endpoint，各自要求不同的 Bearer 金鑰（見 app/mcp_server.py、app/mcp_auth.py）：
# - /mcp：唯讀 tools，聊天後端的 LLM 只連這個。
# - /mcp-admin：列表與寫入 tools（create／update／delete），聊天後端不使用。
app.mount("/mcp", BearerAuthMiddleware(mcp_asgi_app, lambda: settings.MCP_API_KEY, "/mcp"))
app.mount(
    "/mcp-admin",
    BearerAuthMiddleware(mcp_admin_asgi_app, lambda: settings.MCP_ADMIN_API_KEY, "/mcp-admin"),
)


@app.get("/", summary="首頁說明資訊")
def read_root():
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_check": "/health",
        "api_v1": settings.API_V1_STR
    }
