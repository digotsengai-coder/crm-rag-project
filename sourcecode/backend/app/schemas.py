"""FastAPI 請求/回應格式。前端依 type 欄位決定要 render 哪一種訊息元件。"""
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    # assistant 回答上限比使用者訊息寬鬆：max_new_tokens=512 的生成結果換算中文字數可能超過 500，
    # 這裡限制的是「回傳的歷史紀錄」本身，不是使用者新輸入（那個仍受 ChatRequest.message 500 字限制）。
    content: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    # 上限 500 字：避免超長輸入把 LLM context 塞爆或拖慢生成速度
    message: str = Field(min_length=1, max_length=500)
    # 前端傳回目前對話中「之前幾輪」的訊息，用來讓機器人記得上下文（例如「那電池呢？」）。
    # 只有產品問答（type == "product"）這條路徑會用到；訂單查詢是規則比對，不需要歷史。
    history: List[HistoryTurn] = Field(default_factory=list, max_length=20)
    # 要用哪個 LLM 回答；local 是本地 Qwen3.5-2B（僅限 Apple Silicon 開發機），
    # 其餘是線上付費 API（見 app/providers.py）
    provider: Literal["local", "anthropic", "openai", "google", "xai"] = "google"


class SourceRef(BaseModel):
    text: str
    source: str
    topic: str = ""
    distance: float


class ChatResponse(BaseModel):
    type: str  # "product" | "order" | "text"

    # type == "product" | "text"
    text: Optional[str] = None
    source: Optional[str] = None
    sources: Optional[List[SourceRef]] = None

    # type == "order"
    code: Optional[str] = None
    status: Optional[int] = None
    eta: Optional[str] = None
    items: Optional[str] = None


class QuestionCategory(BaseModel):
    name: str
    count: int
    # 屬於這個主題的原始提問（逐字），前端點長條時展開查看
    questions: List[str] = Field(default_factory=list)


class PeriodSummaryResponse(BaseModel):
    start_date: str
    end_date: str
    question_count: int
    categories: List[QuestionCategory] = Field(default_factory=list)
    # 無意義問題（測試訊息、亂打字、與業務無關的閒聊）：純備查，不需要管理者採取行動
    meaningless_questions: List[str] = Field(default_factory=list)
    # 需商家關注：問題合理但太獨特無法歸類，或機器人明顯答不出來（見 app/summary.py 的
    # NO_INFO_ANSWER 訊號輔助判斷），管理者可能要補充知識庫或人工介入
    needs_merchant_attention: List[str] = Field(default_factory=list)
    # 以「@<MCP 機器人名稱>」開頭的 MCP 指令：獨立一類，不算無意義也不算需商家關注
    mcp_questions: List[str] = Field(default_factory=list)
    summary: str


class ProviderInfo(BaseModel):
    id: str
    label: str
    configured: bool


class WidgetTheme(BaseModel):
    primary_color: str = Field(serialization_alias="primaryColor", pattern=r"^#[0-9a-fA-F]{6}$")
    surface_color: str = Field(serialization_alias="surfaceColor", pattern=r"^#[0-9a-fA-F]{6}$")
    text_color: str = Field(serialization_alias="textColor", pattern=r"^#[0-9a-fA-F]{6}$")
    border_radius: int = Field(serialization_alias="borderRadius", ge=0, le=32)


class WidgetConfig(BaseModel):
    brand_name: str = Field(serialization_alias="brandName", min_length=1, max_length=80)
    welcome_message: str = Field(serialization_alias="welcomeMessage", min_length=1, max_length=500)
    logo_url: Optional[str] = Field(default=None, serialization_alias="logoUrl")
    theme: WidgetTheme
    quick_replies: List[str] = Field(serialization_alias="quickReplies", default_factory=list)


class DocumentInfo(BaseModel):
    # 路徑是純粹給人看/篩選用的顯示欄位，不是身分依據——身分是後端 kb_documents.doc_id
    # （內容的 SHA256 唯一對應），對外 API 完全不會出現這個內部流水號，一律用 path 溝通。
    path: str
    tags: List[str] = Field(default_factory=list)
    chunk_count: int
    # 這次呼叫是否真的重新 embed 過：新增/內容更新固定 True；標籤更新/掛到既有內容
    # （linked）/完全沒變都固定 False。列表查詢（GET）不適用，固定給 None。
    content_changed: Optional[bool] = None
    uploaded_at: Optional[str] = None
    file_size_bytes: Optional[int] = None
    # 伺服器端算出的 SHA256，給前端跟自己算的 client 端雜湊核對用。
    content_hash: Optional[str] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]


