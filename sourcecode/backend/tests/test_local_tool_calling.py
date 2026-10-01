"""
測試本地模型（Qwen）的 tool calling：<tool_call> 解析、參數轉型、tool 迴圈、必填參數檢查。

迴圈用「假的生成函式」照劇本輸出（格式取自對真實 Qwen3.5-2B-4bit 的實測輸出），
不載入模型；真實模型的行為見 app/providers.py 的說明與手動實測。
"""
import asyncio

import pytest

from app.mcp_chat import _require_arguments
from app.mcp_client import McpTool, McpToolResult
from app.providers import (
    _coerce_argument,
    _parse_local_tool_calls,
    _run_local_tool_loop,
    _to_openai_tool_definition,
)

# 實測 Qwen3.5-2B-4bit 輸出的格式
REAL_OUTPUT = """<tool_call>
<function=search_order>
<parameter=order_id>
ORD-510155
</parameter>
<parameter=phone_number>
980281157
</parameter>
</function>
</tool_call>"""


# ---- 解析 ----

def test_parse_real_qwen_output():
    text, calls = _parse_local_tool_calls(REAL_OUTPUT)

    assert text == ""
    assert len(calls) == 1
    assert calls[0].name == "search_order"
    assert calls[0].arguments == {"order_id": "ORD-510155", "phone_number": "980281157"}


def test_parse_text_before_call_is_kept_and_call_is_extracted():
    text, calls = _parse_local_tool_calls("我來幫您查詢。\n" + REAL_OUTPUT)

    assert text == "我來幫您查詢。"
    assert calls[0].name == "search_order"


def test_parse_plain_answer_has_no_calls():
    text, calls = _parse_local_tool_calls("我們的營業時間是週一到週五。")

    assert text == "我們的營業時間是週一到週五。"
    assert calls == []


def test_parse_multiple_calls_and_multiline_values():
    raw = """<tool_call>
<function=a>
<parameter=note>
第一行
第二行
</parameter>
</function>
</tool_call>
<tool_call>
<function=b>
</function>
</tool_call>"""

    _, calls = _parse_local_tool_calls(raw)

    assert [c.name for c in calls] == ["a", "b"]
    assert calls[0].arguments == {"note": "第一行\n第二行"}
    assert calls[1].arguments == {}


def test_parse_empty_parameter_value_stays_empty_not_invented():
    """實測：缺少電話時模型會輸出空的 parameter；解析要如實保留成空字串，交給必填檢查處理。"""
    raw = """<tool_call>
<function=search_order>
<parameter=order_id>
ORD-1
</parameter>
<parameter=phone_number>
</parameter>
</function>
</tool_call>"""

    _, calls = _parse_local_tool_calls(raw)

    assert calls[0].arguments == {"order_id": "ORD-1", "phone_number": ""}


def test_parse_truncated_output_is_tolerated():
    """模型輸出被 max_tokens 截斷（少了結尾標籤）時不能丟例外。"""
    _, calls = _parse_local_tool_calls("<tool_call>\n<function=search_order>\n<parameter=order_id>\nORD-1\n</parameter>\n")

    assert calls[0].name == "search_order"
    assert calls[0].arguments == {"order_id": "ORD-1"}


def test_parse_does_not_touch_argument_values():
    """參數值不能被改動（例如簡轉繁會改壞 ID 之類的值）。"""
    _, calls = _parse_local_tool_calls("<tool_call>\n<function=f>\n<parameter=id>\nA-简体-1\n</parameter>\n</function>\n</tool_call>")

    assert calls[0].arguments == {"id": "A-简体-1"}


# ---- 參數轉型 ----

@pytest.mark.parametrize(
    "value,schema,expected",
    [
        ("10", {"type": "integer"}, 10),
        ("1.5", {"type": "number"}, 1.5),
        ("true", {"type": "boolean"}, True),
        ("False", {"type": "boolean"}, False),
        ('["a", "b"]', {"type": "array"}, ["a", "b"]),
        ('{"k": 1}', {"type": "object"}, {"k": 1}),
        ("abc", {"type": "string"}, "abc"),
        ("abc", {}, "abc"),
        ("abc", {"type": "integer"}, "abc"),  # 轉不了就維持原字串，讓 server 回報參數錯誤
        ("5", {"anyOf": [{"type": "integer"}, {"type": "null"}]}, 5),  # Optional[int]
        ("[bad", {"type": "array"}, "[bad"),
    ],
)
def test_coerce_argument(value, schema, expected):
    assert _coerce_argument(value, schema) == expected


# ---- 迴圈 ----

def _tools():
    return [McpTool(
        "search_order", "依訂單編號與電話查詢",
        {"type": "object",
         "properties": {"order_id": {"type": "string"}, "limit": {"type": "integer"}},
         "required": ["order_id"]},
    )]


class ScriptedGenerate:
    """依序回傳劇本輸出，並記錄每次收到的對話與 tools。"""

    def __init__(self, *outputs):
        self._outputs = list(outputs)
        self.calls = []

    async def __call__(self, conversation, tool_definitions, max_new_tokens):
        self.calls.append((list(conversation), tool_definitions))
        return self._outputs.pop(0)


