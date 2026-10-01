export type AccountRole =
  | "platform_primary"
  | "platform_secondary"
  | "tenant_primary"
  | "tenant_secondary";

export type ChatbotRole = "primary" | "secondary";

export interface Account {
  id: string;
  email: string;
  role: AccountRole;
  created_by: string | null;
  created_at: string;
  // 這個帳號在「某一家公司」的身分，只有依 chatbot_id 查出來的帳號才有值；
  // 跟上面全域的 role 是分開的兩件事（同一帳號在不同公司可能不一樣）。
  chatbot_role?: ChatbotRole | null;
}

export interface ChatbotInfo {
  id: string;
  name: string;
  mcp_url: string | null;
  welcome_message: string | null;
  quick_replies: string[] | null;
  // 只表示有沒有設定 MCP 金鑰，金鑰本身不會出現在這個型別（見 getChatbotMcpToken）。
  has_mcp_token?: boolean;
  // 「MCP 機器人名稱」：聊天訊息以 @名稱 開頭時啟動 MCP，後端一律回傳實際生效的名稱（預設 MCP）。
  mcp_trigger_name?: string;
  // RAG 檢索設定：k 是送給 LLM 的片段數（預設 5）；rerank_enabled 是這家公司勾選的偏好。
  rag_top_k?: number;
  rerank_enabled?: boolean;
  // LINE Channel ID 僅供管理端記錄；Secret / Access Token 不由一般 ChatbotInfo 回傳。
  line_channel_id?: string | null;
  // Facebook Page ID 僅供管理端記錄；App Secret / Page Access Token / Verify Token 不由一般 ChatbotInfo 回傳。
  facebook_page_id?: string | null;
  // Instagram Business ID 僅供管理端記錄；Access Token 不由一般 ChatbotInfo 回傳。
  instagram_business_id?: string | null;
  // 「伺服器」能不能做 rerank（正式環境 Cloud Run 固定為 false），不是公司屬性；
  // false 時設定頁把開關停用，不能開啟。
  rerank_available?: boolean;
  created_at: string;
  // 目前登入帳號在這家公司的身分；platform 帳號沒有這個概念，固定是 null。
  your_role?: ChatbotRole | null;
}
