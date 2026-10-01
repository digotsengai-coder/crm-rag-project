"""
多租戶帳號核心邏輯：chatbots（商家服務）/ accounts（帳號）/ chatbot_accounts（帳號-公司
綁定）/ sessions（登入 session）/ audit_log（稽核紀錄）這五張表的 schema 與存取函式。

架構比照 app/rag/documents_store.py 的風格：raw SQL（sqlalchemy.text()）、模組層級
_schema_ready flag 做冪等 CREATE TABLE IF NOT EXISTS，不用 ORM／migration 框架，
跟現有專案的資料層慣例一致；跟 documents_store.py 共用 app/db.py 的同一個 Engine
（同一個 Postgres 資料庫）。

兩層帳號角色（accounts.role）：
- platform_primary / platform_secondary：服務方（平台維運）帳號，看得到所有商家服務。
- tenant_primary / tenant_secondary：商家帳號，只看得到自己綁定（chatbot_accounts）的公司；
  一個 tenant_primary 可以綁多家 chatbot，tenant_secondary 權限跟 primary 相同，差別只在
  「誰能新增/移除誰」（見 main.py 的 /api/admin/accounts 權限判斷）。

session 只存 token 的 SHA-256 雜湊（不存明文），避免資料庫外洩就等於外洩所有人的登入憑證；
明文 token 只在 create_session() 當下回傳給呼叫端一次。
"""
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text as sql_text

from app.config import settings
from app.db import get_engine

_schema_ready = False


