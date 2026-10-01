import json
import logging
import os
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore
from app.config import settings

logger = logging.getLogger("corp-backend.firebase")

_firebase_app: Optional[firebase_admin.App] = None
_db_client = None


def initialize_firebase() -> Optional[firebase_admin.App]:
    """
    初始化 Firebase Admin SDK。
    優先順序：
    1. FIREBASE_CREDENTIALS_PATH (檔案路徑)
    2. FIREBASE_CREDENTIALS_JSON (JSON 字串)
    3. GOOGLE_APPLICATION_CREDENTIALS (標準 GCP 環境變數)
    4. GCP 預設憑證 (Application Default Credentials / GCP Cloud Run 權限)
    """
    global _firebase_app, _db_client

    if _firebase_app is not None:
        return _firebase_app

    # 避免重複初始化預設 App
    if firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        _db_client = firestore.client()
        logger.info("已取得既有 Firebase Admin SDK 實例。")
        return _firebase_app

    cred = None
    cred_source = None

    # 1. 檢查檔案路徑憑證
    cred_path = settings.FIREBASE_CREDENTIALS_PATH or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and os.path.exists(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            cred_source = f"檔案憑證: {cred_path}"
        except Exception as e:
            logger.error(f"無法載入 Firebase 憑證檔案 ({cred_path}): {e}")

    # 2. 檢查 JSON 字串憑證
    if cred is None and settings.FIREBASE_CREDENTIALS_JSON:
        try:
            cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
            cred = credentials.Certificate(cred_dict)
            cred_source = "JSON 字串憑證"
        except Exception as e:
            logger.error(f"無法解析 FIREBASE_CREDENTIALS_JSON: {e}")

    # 3. 嘗試使用預設憑證 (Application Default Credentials)
    if cred is None:
        try:
            cred = credentials.ApplicationDefault()
            cred_source = "GCP Application Default Credentials (ADC)"
        except Exception as e:
            logger.warning(f"無法載入 Application Default Credentials: {e}")

    # 4. 執行初始化
    options = {}
    project_id = (
        settings.GCP_PROJECT_ID
        or os.getenv("GCP_PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("GCP_PROJECT")
    )
    if project_id:
        options["projectId"] = project_id

    try:
        if cred is not None:
            _firebase_app = firebase_admin.initialize_app(cred, options)
            logger.info(f"Firebase Admin SDK 初始化成功 ({cred_source})")
        else:
            # 在無憑證情況下嘗試僅憑 project_id 初始化 (適用於 emulator 模式)
            if os.getenv("FIRESTORE_EMULATOR_HOST"):
                _firebase_app = firebase_admin.initialize_app(options=options)
                logger.info("Firebase Admin SDK 於 Emulator 模式下初始化成功。")
            else:
                logger.warning("未偵測到有效 Firebase 憑證，將於執行時嘗試延遲存取。")
                return None

        _db_client = firestore.client()
        return _firebase_app
    except Exception as e:
        logger.error(f"Firebase Admin SDK 初始化失敗: {e}")
        return None


def get_db():
    """
    取得 Firestore Client 實例。
    若尚未初始化，會嘗試自動執行初始化。
    """
    global _db_client
    if _db_client is not None:
        return _db_client

    initialize_firebase()
    if _db_client is None:
        # 嘗試直接呼叫 firestore.client() (若環境中設定了 FIRESTORE_EMULATOR_HOST 等)
        try:
            _db_client = firestore.client()
            return _db_client
        except Exception as e:
            logger.error(f"取得 Firestore client 失敗: {e}")
            raise RuntimeError(
                "Firestore 客戶端未初始化。請確認已設定 FIREBASE_CREDENTIALS_PATH、"
                "FIREBASE_CREDENTIALS_JSON 或 GCP 憑證環境變數。"
            ) from e
    return _db_client


def is_firebase_initialized() -> bool:
    """
    檢查 Firebase SDK 是否已順利初始化。
    """
    return len(firebase_admin._apps) > 0 or _db_client is not None
