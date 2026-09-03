"""
線上付費 LLM 供應商分派層：讓 /api/chat 除了本地 1.5B/7B 模型外，
也能選擇呼叫 Anthropic Claude、OpenAI、Google Gemini、xAI Grok 的線上 API。

API key／要用的模型名稱存在 settings.LLM_KEYS_PATH 指到的 JSON 檔（預設 backend/llm_keys.json，
不進 git，範本在 backend/llm_keys.example.json）。這個檔案跟程式碼分開放，
是因為 key 是機密資料，不該跟一般設定（.env）混在一起，方便單獨管理/排除在版控外。

所有 generate_xxx() 函式吃同一種 messages 格式：[{"role": "system"|"user"|"assistant", "content": str}]，
跟本地模型（app/llm.py 的 generate()）介面一致，agent.py 呼叫時不需要知道背後是哪家供應商。
"""
import json
import threading

from app.config import settings
from app.llm import generate as generate_local

PROVIDERS = ["local", "anthropic", "openai", "google", "xai"]

_keys_cache = None
_keys_lock = threading.Lock()


class ProviderNotConfigured(Exception):
    """對應 provider 在 llm_keys.json 裡沒有設定 api_key。"""


def _load_keys() -> dict:
    global _keys_cache
    with _keys_lock:
        if _keys_cache is None:
            try:
                with open(settings.LLM_KEYS_PATH, encoding="utf-8") as f:
                    _keys_cache = json.load(f)
            except FileNotFoundError:
                _keys_cache = {}
        return _keys_cache


def is_configured(provider: str) -> bool:
    if provider == "local":
        return True
    return bool(_load_keys().get(provider, {}).get("api_key"))


def _get_config(provider: str) -> dict:
    config = _load_keys().get(provider) or {}
    if not config.get("api_key"):
        raise ProviderNotConfigured(
            f"尚未設定 {provider} 的 API key，請在 backend/llm_keys.json 填入後重啟後端。"
        )
    return config


def _split_system(messages: list[dict]):
    """回傳 (system_prompt, 其餘 messages)；Anthropic/Gemini 的 system prompt 是獨立參數，不放在 messages 陣列裡。"""
    system_prompt = ""
    rest = []
    for m in messages:
        if m["role"] == "system":
            system_prompt = m["content"]
        else:
            rest.append(m)
    return system_prompt, rest


def generate_anthropic(messages: list[dict], max_new_tokens: int) -> str:
    import anthropic

    config = _get_config("anthropic")
    system_prompt, rest = _split_system(messages)
    client = anthropic.Anthropic(api_key=config["api_key"])
    response = client.messages.create(
        model=config.get("model", "claude-sonnet-4-5-20250929"),
        system=system_prompt,
        messages=rest,
        max_tokens=max_new_tokens,
    )
    return "".join(block.text for block in response.content if block.type == "text")


def generate_openai(messages: list[dict], max_new_tokens: int) -> str:
    from openai import OpenAI

    config = _get_config("openai")
    client = OpenAI(api_key=config["api_key"])
    response = client.chat.completions.create(
        model=config.get("model", "gpt-4o-mini"),
        messages=messages,
        max_tokens=max_new_tokens,
    )
    return response.choices[0].message.content


def generate_xai(messages: list[dict], max_new_tokens: int) -> str:
    """xAI Grok 的 API 相容 OpenAI SDK 格式，只是換一個 base_url。"""
    from openai import OpenAI

    config = _get_config("xai")
    client = OpenAI(api_key=config["api_key"], base_url="https://api.x.ai/v1")
    response = client.chat.completions.create(
        model=config.get("model", "grok-4"),
        messages=messages,
        max_tokens=max_new_tokens,
    )
    return response.choices[0].message.content


def generate_google(messages: list[dict], max_new_tokens: int) -> str:
    import google.generativeai as genai

    config = _get_config("google")
    genai.configure(api_key=config["api_key"])
    system_prompt, rest = _split_system(messages)
    model = genai.GenerativeModel(
        config.get("model", "gemini-2.0-flash"),
        system_instruction=system_prompt or None,
    )

    if not rest:
        return ""

    *history, last = rest
    chat = model.start_chat(history=[
        {"role": "model" if h["role"] == "assistant" else "user", "parts": [h["content"]]}
        for h in history
    ])
    response = chat.send_message(
        last["content"],
        generation_config=genai.types.GenerationConfig(max_output_tokens=max_new_tokens),
    )
    return response.text


_DISPATCH = {
    "local": lambda messages, max_new_tokens: generate_local(messages, max_new_tokens=max_new_tokens),
    "anthropic": generate_anthropic,
    "openai": generate_openai,
    "google": generate_google,
    "xai": generate_xai,
}


def generate_with_provider(provider: str, messages: list[dict], max_new_tokens: int = 512) -> str:
    if provider not in _DISPATCH:
        raise ValueError(f"未知的 LLM provider：{provider}")
    return _DISPATCH[provider](messages, max_new_tokens)
