import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    應用程式設定類別，從環境變數或 .env 檔案載入設定。
    """
    APP_NAME: str = "Corp Backend API"
    ENV: str = "development"
    PORT: int = 8001
    API_V1_STR: str = "/api/v1"

    # GCP & Firebase 設定
    GCP_PROJECT_ID: Optional[str] = None
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None

    # MCP endpoint 的 Bearer 金鑰：/mcp（唯讀 tools，給聊天後端 LLM 使用）與
    # /mcp-admin（管理／寫入 tools，聊天後端不使用）各自獨立一把，避免拿到唯讀金鑰
    # 就能呼叫寫入 tool。任何一把沒設定時，對應 endpoint 一律拒絕（fail closed）。
    MCP_API_KEY: Optional[str] = None
    MCP_ADMIN_API_KEY: Optional[str] = None

    # MCP 的 Host header 檢查（SDK 內建的 DNS rebinding 防護）。預設只放行 localhost，本機開發沒問題，
    # 但部署到 Cloud Run 後 Host 是 *.run.app，會被回 421 "Invalid Host header"，所有已通過認證的
    # MCP 請求都失敗。設定這個（逗號分隔，例如 "my-svc-123.europe-west1.run.app"）就只放行這些 Host；
    # 沒設定且在 Cloud Run 上（有 K_SERVICE）時停用此檢查，改由 Bearer 金鑰把關，見 main.py。
    MCP_ALLOWED_HOSTS: Optional[str] = None

    # 產品圖片 Storage URL
    PRODUCT_IMAGE_BASE_URL: str = "https://storage.googleapis.com/crm_squard_product_image"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# 建立全域 Settings 實例
settings = Settings()
