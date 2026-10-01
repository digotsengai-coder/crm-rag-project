import type { ChatbotInfo } from "../types/auth";
import { requestAdminApi } from "./apiClient";

export async function listChatbots(token: string): Promise<ChatbotInfo[]> {
  const data = await requestAdminApi<{ chatbots: ChatbotInfo[] }>(
    "/api/admin/chatbots",
    { token },
  );
  return data.chatbots;
}

export async function createChatbot(
  token: string,
  params: {
    name: string;
    mcp_url?: string;
    mcp_token?: string;
    mcp_trigger_name?: string;
    welcome_message?: string;
    quick_replies?: string[];
  },
): Promise<ChatbotInfo> {
  return requestAdminApi<ChatbotInfo>("/api/admin/chatbots", {
    method: "POST",
    token,
    json: params,
  });
}

export async function deleteChatbot(
  token: string,
  chatbotId: string,
): Promise<void> {
  await requestAdminApi<void>(
    `/api/admin/chatbots/${encodeURIComponent(chatbotId)}`,
    { method: "DELETE", token },
  );
}

export async function updateChatbot(
  token: string,
  chatbotId: string,
  params: {
    name?: string;
    mcp_url?: string;
    // 不帶＝不變更；空字串＝清除金鑰
    mcp_token?: string;
    // 不帶＝不變更；空字串＝回到預設的 MCP
    mcp_trigger_name?: string;
    welcome_message?: string;
    quick_replies?: string[];
    // 送給 LLM 的片段數（1～10）；不帶＝不變更
    rag_top_k?: number;
    // true 只在伺服器支援時才能設（否則後端回 400）；不帶＝不變更
    rerank_enabled?: boolean;
    // LINE Messaging API 設定；Channel ID 僅供記錄。
    line_channel_id?: string;
    line_channel_secret?: string;
    line_channel_access_token?: string;
    // Meta 平台（Facebook 粉專 + Instagram 私訊）設定；app_secret / verify_token 是 Meta App
    // 層級的憑證，兩個管道共用。Page ID / Instagram Business ID 僅供記錄。
    facebook_page_id?: string;
    facebook_app_secret?: string;
    facebook_page_access_token?: string;
    facebook_verify_token?: string;
    instagram_business_id?: string;
    instagram_access_token?: string;
    instagram_app_secret?: string;
  },
): Promise<ChatbotInfo> {
  return requestAdminApi<ChatbotInfo>(
    `/api/admin/chatbots/${encodeURIComponent(chatbotId)}`,
    {
      method: "PUT",
      token,
      json: params,
    },
  );
}

/** 查看這家公司的 MCP 金鑰明文；每次查看後端都會寫入稽核紀錄。 */
export async function getChatbotMcpToken(
  token: string,
  chatbotId: string,
): Promise<string | null> {
  const data = await requestAdminApi<{ mcp_token: string | null }>(
    `/api/admin/chatbots/${encodeURIComponent(chatbotId)}/mcp-token`,
    { token },
  );
  return data.mcp_token;
}
