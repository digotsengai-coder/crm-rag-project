import type { ChatRequest, ChatResponse, ProviderInfo } from "../api-types";
import type { WidgetConfig } from "../config";
import {
  parseChatResponse,
  parseProviders,
  parseWidgetConfig,
} from "./validation";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

function clientHeaders(clientId: string): HeadersInit {
  return { "X-Client-ID": clientId };
}

export async function askBackend(
  request: ChatRequest,
  clientId: string,
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...clientHeaders(clientId) },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`後端回應狀態碼 ${response.status}: ${body}`);
  }
  const data: unknown = await response.json();
  return parseChatResponse(data);
}

export async function fetchProviders(
  clientId: string,
): Promise<ProviderInfo[]> {
  const response = await fetch(`${API_BASE_URL}/api/providers`, {
    headers: clientHeaders(clientId),
  });
  if (!response.ok) throw new Error(`後端回應錯誤：${response.status}`);
  const data: unknown = await response.json();
  return parseProviders(data);
}

export async function fetchWidgetConfig(
  clientId: string,
): Promise<WidgetConfig> {
  const response = await fetch(`${API_BASE_URL}/api/widget/config`, {
    headers: clientHeaders(clientId),
  });
  if (!response.ok) throw new Error(`Widget 設定載入失敗：${response.status}`);
  const data: unknown = await response.json();
  return parseWidgetConfig(data);
}
