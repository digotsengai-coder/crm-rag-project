import type {
  ChatResponse,
  ProviderId,
  ProviderInfo,
  SourceRef,
} from "../api-types";
import { DEFAULT_WIDGET_CONFIG, type WidgetConfig } from "../config";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isSource(value: unknown): value is SourceRef {
  return (
    isRecord(value) &&
    typeof value.text === "string" &&
    typeof value.source === "string" &&
    typeof value.topic === "string" &&
    typeof value.distance === "number" &&
    Number.isFinite(value.distance)
  );
}

export function isProviderId(value: unknown): value is ProviderId {
  return (
    value === "local" ||
    value === "anthropic" ||
    value === "openai" ||
    value === "google" ||
    value === "xai"
  );
}

export function parseChatResponse(value: unknown): ChatResponse {
  if (!isRecord(value)) throw new Error("聊天回應格式錯誤");
  const { type, text, source, sources, code, status, eta, items } = value;
  const strings = [text, source, code, eta, items];
  if (
    strings.some((field) => field != null && typeof field !== "string") ||
    (status != null &&
      (typeof status !== "number" || !Number.isInteger(status))) ||
    (sources != null && (!Array.isArray(sources) || !sources.every(isSource)))
  ) {
    throw new Error("聊天回應欄位格式錯誤");
  }
  // 未使用欄位可以省略；統一為 null，讓 API 型別與後端序列化格式一致。
  const fields = {
    text: typeof text === "string" ? text : null,
    source: typeof source === "string" ? source : null,
    sources: Array.isArray(sources) && sources.every(isSource) ? sources : null,
    code: typeof code === "string" ? code : null,
    status: typeof status === "number" ? status : null,
    eta: typeof eta === "string" ? eta : null,
    items: typeof items === "string" ? items : null,
  };
  if (type === "text" && typeof text === "string")
    return { ...fields, type, text };
  if (
    type === "product" &&
    typeof text === "string" &&
    (source === null || typeof source === "string") &&
    (sources === null || (Array.isArray(sources) && sources.every(isSource)))
  ) {
    return { ...fields, type, text };
  }
  if (
    type === "order" &&
    typeof code === "string" &&
    typeof eta === "string" &&
    typeof items === "string" &&
    typeof status === "number" &&
    Number.isInteger(status)
  ) {
    return { ...fields, type, code, eta, items, status };
  }
  throw new Error("聊天回應類型或必要欄位錯誤");
}

export function parseProviders(value: unknown): ProviderInfo[] {
  if (!Array.isArray(value)) throw new Error("模型清單格式錯誤");
  return value.map((entry: unknown) => {
    if (
      !isRecord(entry) ||
      !isProviderId(entry.id) ||
      typeof entry.label !== "string" ||
      typeof entry.configured !== "boolean"
    ) {
      throw new Error("模型清單項目格式錯誤");
    }
    return { id: entry.id, label: entry.label, configured: entry.configured };
  });
}

function validColor(value: unknown, fallback: string): string {
  return typeof value === "string" && /^#[0-9a-fA-F]{6}$/.test(value)
    ? value
    : fallback;
}

export function parseWidgetConfig(value: unknown): WidgetConfig {
  if (!isRecord(value)) throw new Error("Widget 設定格式錯誤");
  const theme = isRecord(value.theme) ? value.theme : {};
  const radius = theme.borderRadius;
  return {
    brandName:
      typeof value.brandName === "string" && value.brandName.trim()
        ? value.brandName.trim()
        : DEFAULT_WIDGET_CONFIG.brandName,
    welcomeMessage:
      typeof value.welcomeMessage === "string" && value.welcomeMessage.trim()
        ? value.welcomeMessage.trim()
        : DEFAULT_WIDGET_CONFIG.welcomeMessage,
    logoUrl:
      typeof value.logoUrl === "string" && value.logoUrl.trim()
        ? value.logoUrl.trim()
        : null,
    theme: {
      primaryColor: validColor(
        theme.primaryColor,
        DEFAULT_WIDGET_CONFIG.theme.primaryColor,
      ),
      surfaceColor: validColor(
        theme.surfaceColor,
        DEFAULT_WIDGET_CONFIG.theme.surfaceColor,
      ),
      textColor: validColor(
        theme.textColor,
        DEFAULT_WIDGET_CONFIG.theme.textColor,
      ),
      borderRadius:
        typeof radius === "number" &&
        Number.isFinite(radius) &&
        radius >= 0 &&
        radius <= 32
          ? radius
          : DEFAULT_WIDGET_CONFIG.theme.borderRadius,
    },
    quickReplies:
      Array.isArray(value.quickReplies) &&
      value.quickReplies.every((q) => typeof q === "string") &&
      value.quickReplies.length > 0
        ? (value.quickReplies as string[])
        : DEFAULT_WIDGET_CONFIG.quickReplies,
  };
}
