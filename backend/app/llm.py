"""
生成模型（LLM）載入：對應提案流程「根據 RAG 查詢結果給 LLM 回答」中的生成端。

USE_SMALL_MODEL=false（預設）：Qwen2.5-7B-Instruct，4-bit 量化，建議 GPU + 12GB 以上 VRAM。
USE_SMALL_MODEL=true：Qwen2.5-1.5B-Instruct，CPU 也可執行（速度較慢），不需要 bitsandbytes。

模型只在第一次呼叫時載入（lazy loading），第一次呼叫 /api/chat 會需要等待下載與載入模型。
"""
import threading

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from app.config import settings

_tokenizer = None
_model = None

# 同一顆模型不管是「產品問答」還是「當日提問摘要」都會用到，
# 用同一把鎖讓所有 LLM 生成請求排隊，避免併發搶 CPU/GPU。
_generation_lock = threading.Lock()


def get_llm():
    global _tokenizer, _model
    if _model is not None:
        return _tokenizer, _model

    if settings.USE_SMALL_MODEL:
        # device_map="auto" 會用 accelerate 猜測可用記憶體來分配裝置，
        # 在沒有 CUDA 的機器上常會誤判、把部分權重 offload 到硬碟（跑起來極慢甚至出錯）。
        # 明確指定裝置（CPU、或 Apple Silicon 的 MPS）可以避免這個問題。
        if torch.cuda.is_available():
            device, dtype = "cuda", torch.float16
        elif torch.backends.mps.is_available():
            device, dtype = "mps", torch.float16
        else:
            device, dtype = "cpu", torch.float32

        model_name = settings.LLM_MODEL_NAME_SMALL
        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=dtype,
            device_map={"": device},
        )
    else:
        from transformers import BitsAndBytesConfig

        model_name = settings.LLM_MODEL_NAME_FULL
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=bnb_config,
            device_map="auto",
        )

    return _tokenizer, _model


def generate(messages: list[dict], max_new_tokens: int = 512) -> str:
    """給定 chat messages（[{role, content}]），跑一次 LLM 生成並回傳文字。"""
    tokenizer, model = get_llm()

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)

    with _generation_lock:
        output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    generated_ids = output_ids[:, inputs["input_ids"].shape[1]:]
    return tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