def _ensure_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    engine = get_engine()
    with engine.begin() as conn:
        # pgcrypto 提供 gen_random_uuid()；Supabase/多數雲端 Postgres 預設就有裝，
        # CREATE EXTENSION IF NOT EXISTS 是冪等操作，沒有權限時忽略即可（多半已經裝好）。
        try:
            conn.execute(sql_text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        except Exception:
            pass
        conn.execute(sql_text(
            """
            CREATE TABLE IF NOT EXISTS chatbots (
                id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name       TEXT NOT NULL,
                mcp_url    TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        ))
        # chatbots 表已經有真實資料（商家自己建立的公司），不能用「砍掉重建」的方式加欄位；
        # 用 ALTER TABLE ADD COLUMN IF NOT EXISTS 冪等地補上 welcome_message
        # （聊天機器人開頭語，取代 main.py 原本寫死的字串，見 widget_config()）。
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS welcome_message TEXT"
        ))
        # quick_replies：開場快速提問清單（原本 chat-widget 寫死 3 題），存成 JSON 陣列字串
        # （TEXT 欄位），比另開一張子表簡單，反正只是一份不需要單獨查詢/索引的小清單。
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS quick_replies TEXT"
        ))
        # mcp_token：這家公司 MCP server 的 Bearer 金鑰（backend 呼叫該公司 mcp_url 時帶上）。
        # 必須能還原成明文才能送出，所以不能像 session token 那樣只存 hash；因此絕不放進
        # 任何列表／一般回應，只有專用的 get_chatbot_mcp_token() 與其管理端點能讀出來。
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS mcp_token TEXT"
        ))
        # LINE Messaging API 設定
        # line_channel_id 目前僅供管理端記錄，不參與 Webhook 驗證或 LINE API 呼叫。
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS line_channel_id TEXT"
        ))
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS line_channel_secret TEXT"
        ))
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS line_channel_access_token TEXT"
        ))
        # Meta 平台（Facebook 粉專 + Instagram 私訊，共用同一個 webhook）設定。
        # facebook_app_secret／facebook_verify_token 其實是「這個 Meta App」層級的憑證，
        # Facebook 與 Instagram 共用；欄位名沿用第一版的 facebook_* 命名，不因為 Instagram
        # 加入而改名（這個資料庫本機與正式環境共用，一貫只用 ADD COLUMN 累加，不對既有
        # 欄位改名，見上面 mcp_token 的說明）。
        # facebook_page_id 僅供管理端記錄，不參與驗證；page_access_token 呼叫 Facebook Send API。
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS facebook_page_id TEXT"
        ))
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS facebook_app_secret TEXT"
        ))
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS facebook_page_access_token TEXT"
        ))
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS facebook_verify_token TEXT"
        ))
        # instagram_business_id 僅供管理端記錄（也是呼叫 Instagram Send API 時網址裡的 ig 帳號 ID）；
        # instagram_access_token 呼叫 Instagram Send API 回覆用。Verify Token 沿用上面的
        # facebook_verify_token（Meta App 層級，兩個管道共用）；但簽章驗證用的 App Secret
        # 不共用——Meta 在 App 後台建立「Instagram API」這個子產品時會產生獨立的
        # Instagram App ID／App Secret，Instagram 的 webhook 請求是用這組密鑰簽的，
        # 不是主 App 的 facebook_app_secret，所以另外存一欄。
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS instagram_business_id TEXT"
        ))
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS instagram_access_token TEXT"
        ))
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS instagram_app_secret TEXT"
        ))
        # RAG 檢索設定（後台「Chatbot 設定」頁可調）。兩個欄位都允許 NULL，NULL 代表「用系統預設」
        # （rag_top_k → settings.RAG_DEFAULT_TOP_K；rerank_enabled → 關閉），所以既有公司不需要回填。
        # 這個資料庫本機與正式環境共用，正式環境跑的舊版程式只會 SELECT 自己認得的欄位，加欄位不影響它。
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS rag_top_k INTEGER"
        ))
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS rerank_enabled BOOLEAN"
        ))
        # mcp_trigger_name：聊天訊息以「@名稱」開頭時啟動 MCP（後台「MCP 機器人名稱」）。允許 NULL／空字串，
        # 代表用預設的 DEFAULT_MCP_TRIGGER_NAME，所以既有公司不需要回填。
        conn.execute(sql_text(
            "ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS mcp_trigger_name TEXT"
        ))
        conn.execute(sql_text(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email      TEXT NOT NULL UNIQUE,
                role       TEXT NOT NULL CHECK (
                    role IN ('platform_primary', 'platform_secondary', 'tenant_primary', 'tenant_secondary')
                ),
                created_by UUID REFERENCES accounts(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        ))
        conn.execute(sql_text(
            """
            CREATE TABLE IF NOT EXISTS chatbot_accounts (
                account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                chatbot_id UUID NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (account_id, chatbot_id)
            )
            """
        ))
        # role（'primary' / 'secondary'）：同一個帳號可以是 A 公司的主帳號、同時是 B 公司的
        # 協作帳號，這種「依公司而變」的身分沒辦法存在 accounts.role（那是帳號的全域屬性），
        # 只能存在這張綁定關係表上。舊資料（這個欄位還沒存在前建立的綁定）用該帳號當時的
        # 全域角色回填一次：tenant_primary → primary，其餘（含 platform 帳號、tenant_secondary）
        # → secondary，是「猜」不是精確還原，回填後可以再手動調整。
        conn.execute(sql_text(
            "ALTER TABLE chatbot_accounts ADD COLUMN IF NOT EXISTS role TEXT"
        ))
        conn.execute(sql_text(
            """
            UPDATE chatbot_accounts ca SET role = COALESCE(
                (SELECT CASE WHEN a.role = 'tenant_primary' THEN 'primary' ELSE 'secondary' END
                 FROM accounts a WHERE a.id = ca.account_id),
                'secondary'
            )
            WHERE ca.role IS NULL
            """
        ))
        conn.execute(sql_text(
            "ALTER TABLE chatbot_accounts ALTER COLUMN role SET DEFAULT 'secondary'"
        ))
        conn.execute(sql_text(
            "ALTER TABLE chatbot_accounts ALTER COLUMN role SET NOT NULL"
        ))
        conn.execute(sql_text(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                expires_at TIMESTAMPTZ NOT NULL
            )
            """
        ))
        conn.execute(sql_text(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id               BIGSERIAL PRIMARY KEY,
                actor_account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
                action           TEXT NOT NULL,
                target_type      TEXT NOT NULL,
                target_id        TEXT,
                detail           JSONB,
                created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        ))
        conn.execute(sql_text(
            "CREATE INDEX IF NOT EXISTS sessions_account_id_idx ON sessions (account_id)"
        ))
        conn.execute(sql_text(
            "CREATE INDEX IF NOT EXISTS chatbot_accounts_chatbot_id_idx ON chatbot_accounts (chatbot_id)"
        ))
    _schema_ready = True
    bootstrap_initial_platform_admins()


PLATFORM_ROLES = {"platform_primary", "platform_secondary"}
TENANT_ROLES = {"tenant_primary", "tenant_secondary"}


def _row_to_account(row) -> dict:
    return {
        "id": str(row.id),
        "email": row.email,
        "role": row.role,
        "created_by": str(row.created_by) if row.created_by is not None else None,
        "created_at": row.created_at.isoformat() if row.created_at is not None else None,
        # 只有 list_accounts_for_chatbot() 這種帶了 chatbot_accounts.role 的查詢才有值；
        # role 是帳號的全域角色，chatbot_role 是「在這家公司」的身分（primary／secondary），
        # 兩者可能不一樣（例如管理者帳號建立了這家公司，全域 role 是 platform_primary，
        # chatbot_role 卻是 primary）。
        "chatbot_role": getattr(row, "chatbot_role", None),
    }


def get_account_by_email(email: str) -> Optional[dict]:
    _ensure_schema()
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sql_text("SELECT id, email, role, created_by, created_at FROM accounts WHERE email = :email"),
            {"email": email},
        ).fetchone()
    return _row_to_account(row) if row is not None else None


