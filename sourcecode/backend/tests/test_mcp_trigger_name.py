"""
「MCP 機器人名稱」設定（chatbots.mcp_trigger_name）的後台 API：
- 沒設定時預設 MCP（訊息以 @MCP 開頭啟動）。
- 可以改成任意名稱；前後空白與使用者順手打的開頭 @ 會被去掉；中間有空白或 @ 會被拒絕。
- 不帶代表不變更；空字串代表回到預設。
聊天流程實際用這個名稱分流的行為見 test_mcp_chat.py。
"""
import pytest
from fastapi.testclient import TestClient

from app import accounts_store
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _put(client, token, chatbot_id, body):
    return client.put(
        f"/api/admin/chatbots/{chatbot_id}", json=body, headers={"Authorization": f"Bearer {token}"}
    )


def test_new_chatbot_defaults_to_mcp(test_chatbot):
    assert test_chatbot["mcp_trigger_name"] == "MCP"


def test_update_trigger_name_is_persisted_and_returned(client, platform_token, test_chatbot):
    resp = _put(client, platform_token, test_chatbot["id"], {"mcp_trigger_name": "阿柴"})

    assert resp.status_code == 200
    assert resp.json()["mcp_trigger_name"] == "阿柴"
    assert accounts_store.get_chatbot(test_chatbot["id"])["mcp_trigger_name"] == "阿柴"


@pytest.mark.parametrize("raw,expected", [("  阿柴  ", "阿柴"), ("@阿柴", "阿柴"), ("＠阿柴", "阿柴")])
def test_trigger_name_is_normalized(client, platform_token, test_chatbot, raw, expected):
    resp = _put(client, platform_token, test_chatbot["id"], {"mcp_trigger_name": raw})

    assert resp.status_code == 200
    assert resp.json()["mcp_trigger_name"] == expected


@pytest.mark.parametrize("bad", ["阿 柴", "阿@柴", "a" * 21])
def test_invalid_trigger_name_is_rejected(client, platform_token, test_chatbot, bad):
    resp = _put(client, platform_token, test_chatbot["id"], {"mcp_trigger_name": bad})

    assert resp.status_code == 422
    assert accounts_store.get_chatbot(test_chatbot["id"])["mcp_trigger_name"] == "MCP"


def test_update_without_trigger_name_keeps_it(client, platform_token, test_chatbot):
    _put(client, platform_token, test_chatbot["id"], {"mcp_trigger_name": "阿柴"})

    resp = _put(client, platform_token, test_chatbot["id"], {"name": "Pytest Renamed"})

    assert resp.json()["mcp_trigger_name"] == "阿柴"


@pytest.mark.parametrize("empty", ["", "@", "  "])
def test_empty_trigger_name_resets_to_default(client, platform_token, test_chatbot, empty):
    _put(client, platform_token, test_chatbot["id"], {"mcp_trigger_name": "阿柴"})

    resp = _put(client, platform_token, test_chatbot["id"], {"mcp_trigger_name": empty})

    assert resp.status_code == 200
    assert resp.json()["mcp_trigger_name"] == "MCP"
