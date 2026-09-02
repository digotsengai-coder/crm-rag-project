"""
生成模型（LLM）載入：對應提案流程「根據 RAG 查詢結果給 LLM 回答」中的生成端。

USE_SMALL_MODEL=false（預設）：Qwen2.5-7B-Instruct，4-bit 量化，建議 GPU + 12GB 以上 VRAM。
USE_SMALL_MODEL=true：Qwen2.5-1.5B-Instruct，CPU 也可執行（速度較慢），不需要 bitsandbytes。

模型只在第一次呼叫時載入（lazy loading），第一次呼叫 /api/chat 會需要等待下載與載入模型。
"""
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from app.config import settings

_tokenizer = None
_model = None


def get_llm():
    global _tokenizer, _model
    if _model is not None:
        return _tokenizer, _model

    if settings.USE_SMALL_MODEL:
        model_name = settings.LLM_MODEL_NAME_SMALL
        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto",
        )
    else:
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
