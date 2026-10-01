"""
MCP server：把訂單 CRUD 包成 MCP tools，給 backend（CRM 聊天客服）當 MCP client 呼叫。

跟 app/routers/orders.py 共用同一個 app/crud.py，這裡不重複實作 Firestore 存取邏輯，
只是換一層 MCP tool 介面；REST API 維持原樣、兩條路徑並存。

用 stateless HTTP transport：v1（mcp==1.30.0）時 stateless_http/streamable_http_path
是 FastMCP 建構子參數，v2（mcp==2.0.0b2）的 MCPServer 建構子不再接受這些參數，
改成在 app/main.py 呼叫 mcp.streamable_http_app(streamable_http_path="/", stateless_http=True, ...)
時才指定；"/" 一樣是因為 mount 到 FastAPI 時已經在 app/main.py 指定了 "/mcp" 前綴，
避免變成 "/mcp/mcp"。

錯誤處理：v1 時工具內部 raise 一般例外（RuntimeError），FastMCP 框架會接住並轉成
CallToolResult(is_error=True, ...) 回給 client，不會變成協定層級的錯誤。v2 的 MCPServer
（mcp/server/mcpserver/server.py 內部 call_tool 分派邏輯）行為相同：只有工具內主動
raise mcp.shared.exceptions.MCPError 才會被原樣往外拋成協定層級的 JSON-RPC 錯誤，
一般 Exception 一樣會被接住包成 is_error=True 的 CallToolResult。這裡選擇全面改成
raise MCPError，讓 backend 端可以用 try/except MCPError 明確分辨「工具執行失敗」
（已知的業務錯誤，例如 Firestore 讀寫失敗、找不到訂單、未帶更新欄位），跟連線失敗這種
更底層的例外分開處理；同時仍保留錯誤訊息附掛 log。

權限拆分（給聊天後端的 LLM 用的 tool 一定要是唯讀、且不能讓人只靠編號就撈到別人的訂單）：
- `mcp`（掛在 /mcp）：search_order（訂單編號＋電話號碼都符合才回傳）與 get_latest_promotions
  （公開的最新活動，內容在 app/promotions.py），聊天後端的 LLM 只會連到這一個。
- `mcp_admin`（掛在 /mcp-admin）：get_order、list_orders 與 create／update／delete，聊天後端不使用。
  get_order 只憑訂單編號就回傳整筆訂單、list_orders 會回傳所有訂單，兩者都沒有驗證或租戶隔離，
  放在 /mcp 會讓任何人能在聊天視窗逐筆枚舉別人的訂單，所以只放管理端。
兩個 endpoint 各自用不同的 Bearer 金鑰（見 app/mcp_auth.py、app/config.py）。
"""
import logging

from mcp.server.mcpserver import MCPServer
from mcp.shared.exceptions import MCPError
from mcp_types import INTERNAL_ERROR, INVALID_PARAMS, ToolAnnotations

from app import crud
from app.promotions import PROMOTIONS
from app.schemas import OrderCreate, OrderUpdate

logger = logging.getLogger("corp-backend.mcp")

COLLECTION_ORDERS = "Order"

mcp = MCPServer(name="corp-backend-orders")
mcp_admin = MCPServer(name="corp-backend-orders-admin")


@mcp_admin.tool(annotations=ToolAnnotations(read_only_hint=True))
def get_order(order_id: str) -> dict | None:
    """依 ID（NewOrderID 或 OrderID）查詢單筆訂單，回應格式同 GET /Order/{order_id}。找不到時回傳 None。"""
    try:
        doc = crud.get_document(collection_name=COLLECTION_ORDERS, doc_id=order_id)
    except Exception as e:
        logger.error(f"MCP get_order 讀取 Firebase 訂單失敗: {e}")
        raise MCPError(code=INTERNAL_ERROR, message=f"讀取 Firebase 訂單失敗: {order_id}") from e
    if not doc:
        return None
    return {"id": doc.id, **doc.data}


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def search_order(order_id: str, phone_number: str) -> dict | None:
    """依訂單編號與電話號碼查詢訂單，兩者必須完全符合。找不到或電話不符時回傳 None。"""
    try:
        doc = crud.get_document(collection_name=COLLECTION_ORDERS, doc_id=order_id)
    except Exception as e:
        logger.error(f"MCP search_order 讀取 Firebase 訂單失敗: {e}")
        raise MCPError(code=INTERNAL_ERROR, message=f"讀取 Firebase 訂單失敗: {order_id}") from e
    if not doc:
        return None
    if doc.data.get("PhoneNumber") != phone_number:
        return None

    return {"id": doc.id, **doc.data}


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def get_latest_promotions() -> dict:
    """查詢本公司目前最新的優惠活動（例如折扣）。顧客詢問活動、優惠、折扣，或說「原神啟動」時使用，不需要任何參數。"""
    return {"count": len(PROMOTIONS), "promotions": PROMOTIONS}


@mcp_admin.tool(annotations=ToolAnnotations(read_only_hint=True))
def list_orders(limit: int = 100, order_by: str | None = None) -> dict:
    """查詢訂單列表，回應格式同 GET /Order（count + orders）。"""
    try:
        raw_res = crud.list_documents(collection_name=COLLECTION_ORDERS, limit=limit, order_by=order_by)
    except Exception as e:
        logger.error(f"MCP list_orders 查詢 Firebase 訂單列表失敗: {e}")
        raise MCPError(code=INTERNAL_ERROR, message="查詢 Firebase 訂單列表失敗") from e
    orders = [{"id": doc.id, **doc.data} for doc in raw_res.documents]
    return {"count": len(orders), "orders": orders}


@mcp_admin.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False))
def create_order(payload: OrderCreate) -> dict:
    """新增訂單，回應格式同 POST /Order。"""
    try:
        doc_id = payload.NewOrderID or str(payload.OrderID)
        res = crud.create_document(collection_name=COLLECTION_ORDERS, data=payload.model_dump(), doc_id=doc_id)
    except Exception as e:
        logger.error(f"MCP create_order 寫入 Firebase 訂單失敗: {e}")
        raise MCPError(code=INTERNAL_ERROR, message="寫入 Firebase 訂單失敗") from e
    return {"id": res.id, **res.data}


@mcp_admin.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False))
def update_order(order_id: str, payload: OrderUpdate) -> dict | None:
    """更新訂單部分欄位，回應格式同 PATCH /Order/{order_id}。找不到時回傳 None。"""
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise MCPError(code=INVALID_PARAMS, message="未傳遞任何需要更新的欄位")
    try:
        res = crud.update_document(collection_name=COLLECTION_ORDERS, doc_id=order_id, data=update_data, merge=True)
    except Exception as e:
        logger.error(f"MCP update_order 更新 Firebase 訂單失敗: {e}")
        raise MCPError(code=INTERNAL_ERROR, message=f"更新 Firebase 訂單失敗: {order_id}") from e
    if not res:
        return None
    return {"id": res.id, **res.data}


@mcp_admin.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True))
def delete_order(order_id: str) -> dict | None:
    """刪除訂單，回應格式同 DELETE /Order/{order_id}。找不到時回傳 None。"""
    try:
        success = crud.delete_document(collection_name=COLLECTION_ORDERS, doc_id=order_id)
    except Exception as e:
        logger.error(f"MCP delete_order 刪除 Firebase 訂單失敗: {e}")
        raise MCPError(code=INTERNAL_ERROR, message=f"刪除 Firebase 訂單失敗: {order_id}") from e
    if not success:
        return None
    return {"status": "success", "message": f"已成功刪除 Firebase 訂單 ID '{order_id}'"}
