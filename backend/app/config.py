"""
專案設定值。讀取 .env（沒有的話用預設值），對應：
- USE_SMALL_MODEL: 是否改用較小的 LLM（不需要 GPU）
- EMBEDDING_MODEL_NAME / LLM_MODEL_NAME_*: 對應提案中「Embedding 模型」與「生成模型」的技術選型
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    USE_SMALL_MODEL: bool = os.getenv("USE_SMALL_MODEL", "false").lower() == "true"

    EMBEDDING_MODEL_NAME: str = "intfloat/multilingual-e5-base"
    LLM_MODEL_NAME_FULL: str = "Qwen/Qwen2.5-7B-Instruct"
    LLM_MODEL_NAME_SMALL: str = "Qwen/Qwen2.5-1.5B-Instruct"

    TOP_K: int = 3

    # Chroma 向量資料庫持久化目錄；正式上線建議指向獨立磁碟路徑並定期備份
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")

    # 對話紀錄 SQLite 檔案路徑，供未來「管理者摘要當日提問」功能使用
    CHAT_LOG_DB_PATH: str = os.getenv("CHAT_LOG_DB_PATH", "./chat_log.db")

    # 訂單資料 SQLite 檔案路徑；之後要接真實 ERP/訂單系統，把 orders.py 的查詢函式改成呼叫外部 API 即可
    ORDERS_DB_PATH: str = os.getenv("ORDERS_DB_PATH", "./orders.db")

    # 多輪對話最多保留幾輪（一輪 = 一則使用者訊息 + 一則機器人回覆），避免 context 太長讓 1.5B 模型變慢
    MAX_HISTORY_TURNS: int = 4

    CORS_ORIGINS: list = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]

    # 線上付費 LLM 的 API key／模型名稱設定檔（不進 git，範本見 llm_keys.example.json）
    LLM_KEYS_PATH: str = os.getenv("LLM_KEYS_PATH", "./llm_keys.json")

    # RAG 檢索引擎："custom"（自訂 Chroma + 手寫檢索，預設）或 "llamaindex"（用 LlamaIndex 的 VectorStoreIndex）
    # 兩套引擎介面相同，見 app/rag/engine.py；語意拆分規則兩套共用（app/rag/product_parser.py）。
    RAG_ENGINE: str = os.getenv("RAG_ENGINE", "custom")

    # LlamaIndex 引擎的索引持久化目錄，跟 custom 引擎的 CHROMA_PERSIST_DIR 分開存放
    LLAMAINDEX_PERSIST_DIR: str = os.getenv("LLAMAINDEX_PERSIST_DIR", "./llamaindex_data")

    # 兩套引擎的「有沒有查到答案」距離門檻分開設定，因為分數尺度不同、不能共用同一個數字
    # （custom 用原始 L2 距離，llamaindex 用 1 - 相似度分數，經驗值需要各自校準）
    RAG_NO_INFO_THRESHOLDS: dict = {"custom": 0.30, "llamaindex": 0.30}


settings = Settings()