def get_account_by_id(account_id: str) -> Optional[dict]:
    _ensure_schema()
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sql_text("SELECT id, email, role, created_by, created_at FROM accounts WHERE id = :id"),
            {"id": account_id},
        ).fetchone()
    return _row_to_account(row) if row is not None else None


def create_account(email: str, role: str, created_by: Optional[str]) -> dict:
    """新增一個帳號（次帳號/次開發者新增立即生效，不用寄信確認）。email 全域唯一。"""
    _ensure_schema()
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            sql_text(
                """
                INSERT INTO accounts (email, role, created_by)
                VALUES (:email, :role, :created_by)
                RETURNING id, email, role, created_by, created_at
                """
            ),
            {"email": email, "role": role, "created_by": created_by},
        ).fetchone()
    return _row_to_account(row)


def delete_account(account_id: str) -> bool:
    """刪除帳號；ON DELETE CASCADE 會連帶刪掉 chatbot_accounts／sessions，
    達成「移除次帳號時立刻讓對方 session 失效」（不是等 token 自然過期）。"""
    _ensure_schema()
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            sql_text("DELETE FROM accounts WHERE id = :id RETURNING id"), {"id": account_id}
        ).fetchone()
    return row is not None


def list_platform_accounts() -> list[dict]:
    """給「管理者帳號」頁籤用：只回傳 platform_primary／platform_secondary 這兩種角色，
    不含任何商家帳號（商家帳號一定是透過 chatbot_accounts 綁定，跟這裡完全分開查詢）。"""
    _ensure_schema()
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sql_text(
                "SELECT id, email, role, created_by, created_at FROM accounts "
                "WHERE role IN ('platform_primary', 'platform_secondary') ORDER BY created_at"
            )
        ).fetchall()
    return [_row_to_account(r) for r in rows]


def list_accounts_for_chatbot(chatbot_id: str) -> list[dict]:
    """給「公司設定→管理帳號」用：回傳綁定這一家 chatbot_id 的帳號（不含其他公司的協作
    帳號）——修正原本 list_accounts_visible_to() 對 platform 角色回傳「全部帳號」，導致
    公司設定頁看到其他公司帳號混在一起的問題。不特別排除管理者角色：管理者帳號預設不會被
    綁定任何公司（一般管理者天生就不會出現在這份清單），但如果是管理者自己建立了這家公司
    （見 main.py create_chatbot()），或被明確加為協作帳號，就應該正常顯示、正常能被增減，
    不該被角色濾掉。"""
    _ensure_schema()
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sql_text(
                """
                SELECT a.id, a.email, a.role, a.created_by, a.created_at, ca.role AS chatbot_role
                FROM accounts a
                JOIN chatbot_accounts ca ON ca.account_id = a.id
                WHERE ca.chatbot_id = :chatbot_id
                ORDER BY a.created_at
                """
            ),
            {"chatbot_id": chatbot_id},
        ).fetchall()
    return [_row_to_account(r) for r in rows]


