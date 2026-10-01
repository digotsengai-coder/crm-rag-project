"""
測試 app/providers.py 的 tool calling：JSON Schema 轉換、Gemini tool 迴圈。

沒有對真實的 Gemini API 做端到端驗證（測試環境沒有金鑰、也不該花費真實額度）：
迴圈用「假的 ChatSession」搭配 SDK 真實的 proto 物件（Part／FunctionCall／Candidate）驅動，
確認我們讀取模型回應、回填 function_response 的方式與 SDK 的資料結構一致。
"""
import asyncio
import json
from types import SimpleNamespace

import google.generativeai as genai
import pytest

from app import providers
from app.mcp_client import McpTool, McpToolResult
from app.providers import (
    ToolCallingNotSupported,
    _run_gemini_tool_loop,
    _to_gemini_function_declaration,
    generate_with_tools,
    supports_tool_calling,
)

protos = genai.protos


def _response(*parts):
    return SimpleNamespace(candidates=[protos.Candidate(content=protos.Content(parts=list(parts)))])


def _call(name, **args):
    return protos.Part(function_call=protos.FunctionCall(name=name, args=args))


def _text(text):
    return protos.Part(text=text)


class FakeChat:
    """依序回傳預先設定好的回應，並記錄每次送出的內容與參數。"""

    def __init__(self, *responses):
        self._responses = list(responses)
        self.sent: list[tuple] = []

    async def send_message_async(self, content, **kwargs):
        self.sent.append((content, kwargs))
        return self._responses.pop(0)


def _tools(*names):
    return [McpTool(name=n, description=f"{n} 說明", input_schema={}) for n in names]


def _run(chat, tools, call_tool, max_rounds=3, message="問題"):
    return asyncio.run(_run_gemini_tool_loop(chat, message, tools, call_tool, 512, max_rounds))


def test_model_calls_tool_then_answers_with_tool_result():
    seen = []

    async def call_tool(name, arguments):
        seen.append((name, arguments))
        return McpToolResult(text='{"status": "shipped"}')

    chat = FakeChat(_response(_call("get_order", order_id="A123")), _response(_text("您的訂單已出貨")))

    answer, records = _run(chat, _tools("get_order"), call_tool)

    assert answer == "您的訂單已出貨"
    assert seen == [("get_order", {"order_id": "A123"})]
    assert [(r.name, r.arguments, r.is_error) for r in records] == [("get_order", {"order_id": "A123"}, False)]
    # 第二次送出的內容是 function_response，帶著 tool 的結果
    sent_parts = chat.sent[1][0]
    assert sent_parts[0].function_response.name == "get_order"
    assert dict(sent_parts[0].function_response.response) == {"result": '{"status": "shipped"}'}


def test_no_tool_call_returns_text_directly():
    async def call_tool(name, arguments):
        raise AssertionError("不該呼叫 tool")

    answer, records = _run(FakeChat(_response(_text("直接回答"))), _tools("get_order"), call_tool)

    assert answer == "直接回答"
    assert records == []


def test_tool_error_is_sent_back_as_error_payload():
    async def call_tool(name, arguments):
        return McpToolResult(text="查無訂單", is_error=True)

    chat = FakeChat(_response(_call("get_order", order_id="Z")), _response(_text("查不到這筆訂單")))

    answer, records = _run(chat, _tools("get_order"), call_tool)

    assert records[0].is_error is True
    assert dict(chat.sent[1][0][0].function_response.response) == {"error": "查無訂單"}


def test_hallucinated_tool_name_is_not_forwarded_to_server():
    called = []

    async def call_tool(name, arguments):
        called.append(name)
        return McpToolResult(text="x")

    chat = FakeChat(_response(_call("delete_everything")), _response(_text("抱歉，我做不到")))

    answer, records = _run(chat, _tools("get_order"), call_tool)

    assert called == []
    assert records[0].is_error is True
    assert "delete_everything" in dict(chat.sent[1][0][0].function_response.response)["error"]


def test_multiple_calls_in_one_turn_are_all_executed():
    async def call_tool(name, arguments):
        return McpToolResult(text=f"{name} 結果")

    chat = FakeChat(_response(_call("a"), _call("b")), _response(_text("完成")))

    answer, records = _run(chat, _tools("a", "b"), call_tool)

    assert [r.name for r in records] == ["a", "b"]
    assert len(chat.sent[1][0]) == 2  # 兩個 function_response 一起送回


def test_loop_is_bounded_and_last_round_disables_function_calling():
    """模型一直想呼叫 tool 時不能無限迴圈：最後一輪關掉 function calling，強迫它給出答案。"""
    async def call_tool(name, arguments):
        return McpToolResult(text="資料")

    chat = FakeChat(
        _response(_call("a")), _response(_call("a")), _response(_call("a")),  # 一直要求呼叫
        _response(_text("用現有資訊回答")),
    )

    answer, records = _run(chat, _tools("a"), call_tool, max_rounds=3)

    assert answer == "用現有資訊回答"
    assert len(records) == 3
    assert "tool_config" not in chat.sent[1][1] and "tool_config" not in chat.sent[2][1]
    assert chat.sent[3][1]["tool_config"] == {"function_calling_config": {"mode": "NONE"}}


