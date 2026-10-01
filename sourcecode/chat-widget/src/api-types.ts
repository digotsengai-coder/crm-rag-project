export type ProviderId = "local" | "anthropic" | "openai" | "google" | "xai";

export interface HistoryTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
  history: HistoryTurn[];
  provider: ProviderId;
}

export interface SourceRef {
  text: string;
  source: string;
  topic: string;
  distance: number;
}

interface ChatResponseFields {
  text: string | null;
  source: string | null;
  sources: SourceRef[] | null;
  code: string | null;
  status: number | null;
  eta: string | null;
  items: string | null;
}

export interface TextChatResponse extends ChatResponseFields {
  type: "text";
  text: string;
}

export interface ProductChatResponse extends ChatResponseFields {
  type: "product";
  text: string;
  source: string | null;
  sources: SourceRef[] | null;
}

export interface OrderChatResponse extends ChatResponseFields {
  type: "order";
  code: string;
  status: number;
  eta: string;
  items: string;
}

export type ChatResponse =
  TextChatResponse | ProductChatResponse | OrderChatResponse;

export interface ProviderInfo {
  id: ProviderId;
  label: string;
  configured: boolean;
}