def bind_chatbot(account_id: str, chatbot_id: str, role: str = "secondary") -> None:
    """role：這個帳號在**這家公司**的身分（'primary' 或 'secondary'），跟帳號的全域
    accounts.role 是分開的兩件事——同一個帳號可以是 A 公司的 primary、同時是 B 公司的
    secondary。已經綁定過時用新值覆蓋 role（例如把協作帳號升成共同主帳號），不是單純忽略。
    """
    _ensure_schema()
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sql_text(
                """
                INSERT INTO chatbot_accounts (account_id, chatbot_id, role)
                VALUES (:account_id, :chatbot_id, :role)
                ON CONFLICT (account_id, chatbot_id) DO UPDATE SET role = EXCLUDED.role
                """
            ),
            {"account_id": account_id, "chatbot_id": chatbot_id, "role": role},
        )


def unbind_chatbot(account_id: str, chatbot_id: str) -> None:
    _ensure_schema()
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sql_text(
                "DELETE FROM chatbot_accounts WHERE account_id = :account_id AND chatbot_id = :chatbot_id"
            ),
            {"account_id": account_id, "chatbot_id": chatbot_id},
        )


def account_has_chatbot_access(account: dict, chatbot_id: str) -> bool:
    """platform 角色對任何公司都有存取權；tenant 角色要查 chatbot_accounts 有沒有綁定。"""
    if account["role"] in PLATFORM_ROLES:
        return True
    _ensure_schema()
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sql_text(
                "SELECT 1 FROM chatbot_accounts WHERE account_id = :account_id AND chatbot_id = :chatbot_id"
            ),
            {"account_id": account["id"], "chatbot_id": chatbot_id},
        ).fetchone()
    return row is not None


def get_chatbot_role(account_id: str, chatbot_id: str) -> Optional[str]:
    """查這個帳號在這家公司的身分（'primary'／'secondary'），沒綁定回 None。只回答「這家
    公司」的身分，不管帳號的全域角色——呼叫端如果是 platform 帳號，通常不用查這個
    （platform 對任何公司本來就有完整存取權，見 account_has_chatbot_access）。"""
    _ensure_schema()
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sql_text(
                "SELECT role FROM chatbot_accounts WHERE account_id = :account_id AND chatbot_id = :chatbot_id"
            ),
            {"account_id": account_id, "chatbot_id": chatbot_id},
        ).fetchone()
    return row.role if row is not None else None


def is_chatbot_primary(account: dict, chatbot_id: str) -> bool:
    """這個帳號能不能管理（新增/移除）這家公司的其他協作帳號：platform 角色永遠可以；
    tenant 角色要是這家公司的 primary 才行（secondary 看得到協作帳號清單，但不能增減）。"""
    if account["role"] in PLATFORM_ROLES:
        return True
    return get_chatbot_role(account["id"], chatbot_id) == "primary"


# 沒設定「MCP 機器人名稱」時的觸發詞：訊息以 @MCP 開頭（忽略大小寫）就啟動 MCP。
DEFAULT_MCP_TRIGGER_NAME = "MCP"

# has_mcp_token 只表示「有沒有設定」，金鑰本身不放進一般查詢結果（見 _ensure_schema 的說明）。
_HAS_MCP_TOKEN_SQL = "(mcp_token IS NOT NULL AND mcp_token <> '') AS has_mcp_token"