class PrecheckItem(BaseModel):
    path: str
    client_sha256: str
    tags: List[str] = Field(default_factory=list)


class PrecheckRequest(BaseModel):
    # 資料夾全量覆蓋模式用：算「這次上傳沒包含到的既有路徑」（見 PrecheckResponse.stale_paths）。
    scope_prefix: Optional[str] = None
    # 上限 200：避免單次預檢請求塞爆，多檔案上傳的前端應自行分批。
    items: List[PrecheckItem] = Field(min_length=1, max_length=200)


class PrecheckResultItem(BaseModel):
    path: str
    # linked：這個內容雜湊命中「別的」既有內容（不管這個路徑本來有沒有紀錄），只需要更新
    # 標籤紀錄指向該內容，不需要重新上傳/重新 embed——取代原本的 duplicate_of／renamed 概念。
    status: Literal["new", "unchanged", "content_changed", "tags_only_changed", "linked"]


class PrecheckResponse(BaseModel):
    items: List[PrecheckResultItem]
    # scope_prefix 底下、這次上傳沒包含到的既有路徑；沒帶 scope_prefix 就固定是空陣列。
    stale_paths: List[str] = Field(default_factory=list)


# ---- 多租戶帳號 / Google 登入 / 公司管理（Phase 1，見 app/auth.py、app/accounts_store.py） ----


class GoogleLoginRequest(BaseModel):
    id_token: str


class AccountInfo(BaseModel):
    id: str
    email: str
    role: Literal["platform_primary", "platform_secondary", "tenant_primary", "tenant_secondary"]
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    # 這個帳號在「某一家公司」的身分（'primary'／'secondary'），只有透過
    # GET /api/admin/accounts?chatbot_id= 查出來的帳號才有值；跟上面的 role（全域角色）
    # 是分開的兩件事，見 accounts_store.list_accounts_for_chatbot() 的說明。
    chatbot_role: Optional[Literal["primary", "secondary"]] = None


class LoginResponse(BaseModel):
    token: str
    account: AccountInfo


def _rerank_available() -> bool:
    # 延遲 import：schemas 被大量模組載入，不要讓它在 import 時就拉進 reranker 的相依套件
    from app.rag.reranker import is_supported

    return is_supported()


class ChatbotInfo(BaseModel):
    id: str
    name: str
    mcp_url: Optional[str] = None
    welcome_message: Optional[str] = None
    quick_replies: Optional[List[str]] = None
    # 只表示有沒有設定 MCP 金鑰；金鑰本身不出現在這個回應（見 GET /api/admin/chatbots/{id}/mcp-token）
    has_mcp_token: bool = False
    # 聊天訊息以「@名稱」開頭時啟動 MCP，這裡是實際生效的名稱（沒設定就是預設的 MCP）。
    mcp_trigger_name: str = "MCP"
    # RAG 檢索設定：k 是送給 LLM 的片段數；rerank_enabled 是這家公司在後台勾選的偏好（存在共用
    # 資料庫），不代表一定會生效。
    rag_top_k: int = 5
    rerank_enabled: bool = False

    # LINE Channel ID 僅供管理端記錄，不參與 Webhook 驗證或 LINE API 呼叫。
    line_channel_id: Optional[str] = None

    # Facebook Page ID 僅供管理端記錄，不參與 Webhook 驗證或 Send API 呼叫。
    facebook_page_id: Optional[str] = None

    # Instagram Business ID 僅供管理端記錄（也是呼叫 Instagram Send API 網址中的 ig 帳號 ID）。
    instagram_business_id: Optional[str] = None

    # 這台「伺服器」能不能做 rerank（總開關、非 Cloud Run、binary 存在，見 reranker.is_supported()）。
    # 不是公司的屬性，但放在每筆公司資料裡，前端不用另外多打一支 API；後台頁面據此決定要不要停用開關。
    rerank_available: bool = Field(default_factory=lambda: _rerank_available())
    created_at: Optional[str] = None
    # 目前登入帳號在這家公司的身分（'primary'／'secondary'），只有 /api/auth/me 對 tenant
    # 角色回傳時才有值；platform 角色沒有「依公司而變」的身分，固定是 None。
    your_role: Optional[Literal["primary", "secondary"]] = None


class MeResponse(BaseModel):
    account: AccountInfo
    chatbots: List[ChatbotInfo]