def _run(generate, call_tool, max_rounds=3, postprocess=lambda t: t):
    return asyncio.run(_run_local_tool_loop(
        generate, [{"role": "user", "content": "問題"}], _tools(), call_tool, 256, max_rounds, postprocess
    ))


def test_loop_calls_tool_feeds_result_back_and_returns_answer():
    seen = []

    async def call_tool(name, arguments):
        seen.append((name, arguments))
        return McpToolResult(text='{"status": "shipped"}')

    generate = ScriptedGenerate(
        "<tool_call>\n<function=search_order>\n<parameter=order_id>\nORD-1\n</parameter>\n<parameter=limit>\n5\n</parameter>\n</function>\n</tool_call>",
        "訂單已出貨",
    )

    answer, records = _run(generate, call_tool)

    assert answer == "訂單已出貨"
    assert seen == [("search_order", {"order_id": "ORD-1", "limit": 5})]  # limit 依 schema 轉成 int
    assert [(r.name, r.arguments, r.is_error) for r in records] == [("search_order", {"order_id": "ORD-1", "limit": 5}, False)]
    # 第二次生成看得到 assistant 的 tool_calls 與 role=tool 的結果
    second_conversation = generate.calls[1][0]
    assert second_conversation[-2]["tool_calls"][0]["function"] == {"name": "search_order", "arguments": {"order_id": "ORD-1", "limit": 5}}
    assert second_conversation[-1] == {"role": "tool", "content": '{"status": "shipped"}'}
    # tools 以 OpenAI 風格定義交給 template
    assert generate.calls[0][1] == [_to_openai_tool_definition(_tools()[0])]


def test_loop_without_tool_call_returns_answer_directly():
    async def call_tool(name, arguments):
        raise AssertionError("不該呼叫 tool")

    answer, records = _run(ScriptedGenerate("您好，請問有什麼可以幫您？"), call_tool)

    assert answer == "您好，請問有什麼可以幫您？"
    assert records == []


def test_loop_unknown_tool_is_not_forwarded():
    called = []

    async def call_tool(name, arguments):
        called.append(name)
        return McpToolResult(text="x")

    generate = ScriptedGenerate("<tool_call>\n<function=delete_everything>\n</function>\n</tool_call>", "抱歉，我做不到")

    answer, records = _run(generate, call_tool)

    assert called == []
    assert records[0].is_error is True
    assert "delete_everything" in generate.calls[1][0][-1]["content"]


def test_loop_is_bounded_and_last_generation_has_no_tools():
    async def call_tool(name, arguments):
        return McpToolResult(text="資料")

    call = "<tool_call>\n<function=search_order>\n<parameter=order_id>\nX\n</parameter>\n</function>\n</tool_call>"
    generate = ScriptedGenerate(call, call, call, "用現有資訊回答")

    answer, records = _run(generate, call_tool, max_rounds=3)

    assert answer == "用現有資訊回答"
    assert len(records) == 3
    assert all(tools for _, tools in generate.calls[:3])  # 前三輪有提供 tools
    assert generate.calls[3][1] is None  # 用完輪數後的最後一次生成不再提供 tools


def test_postprocess_applies_to_final_answer_only_not_to_tool_arguments():
    seen = []

    async def call_tool(name, arguments):
        seen.append(arguments)
        return McpToolResult(text="ok")

    generate = ScriptedGenerate(
        "<tool_call>\n<function=search_order>\n<parameter=order_id>\nA-简体\n</parameter>\n</function>\n</tool_call>",
        "简体答案",
    )

    answer, _ = _run(generate, call_tool, postprocess=lambda t: t.replace("简体", "繁體"))

    assert answer == "繁體答案"
    assert seen == [{"order_id": "A-简体"}]  # 參數維持原樣


# ---- 必填參數檢查（mcp_chat._require_arguments） ----

def _checked(call_tool):
    return _require_arguments(_tools(), call_tool)


def test_missing_required_argument_is_rejected_without_calling_server():
    """實測缺少必填參數時小模型會拿空字串去呼叫 tool；要在送去 server 之前擋下並請它反問顧客。"""
    called = []

    async def call_tool(name, arguments):
        called.append(arguments)
        return McpToolResult(text="x")

    result = asyncio.run(_checked(call_tool)("search_order", {"order_id": ""}))

    assert called == []
    assert result.is_error is True
    assert "order_id" in result.text and "向顧客詢問" in result.text


def test_missing_key_entirely_is_also_rejected():
    async def call_tool(name, arguments):
        raise AssertionError

    result = asyncio.run(_checked(call_tool)("search_order", {}))

    assert result.is_error is True


def test_complete_arguments_pass_through_and_optional_may_be_empty():
    async def call_tool(name, arguments):
        return McpToolResult(text=f"收到 {arguments}")

    result = asyncio.run(_checked(call_tool)("search_order", {"order_id": "ORD-1"}))  # limit 選填，沒帶

    assert result.is_error is False
    assert "ORD-1" in result.text


def test_unknown_tool_name_is_passed_through_to_the_normal_error_path():
    async def call_tool(name, arguments):
        return McpToolResult(text="unknown", is_error=True)

    result = asyncio.run(_checked(call_tool)("not_a_tool", {}))

    assert result.text == "unknown"
