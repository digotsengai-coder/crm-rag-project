from fastapi import APIRouter
from app.config import settings
from app.firebase_client import is_firebase_initialized
from app.schemas import HealthStatus

router = APIRouter(tags=["Health Check"])


@router.get("/health", response_model=HealthStatus, summary="服務健康檢查")
def health_check():
    """
    檢查 corp-backend 服務狀態及 Firebase Firestore 連線狀態。
    """
    firebase_ok = is_firebase_initialized()
    status_str = "healthy" if firebase_ok else "degraded"
    details_str = "Firebase SDK 已就緒。" if firebase_ok else "Firebase 未初始化（缺憑證或專案設定）。"

    return HealthStatus(
        status=status_str,
        app_name=settings.APP_NAME,
        firebase_connected=firebase_ok,
        details=details_str
    )