def _row_to_chatbot(row) -> dict:
    return {
        "id": str(row.id),
        "name": row.name,
        "mcp_url": row.mcp_url,
        "welcome_message": row.welcome_message,
        "quick_replies": json.loads(row.quick_replies) if row.quick_replies else None,
        "has_mcp_token": bool(row.has_mcp_token),
        # 一律回傳「實際生效」的名稱（沒設定就是預設值），前端與 /api/chat 不用各自處理空值
        "mcp_trigger_name": row.mcp_trigger_name or DEFAULT_MCP_TRIGGER_NAME,
        # NULL（從沒設定過）→ 系統預設；k 是「送給 LLM 的片段數」，見 settings.RAG_DEFAULT_TOP_K
        "rag_top_k": row.rag_top_k or settings.RAG_DEFAULT_TOP_K,
        "rerank_enabled": bool(row.rerank_enabled),
        "line_channel_id": getattr(row, "line_channel_id", None),
        "line_channel_secret": getattr(row, "line_channel_secret", None),
        "line_channel_access_token": getattr(row, "line_channel_access_token", None),
        "facebook_page_id": getattr(row, "facebook_page_id", None),
        "facebook_app_secret": getattr(row, "facebook_app_secret", None),
        "facebook_page_access_token": getattr(row, "facebook_page_access_token", None),
        "facebook_verify_token": getattr(row, "facebook_verify_token", None),
        "instagram_business_id": getattr(row, "instagram_business_id", None),
        "instagram_access_token": getattr(row, "instagram_access_token", None),
        "instagram_app_secret": getattr(row, "instagram_app_secret", None),
        "created_at": row.created_at.isoformat() if row.created_at is not None else None,
        # 只有透過 list_chatbots_visible_to() 查出來的公司才有這個欄位（SELECT 裡有多帶
        # your_role）；get_chatbot()／create_chatbot()／update_chatbot() 回傳的公司資訊
        # 沒有「查詢者身分」這個概念，getattr 拿不到就是 None，不是每個呼叫端都要改。
        "your_role": getattr(row, "your_role", None),
    }


def create_chatbot(
    name: str, mcp_url: Optional[str], welcome_message: Optional[str] = None,
    quick_replies: Optional[list[str]] = None, mcp_token: Optional[str] = None,
    mcp_trigger_name: Optional[str] = None,
) -> dict:
    _ensure_schema()
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            sql_text(
                """
                INSERT INTO chatbots (name, mcp_url, welcome_message, quick_replies, mcp_token, mcp_trigger_name)
                VALUES (:name, :mcp_url, :welcome_message, :quick_replies, :mcp_token, :mcp_trigger_name)
                RETURNING id, name, mcp_url, welcome_message, quick_replies, rag_top_k, rerank_enabled, mcp_trigger_name,
                          created_at, """
            + _HAS_MCP_TOKEN_SQL
            ),
            {
                "name": name, "mcp_url": mcp_url, "welcome_message": welcome_message,
                "quick_replies": json.dumps(quick_replies) if quick_replies is not None else None,
                "mcp_token": mcp_token or None,
                "mcp_trigger_name": mcp_trigger_name or None,
            },
        ).fetchone()
    return _row_to_chatbot(row)


