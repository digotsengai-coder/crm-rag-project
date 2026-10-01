"""
繞過 llama-index 官方的 optimum/optimum-onnx 整合套件，直接用 onnxruntime 跑 int8 量化的
multilingual-e5-base，接上 LlamaIndex 的 BaseEmbedding 介面。

為什麼不用官方的 llama-index-embeddings-huggingface-optimum：那個套件依賴的
optimum-onnx 明確要求 transformers<4.58.0，但這個專案其他想用新版 transformers 的套件
（mlx-lm 要求 >=5.0.0）版本完全沒有交集，同一個環境裝不出兩邊都滿足的組合，是硬性衝突、
無解（實測驗證過）。onnxruntime 本身不依賴 transformers 版本，所以繞過 optimum 自己寫這個
類別可以避開衝突。

tokenizer 故意用 `tokenizers`（HuggingFace 斷詞引擎本尊，Rust 實作）直接載入
tokenizer.json，不用 `transformers.AutoTokenizer`：實測光 `from transformers import
AutoTokenizer` 這行就會連帶把 torch 載入進來（不管有沒有用到 GPU），多吃 ~380MB 記憶體，
Cloud Run 預設 512Mi 記憶體會不夠用；`tokenizers` 是獨立的底層套件，不依賴 torch。兩者
對同樣輸入的 tokenize 結果（input_ids／attention_mask）逐位元組驗證過完全一致，不影響
既有 pgvector 索引資料的向量結果。

模型來源：Teradata/multilingual-e5-base 這個 repo 有官方 fp32 模型轉換好的多種精度 ONNX
檔案（https://huggingface.co/Teradata/multilingual-e5-base），這裡用 onnx/model_int8.onnx。
輸出向量維度跟原本的 fp32 版一樣是 768 維（同一個 base 模型量化，架構沒變），不用改動
app/rag/llamaindex_engine.py 的 EMBED_DIM，也不影響既有 pgvector 表結構。

輸入/輸出格式依照該 repo 官方附的 test_local.py 參考程式碼驗證過：
- 輸入只需要 input_ids／attention_mask（不需要 token_type_ids）
- 輸出用 index 1（已經是 pooling 過的句子向量），不是 index 0 的逐 token last_hidden_state
"""
from typing import Any, List, Optional

import numpy as np
from llama_index.core.base.embeddings.base import DEFAULT_EMBED_BATCH_SIZE, BaseEmbedding
from llama_index.core.bridge.pydantic import Field, PrivateAttr

DEFAULT_ONNX_REPO = "Teradata/multilingual-e5-base"
DEFAULT_ONNX_FILENAME = "onnx/model_int8.onnx"


class OnnxInt8Embedding(BaseEmbedding):
    """用 onnxruntime 直接跑 int8 量化 ONNX 模型的 embedding，繞過 optimum。"""

    repo_id: str = Field(default=DEFAULT_ONNX_REPO, description="HuggingFace repo，含 ONNX 檔案與 tokenizer。")
    onnx_filename: str = Field(default=DEFAULT_ONNX_FILENAME, description="repo 內 ONNX 檔案的相對路徑。")
    max_length: int = Field(default=512, description="tokenize 時的最大長度，超過會截斷。", gt=0)
    query_instruction: str = Field(default="query: ", description="查詢文字前綴（e5 非對稱檢索慣例）。")
    text_instruction: str = Field(default="passage: ", description="段落文字前綴（e5 非對稱檢索慣例）。")

    _session: Any = PrivateAttr()
    _tokenizer: Any = PrivateAttr()

    def __init__(
        self,
        repo_id: str = DEFAULT_ONNX_REPO,
        onnx_filename: str = DEFAULT_ONNX_FILENAME,
        max_length: int = 512,
        query_instruction: str = "query: ",
        text_instruction: str = "passage: ",
        embed_batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
        **kwargs: Any,
    ) -> None:
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        onnx_path = hf_hub_download(repo_id=repo_id, filename=onnx_filename)
        session = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        tokenizer = Tokenizer.from_pretrained(repo_id)
        # e5 系列模型沿用 XLM-RoBERTa 斷詞器，"<pad>" 固定是 pad token；
        # enable_padding/enable_truncation 是 tokenizers 套件的設定方式，
        # 對應 AutoTokenizer 呼叫時帶的 padding=True/truncation=True/max_length 參數。
        tokenizer.enable_padding(pad_id=tokenizer.token_to_id("<pad>"), pad_token="<pad>")
        tokenizer.enable_truncation(max_length=max_length)

        super().__init__(
            embed_batch_size=embed_batch_size,
            model_name=repo_id,
            repo_id=repo_id,
            onnx_filename=onnx_filename,
            max_length=max_length,
            query_instruction=query_instruction,
            text_instruction=text_instruction,
            **kwargs,
        )
        self._session = session
        self._tokenizer = tokenizer

    @classmethod
    def class_name(cls) -> str:
        return "OnnxInt8Embedding"

    def _embed(self, texts: List[str]) -> List[List[float]]:
        encoded = self._tokenizer.encode_batch(texts)
        onnx_inputs = {
            "input_ids": np.array([e.ids for e in encoded], dtype=np.int64),
            "attention_mask": np.array([e.attention_mask for e in encoded], dtype=np.int64),
        }
        outputs = self._session.run(None, onnx_inputs)
        embeddings = outputs[1]

        # L2 正規化，維持跟現有 HuggingFaceEmbedding(normalize=True) 一致的行為，確保向量
        # 相似度搜尋的尺度一致；norms 裡的 0（理論上不會發生，防禦性處理）避免除以零。
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1e-12
        return (embeddings / norms).tolist()

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._embed([self.query_instruction + query])[0]

    def _get_text_embedding(self, text: str) -> List[float]:
        return self._embed([self.text_instruction + text])[0]

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self._embed([self.text_instruction + t for t in texts])

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._get_text_embedding(text)