def test_empty_candidates_return_empty_text():
    async def call_tool(name, arguments):
        raise AssertionError

    chat = FakeChat(SimpleNamespace(candidates=[]))

    assert _run(chat, _tools("a"), call_tool) == ("", [])


# ---- JSON Schema 轉換 ----

def test_pydantic_style_schema_is_converted_to_gemini_subset():
    schema = {
        "$defs": {"Item": {"properties": {"sku": {"title": "Sku", "type": "string"}, "qty": {"default": 1, "type": "integer"}},
                           "required": ["sku"], "title": "Item", "type": "object"}},
        "properties": {
            "keyword": {"title": "Keyword", "type": "string"},
            "limit": {"default": 10, "title": "Limit", "type": "integer"},
            "note": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None, "title": "Note"},
            "tags": {"anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}]},
            "item": {"anyOf": [{"$ref": "#/$defs/Item"}, {"type": "null"}], "default": None},
        },
        "required": ["keyword"], "title": "searchArguments", "type": "object",
    }

    declaration = _to_gemini_function_declaration(McpTool("search", "搜尋", schema))

    params = declaration["parameters"]
    assert params["required"] == ["keyword"]
    assert params["properties"]["note"] == {"type": "string", "nullable": True}
    assert params["properties"]["tags"] == {"type": "array", "items": {"type": "string"}, "nullable": True}
    item = params["properties"]["item"]
    assert item["nullable"] is True and item["required"] == ["sku"]
    assert item["properties"]["qty"] == {"type": "integer"}
    text = json.dumps(declaration)
    for forbidden in ("$defs", "$ref", "anyOf", "title", "default"):
        assert forbidden not in text
    # 真的餵給 SDK：不能被拒絕
    genai.GenerativeModel("gemini-test", tools=[{"function_declarations": [declaration]}])


def test_tool_without_arguments_omits_parameters():
    declaration = _to_gemini_function_declaration(
        McpTool("ping", "無參數", {"properties": {}, "title": "pingArguments", "type": "object"})
    )

    assert "parameters" not in declaration
    genai.GenerativeModel("gemini-test", tools=[{"function_declarations": [declaration]}])


def test_self_referencing_schema_does_not_recurse_forever():
    schema = {"$defs": {"Node": {"type": "object", "properties": {"child": {"$ref": "#/$defs/Node"}}}},
              "type": "object", "properties": {"root": {"$ref": "#/$defs/Node"}}}

    declaration = _to_gemini_function_declaration(McpTool("tree", "d", schema))

    assert declaration["parameters"]["properties"]["root"]["type"] == "object"


# ---- generate_with_tools 的接線 ----

def test_only_google_and_local_support_tool_calling():
    assert supports_tool_calling("google") is True
    assert supports_tool_calling("local") is True
    for provider in ("anthropic", "openai", "xai"):
        assert supports_tool_calling(provider) is False


def test_unsupported_provider_raises():
    async def call_tool(name, arguments):
        return McpToolResult(text="x")

    with pytest.raises(ToolCallingNotSupported):
        asyncio.run(generate_with_tools("openai", [{"role": "user", "content": "hi"}], [], call_tool))


def test_generate_with_tools_wires_prompt_history_and_tools(monkeypatch):
    captured = {}
    fake_chat = FakeChat(_response(_text("答案")))

    class FakeModel:
        def __init__(self, model_name, system_instruction=None, tools=None):
            captured.update(model_name=model_name, system=system_instruction, tools=tools)

        def start_chat(self, history):
            captured["history"] = history
            return fake_chat

    monkeypatch.setattr(providers, "_get_config", lambda provider: {"api_key": "k"})
    monkeypatch.setattr(genai, "configure", lambda api_key: None)
    monkeypatch.setattr(genai, "GenerativeModel", FakeModel)

    async def call_tool(name, arguments):
        return McpToolResult(text="x")

    messages = [
        {"role": "system", "content": "系統提示"},
        {"role": "user", "content": "上一題"},
        {"role": "assistant", "content": "上一答"},
        {"role": "user", "content": "這一題"},
    ]
    answer, records = asyncio.run(generate_with_tools("google", messages, _tools("get_order"), call_tool))

    assert answer == "答案"
    assert captured["system"] == "系統提示"
    assert captured["history"] == [
        {"role": "user", "parts": ["上一題"]},
        {"role": "model", "parts": ["上一答"]},
    ]
    assert fake_chat.sent[0][0] == "這一題"
    assert captured["tools"][0]["function_declarations"][0]["name"] == "get_order"