def update_chatbot(
    chatbot_id: str, name: Optional[str], mcp_url: Optional[str], welcome_message: Optional[str] = None,
    quick_replies: Optional[list[str]] = None, mcp_token: Optional[str] = None,
    rag_top_k: Optional[int] = None, rerank_enabled: Optional[bool] = None,
    mcp_trigger_name: Optional[str] = None,
    line_channel_id: Optional[str] = None,
    line_channel_secret: Optional[str] = None,
    line_channel_access_token: Optional[str] = None,
    facebook_page_id: Optional[str] = None,
    facebook_app_secret: Optional[str] = None,
    facebook_page_access_token: Optional[str] = None,
    facebook_verify_token: Optional[str] = None,
    instagram_business_id: Optional[str] = None,
    instagram_access_token: Optional[str] = None,
    instagram_app_secret: Optional[str] = None,
) -> Optional[dict]:
    """
    只更新有帶值的欄位（None 代表「這次沒有要改這個欄位」，不是「要清空」）——
    公司資訊頁面可能只改名稱、只改 mcp_url、只改 welcome_message／quick_replies，或同時改，
    呼叫端不用先查目前值再整包送回來。quick_replies 是清單，先序列化成 JSON 字串再跟其他
    欄位一樣用 COALESCE 判斷「這次有沒有要改」。
    mcp_token 也是同樣規則；要清除金鑰時傳空字串（None 代表不改）。
    rag_top_k／rerank_enabled 同樣是 None＝不改；rerank_enabled 傳 False 是「明確關閉」，
    COALESCE 只在參數為 NULL 時才保留舊值，False 不會被當成「沒帶」。
    mcp_trigger_name 同樣 None＝不改；空字串會存成空值，讀出時回到預設的 DEFAULT_MCP_TRIGGER_NAME。
    """
    _ensure_schema()
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            sql_text(
                """
                UPDATE chatbots
                SET name = COALESCE(:name, name),
                    mcp_url = COALESCE(:mcp_url, mcp_url),
                    welcome_message = COALESCE(:welcome_message, welcome_message),
                    quick_replies = COALESCE(:quick_replies, quick_replies),
                    mcp_token = COALESCE(:mcp_token, mcp_token),
                    rag_top_k = COALESCE(:rag_top_k, rag_top_k),
                    rerank_enabled = COALESCE(:rerank_enabled, rerank_enabled),
                    mcp_trigger_name = COALESCE(:mcp_trigger_name, mcp_trigger_name),
                    line_channel_id = COALESCE(:line_channel_id, line_channel_id),
                    line_channel_secret = COALESCE(:line_channel_secret, line_channel_secret),
                    line_channel_access_token = COALESCE(:line_channel_access_token, line_channel_access_token),
                    facebook_page_id = COALESCE(:facebook_page_id, facebook_page_id),
                    facebook_app_secret = COALESCE(:facebook_app_secret, facebook_app_secret),
                    facebook_page_access_token = COALESCE(:facebook_page_access_token, facebook_page_access_token),
                    facebook_verify_token = COALESCE(:facebook_verify_token, facebook_verify_token),
                    instagram_business_id = COALESCE(:instagram_business_id, instagram_business_id),
                    instagram_access_token = COALESCE(:instagram_access_token, instagram_access_token),
                    instagram_app_secret = COALESCE(:instagram_app_secret, instagram_app_secret)
                WHERE id = :id
                RETURNING id, name, mcp_url, welcome_message, quick_replies, rag_top_k, rerank_enabled, mcp_trigger_name,
                          line_channel_id, line_channel_secret, line_channel_access_token,
                          facebook_page_id, facebook_app_secret, facebook_page_access_token, facebook_verify_token,
                          instagram_business_id, instagram_access_token, instagram_app_secret,
                          created_at, """
            + _HAS_MCP_TOKEN_SQL
            ),
            {
                "id": chatbot_id, "name": name, "mcp_url": mcp_url, "welcome_message": welcome_message,
                "quick_replies": json.dumps(quick_replies) if quick_replies is not None else None,
                "mcp_token": mcp_token,
                "rag_top_k": rag_top_k, "rerank_enabled": rerank_enabled,
                "mcp_trigger_name": mcp_trigger_name,
                "line_channel_id": line_channel_id,
                "line_channel_secret": line_channel_secret,
                "line_channel_access_token": line_channel_access_token,
                "facebook_page_id": facebook_page_id,
                "facebook_app_secret": facebook_app_secret,
                "facebook_page_access_token": facebook_page_access_token,
                "facebook_verify_token": facebook_verify_token,
                "instagram_business_id": instagram_business_id,
                "instagram_access_token": instagram_access_token,
                "instagram_app_secret": instagram_app_secret,
            },
        ).fetchone()
    return _row_to_chatbot(row) if row is not None else None


