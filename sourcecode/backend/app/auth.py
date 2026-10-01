"""
Google 登入 + session 驗證 + RBAC dependencies。

Session 傳輸走 `Authorization: Bearer <token>` header（不是 cookie）——延續現有 API 完全
stateless、header-based 的風格（見 main.py 的 _require_client_id / X-Client-ID），也避免
allow_credentials／cross-origin cookie 的額外複雜度；main.py 現有的
CORSMiddleware(allow_headers=["*"]) 已經涵蓋 Authorization header，不用改 CORS 設定。

RBAC dependencies 沿用 main.py._require_client_id 一樣的 sync function + Header()/Depends()
寫法，維持專案既有慣例。
"""
from fastapi import Depends, Header, HTTPException

from app import accounts_store
from app.config import settings


# 允許本機時鐘與 Google 伺服器有幾秒誤差：token 的 iat／nbf 是 Google 伺服器的時間，
# 本機（尤其是沒開自動校時的開發機）時鐘稍慢就會被判成「Token used too early」而登入失敗。
# 只放寬 10 秒，不影響 token 的有效期限判斷；正式環境（Cloud Run）時鐘有校時，用不到這個容差。
GOOGLE_TOKEN_CLOCK_SKEW_SECONDS = 10


def verify_google_id_token(id_token_str: str) -> str:
    """
    驗證 Google ID token，回傳 email。驗證失敗（簽章不對、過期、aud 不符）一律拋
    ValueError，讓呼叫端統一轉成 401——不把 google-auth 底層的例外型別外洩到路由層。

    獨立成一個函式（不是直接寫在路由裡）方便測試 monkeypatch：pytest 沒辦法真的跟 Google
    要一個有效 ID token，測試會直接 monkeypatch 這個函式回傳固定 email。
    """
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    try:
        payload = google_id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=GOOGLE_TOKEN_CLOCK_SKEW_SECONDS,
        )
    except Exception as e:
        raise ValueError(f"Google ID token 驗證失敗：{e}")
    email = payload.get("email")
    if not email:
        raise ValueError("Google ID token 沒有 email 欄位。")
    return email


def require_session(
    authorization: str | None = Header(default=None),
) -> dict:
    """
    讀 Authorization: Bearer <token> header，查 accounts_store.get_account_by_session，
    查無或過期回 401。回傳的 dict 是 accounts_store._row_to_account() 的格式
    （id/email/role/created_by/created_at）。
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少或格式錯誤的 Authorization header。")
    token = authorization[len("Bearer "):].strip()
    if not token:
        raise HTTPException(status_code=401, detail="缺少或格式錯誤的 Authorization header。")
    account = accounts_store.get_account_by_session(token)
    if account is None:
        raise HTTPException(status_code=401, detail="登入已失效，請重新登入。")
    return account


def require_platform_role(account: dict = Depends(require_session)) -> dict:
    """在 require_session() 基礎上檢查角色是 platform_*，否則 403。"""
    if account["role"] not in accounts_store.PLATFORM_ROLES:
        raise HTTPException(status_code=403, detail="此操作僅限平台維運帳號。")
    return account


def require_chatbot_access(chatbot_id: str, account: dict = Depends(require_session)) -> dict:
    """
    chatbot_id 來自 route path/query（FastAPI 依參數名稱注入，main.py 的路由固定用
    `chatbot_id` 這個名字）。檢查目前帳號是 platform 角色，或在 chatbot_accounts 裡有
    該 chatbot_id 的綁定，否則 403。
    """
    if not accounts_store.account_has_chatbot_access(account, chatbot_id):
        raise HTTPException(status_code=403, detail="沒有這家公司的存取權限。")
    return account
