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

    CORS_ORIGINS: list = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]


settings = Settings()