def get_chatbot(chatbot_id: str) -> Optional[dict]:
    _ensure_schema()
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sql_text(
                "SELECT id, name, mcp_url, welcome_message, quick_replies, rag_top_k, rerank_enabled, mcp_trigger_name, "
                "line_channel_id, line_channel_secret, line_channel_access_token, "
                "facebook_page_id, facebook_app_secret, facebook_page_access_token, facebook_verify_token, "
                "instagram_business_id, instagram_access_token, instagram_app_secret, created_at, "
                + _HAS_MCP_TOKEN_SQL + " FROM chatbots WHERE id = :id"
            ),
            {"id": chatbot_id},
        ).fetchone()
    return _row_to_chatbot(row) if row is not None else None


def get_chatbot_mcp_token(chatbot_id: str) -> Optional[str]:
    """
    唯一會讀出 MCP 金鑰明文的函式：只給兩個地方用——backend 呼叫該公司 MCP server 時帶上，
    以及管理端點讓有權限的帳號查看。沒設定（NULL 或空字串）一律回 None。
    """
    _ensure_schema()
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sql_text("SELECT mcp_token FROM chatbots WHERE id = :id"), {"id": chatbot_id}
        ).fetchone()
    return (row.mcp_token or None) if row is not None else None


def delete_chatbot(chatbot_id: str) -> bool:
    """
    硬刪除公司：chatbot_accounts 靠 ON DELETE CASCADE 自動清掉綁定紀錄；RAG 文件/向量
    不是外鍵關聯（documents_store 的 kb_documents.chatbot_id 沒有實體 FK，避免兩個模組
    互相依賴對方的 schema），呼叫端要自己另外呼叫 documents_store.purge_chatbot()。
    """
    _ensure_schema()
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            sql_text("DELETE FROM chatbots WHERE id = :id RETURNING id"), {"id": chatbot_id}
        ).fetchone()
    return row is not None


def list_chatbots_visible_to(account: dict) -> list[dict]:
    """platform 角色回全部（沒有「這家公司的身分」這個概念，your_role 固定 None）；
    tenant 角色經 chatbot_accounts join 回自己綁定的，附帶 your_role（'primary'／
    'secondary'）讓前端可以依公司分別顯示「主帳號」還是「協作帳號」，不是看帳號的
    全域角色（accounts.role）——同一個帳號在不同公司的 your_role 可能不一樣。"""
    _ensure_schema()
    engine = get_engine()
    if account["role"] in PLATFORM_ROLES:
        sql = sql_text(
            "SELECT id, name, mcp_url, welcome_message, quick_replies, rag_top_k, rerank_enabled, mcp_trigger_name, line_channel_id, "
            "facebook_page_id, instagram_business_id, created_at, "
            + _HAS_MCP_TOKEN_SQL + ", NULL AS your_role FROM chatbots ORDER BY created_at"
        )
        params = {}
    else:
        sql = sql_text(
            """
            SELECT c.id, c.name, c.mcp_url, c.welcome_message, c.quick_replies, c.rag_top_k, c.rerank_enabled, c.mcp_trigger_name,
                   c.line_channel_id, c.facebook_page_id, c.instagram_business_id, c.created_at,
                   (c.mcp_token IS NOT NULL AND c.mcp_token <> '') AS has_mcp_token,
                   ca.role AS your_role
            FROM chatbots c
            JOIN chatbot_accounts ca ON ca.chatbot_id = c.id
            WHERE ca.account_id = :account_id
            ORDER BY c.created_at
            """
        )
        params = {"account_id": account["id"]}
    with engine.connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_chatbot(r) for r in rows]


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(account_id: str) -> str:
    """建立一個新 session，回傳明文 token 給呼叫端（僅此一次，DB 只存 hash）。"""
    _ensure_schema()
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.SESSION_TTL_HOURS)
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sql_text(
                "INSERT INTO sessions (token_hash, account_id, expires_at) VALUES (:h, :account_id, :exp)"
            ),
            {"h": token_hash, "account_id": account_id, "exp": expires_at},
        )
    return token