class ChatbotListResponse(BaseModel):
    chatbots: List[ChatbotInfo]


class McpTokenResponse(BaseModel):
    mcp_token: Optional[str] = None


def _normalize_mcp_trigger_name(value: Optional[str]) -> Optional[str]:
    """
    去掉前後空白與使用者順手打的開頭 @／＠（介面上已經固定顯示 @，兩種都收）；名稱中間不能有空白或 @，
    否則訊息「@名稱 問題」永遠對不上。空字串代表「回到預設 MCP」，原樣保留給 accounts_store 處理。
    """
    if value is None:
        return None
    value = value.strip().lstrip("@＠").strip()
    if any(ch.isspace() or ch in "@＠" for ch in value):
        raise ValueError("MCP 機器人名稱不能包含空白或 @")
    return value


class ChatbotCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    mcp_url: Optional[str] = Field(default=None, max_length=500)
    mcp_token: Optional[str] = Field(default=None, max_length=500)
    welcome_message: Optional[str] = Field(default=None, max_length=500)
    quick_replies: Optional[List[str]] = Field(default=None, max_length=10)
    mcp_trigger_name: Optional[str] = Field(default=None, max_length=20)

    _check_mcp_trigger_name = field_validator("mcp_trigger_name")(_normalize_mcp_trigger_name)


class ChatbotUpdateRequest(BaseModel):
    # 只更新有帶值的欄位；沒帶的欄位維持不變（不是清空），見 accounts_store.update_chatbot()。
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    mcp_url: Optional[str] = Field(default=None, max_length=500)
    # 空字串代表清除金鑰；不帶（None）代表不修改
    mcp_token: Optional[str] = Field(default=None, max_length=500)
    welcome_message: Optional[str] = Field(default=None, max_length=500)
    quick_replies: Optional[List[str]] = Field(default=None, max_length=10)
    # 送給 LLM 的片段數 k（1～10）；不帶＝不變更
    rag_top_k: Optional[int] = Field(default=None, ge=1, le=10)
    # true 只在伺服器支援 rerank 時才能設（否則 400）；false（關閉）任何環境都允許；不帶＝不變更
    rerank_enabled: Optional[bool] = None
    # 「MCP 機器人名稱」：訊息以 @名稱 開頭時啟動 MCP；空字串＝回到預設 MCP；不帶＝不變更
    mcp_trigger_name: Optional[str] = Field(default=None, max_length=20)

    # LINE Messaging API 設定；Channel ID 目前僅供記錄。
    line_channel_id: Optional[str] = Field(default=None, max_length=200)
    line_channel_secret: Optional[str] = Field(default=None, max_length=500)
    line_channel_access_token: Optional[str] = Field(default=None, max_length=2000)

    # Meta 平台（Facebook 粉專 + Instagram 私訊）設定；app_secret／verify_token 是 Meta App 層級
    # 的憑證，兩個管道共用。Page ID／Instagram Business ID 目前僅供記錄。
    facebook_page_id: Optional[str] = Field(default=None, max_length=200)
    facebook_app_secret: Optional[str] = Field(default=None, max_length=500)
    facebook_page_access_token: Optional[str] = Field(default=None, max_length=2000)
    facebook_verify_token: Optional[str] = Field(default=None, max_length=200)
    instagram_business_id: Optional[str] = Field(default=None, max_length=200)
    instagram_access_token: Optional[str] = Field(default=None, max_length=2000)
    # Instagram 這個子產品有自己獨立的 App Secret（跟 facebook_app_secret 不同），
    # 驗證 Instagram 訊息的 Webhook 簽章要用這組，不能沿用主 App 的密鑰。
    instagram_app_secret: Optional[str] = Field(default=None, max_length=500)

    _check_mcp_trigger_name = field_validator("mcp_trigger_name")(_normalize_mcp_trigger_name)


class AccountCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: Literal["platform_primary", "platform_secondary", "tenant_primary", "tenant_secondary"]
    # tenant_* 角色新增時必填（要綁定到哪家公司）；platform_* 角色不需要。
    chatbot_id: Optional[str] = None


class AccountListResponse(BaseModel):
    accounts: List[AccountInfo]


class AuditLogEntry(BaseModel):
    id: int
    actor_email: Optional[str] = None
    action: str
    target_type: str
    target_id: Optional[str] = None
    detail: Optional[Any] = None
    created_at: Optional[str] = None


class AuditLogListResponse(BaseModel):
    entries: List[AuditLogEntry]
