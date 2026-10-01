const ADMIN_API_BASE_URL =
  import.meta.env.VITE_RAG_API_URL || "http://localhost:8000";

type UnauthorizedHandler = () => void;

let unauthorizedHandler: UnauthorizedHandler | null = null;
let unauthorizedHandled = false;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface AdminApiRequestOptions extends Omit<
  RequestInit,
  "body" | "headers"
> {
  token?: string;
  json?: unknown;
  body?: BodyInit;
  headers?: HeadersInit;
}

export function setUnauthorizedHandler(
  handler: UnauthorizedHandler,
): () => void {
  unauthorizedHandler = handler;
  unauthorizedHandled = false;

  return () => {
    if (unauthorizedHandler === handler) unauthorizedHandler = null;
  };
}

function notifyUnauthorized(): void {
  if (unauthorizedHandled) return;
  unauthorizedHandled = true;
  unauthorizedHandler?.();
}

function getFallbackErrorMessage(status: number): string {
  if (status === 400) return "請求內容有誤，請確認後再試。";
  if (status === 401) return "登入授權已失效，請重新登入。";
  if (status === 403) return "目前帳號沒有執行此操作的權限。";
  if (status === 404) return "找不到指定的資料。";
  if (status === 409) return "資料狀態衝突，請重新整理後再試。";
  if (status === 422) return "提交的資料格式不正確。";
  if (status === 429) return "請求過於頻繁，請稍後再試。";
  if (status >= 500) return "服務暫時無法使用，請稍後再試。";
  return `請求失敗（狀態碼 ${status}）。`;
}

async function getErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: unknown;
    } | null;
    if (typeof payload?.detail === "string" && payload.detail.trim()) {
      return payload.detail;
    }
  }

  return getFallbackErrorMessage(response.status);
}

export async function requestAdminApi<T>(
  path: string,
  options: AdminApiRequestOptions = {},
): Promise<T> {
  const { token, json, body, headers: customHeaders, ...requestInit } = options;
  const headers = new Headers(customHeaders);

  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (json !== undefined) headers.set("Content-Type", "application/json");

  let response: Response;
  try {
    response = await fetch(`${ADMIN_API_BASE_URL}${path}`, {
      ...requestInit,
      headers,
      body: json !== undefined ? JSON.stringify(json) : body,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw new ApiError("無法連線至服務，請檢查網路後再試。");
  }

  if (!response.ok) {
    const message = await getErrorMessage(response);
    if (token && response.status === 401) notifyUnauthorized();
    throw new ApiError(message, response.status);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) return undefined as T;

  const responseText = await response.text();
  if (!responseText.trim()) return undefined as T;

  try {
    return JSON.parse(responseText) as T;
  } catch {
    throw new ApiError("服務回應格式不正確，請稍後再試。", response.status);
  }
}
