"""
測試 /api/chat 端點的分流（main.py 的 _handle_chat）。

用 FastAPI TestClient 當黑箱測試，確保：
- 訊息以 `@mcp` 開頭時走 MCP 路徑（app/mcp_chat.py），各種「不能用」的情況（沒有對應公司、公司沒填
  mcp_url、provider 不支援 tool calling、連不上 MCP server）都回傳可理解的文字，不是 500、也不會
  悄悄退回 RAG。完整的 tool 呼叫流程見 tests/test_mcp_chat.py。
- 沒有 `@mcp` 的訊息一律走原本的 RAG + LLM，就算內容長得像訂單編號也一樣（不再有訂單專屬的正則分流）。
"""
import pytest
from fastapi.testclient import TestClient

from app import accounts_store
from app.config import settings
from app.main import app, _chatbot_request_log, _request_log

CLIENT_HEADERS = {"X-Client-ID": "client_test"}


@pytest.fixture
def mcp_chatbot():
    """有填 mcp_url 的測試公司。mcp_url 指向一個沒人監聽的位址：這裡的測試不需要真的連到 MCP server。"""
    chatbot = accounts_store.create_chatbot("Pytest MCP Chatbot", "http://localhost:9/mcp")
    yield chatbot
    accounts_store.delete_chatbot(chatbot["id"])


def _client_headers(chatbot_id: str) -> dict:
    return {"X-Client-ID": chatbot_id}


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """避免同一支測試檔案內多次呼叫 /api/chat 時，被 main.py 的簡易 rate limit 誤擋。"""
    _request_log.clear()
    _chatbot_request_log.clear()
    yield
    _request_log.clear()
    _chatbot_request_log.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _post_chat(client, message, chatbot_id=None, provider="google"):
    return client.post(
        "/api/chat",
        json={"message": message, "history": [], "provider": provider},
        headers=_client_headers(chatbot_id) if chatbot_id else CLIENT_HEADERS,
    )



def test_mcp_command_without_chatbot_returns_not_enabled_message(client):
    """X-Client-ID 對不到任何公司（"client_test" 不是合法 UUID）時，@mcp 回覆尚未開啟，不是 500。"""
    resp = _post_chat(client, "@mcp 幫我查訂單 A12345")

    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "text"
    assert "尚未開啟 MCP 功能" in body["text"]


def test_mcp_command_when_chatbot_has_no_mcp_url_returns_not_enabled_message(client, test_chatbot):
    resp = _post_chat(client, "@mcp 幫我查訂單 A12345", test_chatbot["id"])

    assert resp.json()["type"] == "text"
    assert "尚未開啟 MCP 功能" in resp.json()["text"]


def test_mcp_command_with_empty_question_prompts_for_question(client, mcp_chatbot):
    resp = _post_chat(client, "  @MCP  ", mcp_chatbot["id"])

    assert resp.json()["type"] == "text"
    assert "請在 @MCP 後面輸入您的問題" in resp.json()["text"]


def test_mcp_command_with_unsupported_provider_says_so(client, mcp_chatbot):
    resp = _post_chat(client, "@mcp 查庫存", mcp_chatbot["id"], provider="openai")

    assert resp.json()["type"] == "text"
    assert "僅支援 Gemini 與本地模型" in resp.json()["text"]


def test_mcp_command_when_mcp_server_unreachable_returns_friendly_text(client, mcp_chatbot):
    """公司的 MCP server 連不上：回友善文字，不退回 RAG、不丟 500。"""
    resp = _post_chat(client, "@mcp 查庫存", mcp_chatbot["id"])

    assert resp.status_code == 200
    assert resp.json()["type"] == "text"
    assert "暫時無法連線" in resp.json()["text"]


@pytest.mark.parametrize("message", ["A12345", "我想查訂單 ORD-500001", "我想查訂單狀態", "請幫我 @mcp 查"])
def test_messages_without_leading_mcp_go_to_rag_even_if_they_look_like_orders(client, monkeypatch, message):
    """不再有訂單專屬的正則分流：沒有以 @mcp 開頭的訊息一律走 RAG + LLM。"""
    from app import main as main_module

    class FakeAgent:
        def generate_answer(self, text, history=None, provider="google", chatbot_id=None, top_k=None, use_rerank=False):
            return f"RAG 回答：{text}", []

    monkeypatch.setattr(main_module, "get_agent", lambda: FakeAgent())

    resp = _post_chat(client, message)

    assert resp.json()["type"] == "text"
    assert resp.json()["text"] == f"RAG 回答：{message}"


@pytest.mark.parametrize("path", ["/api/providers", "/api/widget/config"])
def test_widget_get_endpoints_require_client_id(client, path):
    resp = client.get(path)

    assert resp.status_code == 422
    assert "X-Client-ID" in resp.json()["detail"]


def test_chat_rate_limits_per_chatbot_id(client, monkeypatch):
    """
    chatbot_id 是公開識別碼（widget 原始碼裡看得到），單靠 per-IP 限流擋不住換 IP／多台機器
    打同一個 chatbot_id 的濫用，所以要另外對 chatbot_id 本身也有總量限制。
    """
    from app import main as main_module

    monkeypatch.setattr(main_module, "CHATBOT_RATE_LIMIT_MAX_REQUESTS", 3)
    chatbot_id = "client_chatbot_rate_limit_test"

    for _ in range(3):
        resp = client.post(
            "/api/chat",
            json={"message": "哈囉", "history": [], "provider": "google"},
            headers={"X-Client-ID": chatbot_id},
        )
        assert resp.status_code == 200

    resp = client.post(
        "/api/chat",
        json={"message": "哈囉", "history": [], "provider": "google"},
        headers={"X-Client-ID": chatbot_id},
    )
    assert resp.status_code == 429


def test_chat_rejects_too_long_client_id(client):
    resp = client.post(
        "/api/chat",
        json={"message": "我想查訂單狀態", "history": [], "provider": "google"},
        headers={"X-Client-ID": "x" * 129},
    )

    assert resp.status_code == 422


def test_widget_config_returns_customizable_defaults(client):
    resp = client.get("/api/widget/config", headers=CLIENT_HEADERS)

    assert resp.status_code == 200
    assert resp.json() == {
        "brandName": "線上客服",
        "welcomeMessage": "您好，我是線上客服，可以問我任何產品的規格、特色，或是退換貨政策喔。",
        "logoUrl": None,
        "theme": {
            "primaryColor": "#315b7d",
            "surfaceColor": "#ffffff",
            "textColor": "#17212b",
            "borderRadius": 20,
        },
        "quickReplies": ["無線滑鼠支援多少 DPI？", "退貨要幾天內申請？"],
    }


def test_widget_client_header_is_allowed_by_cors(client):
    allowed_origin = "https://example.com" if "*" in settings.CORS_ORIGINS else settings.CORS_ORIGINS[0]
    resp = client.options(
        "/api/chat",
        headers={
            "Origin": allowed_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,X-Client-ID",
        },
    )

    assert resp.status_code == 200
    assert "x-client-id" in resp.headers["access-control-allow-headers"].lower()