def get_account_by_session(token: str) -> Optional[dict]:
    """雜湊比對 + 檢查 expires_at；查無或已過期一律回 None（呼叫端統一回 401，不用分辨原因，
    避免洩漏「token 格式對但過期了」這種細節給攻擊者）。"""
    _ensure_schema()
    token_hash = _hash_token(token)
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sql_text(
                """
                SELECT a.id, a.email, a.role, a.created_by, a.created_at
                FROM sessions s JOIN accounts a ON a.id = s.account_id
                WHERE s.token_hash = :h AND s.expires_at > now()
                """
            ),
            {"h": token_hash},
        ).fetchone()
    return _row_to_account(row) if row is not None else None


def revoke_session(token: str) -> None:
    _ensure_schema()
    token_hash = _hash_token(token)
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(sql_text("DELETE FROM sessions WHERE token_hash = :h"), {"h": token_hash})


def record_audit(
    actor_account_id: Optional[str], action: str, target_type: str, target_id: Optional[str] = None,
    detail: Optional[dict] = None,
) -> None:
    """稽核紀錄：誰（actor_account_id）對什麼（target_type/target_id）做了什麼（action）。
    detail 是自由格式的補充資訊（例如上傳文件的路徑），存 JSONB。"""
    _ensure_schema()
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sql_text(
                """
                INSERT INTO audit_log (actor_account_id, action, target_type, target_id, detail)
                VALUES (:actor_account_id, :action, :target_type, :target_id, :detail)
                """
            ),
            {
                "actor_account_id": actor_account_id,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "detail": _to_jsonb(detail),
            },
        )


def _to_jsonb(detail: Optional[dict]):
    import json

    return json.dumps(detail) if detail is not None else None


def _row_to_audit_entry(row) -> dict:
    return {
        "id": row.id,
        "actor_email": row.actor_email,
        "action": row.action,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "detail": row.detail,
        "created_at": row.created_at.isoformat() if row.created_at is not None else None,
    }


def list_audit_log_for_chatbot(chatbot_id: str, limit: int = 100) -> list[dict]:
    """
    查一家公司相關的稽核紀錄：target_type='chatbot' 時 target_id 本身就是 chatbot_id；
    'kb_document' 跟部分 'account' 動作（新增/刪除次帳號）則是把 chatbot_id 存在 detail
    這個 JSONB 欄位裡（見 main.py 各個 record_audit() 呼叫點），所以兩種都要比對，才不會漏掉
    「新增/刪除這家公司的協作帳號」這類紀錄。
    """
    _ensure_schema()
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sql_text(
                """
                SELECT al.id, a.email AS actor_email, al.action, al.target_type, al.target_id,
                       al.detail, al.created_at
                FROM audit_log al
                LEFT JOIN accounts a ON a.id = al.actor_account_id
                WHERE al.target_id = :chatbot_id OR al.detail->>'chatbot_id' = :chatbot_id
                ORDER BY al.created_at DESC
                LIMIT :limit
                """
            ),
            {"chatbot_id": chatbot_id, "limit": limit},
        ).fetchall()
    return [_row_to_audit_entry(r) for r in rows]


def bootstrap_initial_platform_admins() -> None:
    """
    解決「雞生蛋」的 bootstrap 問題：一開始 accounts 表沒有任何帳號，沒人能登入。
    只在 accounts 表完全是空的時候，把 settings.INITIAL_PLATFORM_ADMIN_EMAILS 列出的
    email 建成 platform_primary；一次性、冪等（表有資料後就不會再跑）。
    這個函式由 _ensure_schema() 在確認 schema 建立完成後自動呼叫，不需要呼叫端另外處理。
    """
    if not settings.INITIAL_PLATFORM_ADMIN_EMAILS:
        return
    engine = get_engine()
    with engine.connect() as conn:
        count = conn.execute(sql_text("SELECT count(*) FROM accounts")).scalar_one()
    if count > 0:
        return
    for email in settings.INITIAL_PLATFORM_ADMIN_EMAILS:
        with engine.begin() as conn:
            conn.execute(
                sql_text(
                    """
                    INSERT INTO accounts (email, role, created_by) VALUES (:email, 'platform_primary', NULL)
                    ON CONFLICT (email) DO NOTHING
                    """
                ),
                {"email": email},
            )
