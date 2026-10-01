import type {
  DocumentInfo,
  PrecheckRequestItem,
  PrecheckResponse,
} from "../types/documents";
import { requestAdminApi } from "./apiClient";

// path 可能含斜線（例如 "policy/faq/faq1.md"），需逐段 encode 再接回，
// 避免整段 encodeURIComponent 把斜線也編碼成 %2F 導致後端 :path 路由解析錯誤。
function encodePathForUrl(path: string): string {
  return path
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");
}

export async function sha256Hex(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export async function fetchDocuments(
  token: string,
  chatbotId: string,
): Promise<DocumentInfo[]> {
  const data = await requestAdminApi<{ documents: DocumentInfo[] }>(
    `/api/admin/documents?chatbot_id=${encodeURIComponent(chatbotId)}`,
    { token },
  );
  return data.documents;
}

export async function precheckDocuments(
  token: string,
  chatbotId: string,
  items: PrecheckRequestItem[],
  scopePrefix: string | null,
): Promise<PrecheckResponse> {
  return requestAdminApi<PrecheckResponse>(
    `/api/admin/documents/precheck?chatbot_id=${encodeURIComponent(chatbotId)}`,
    {
      method: "POST",
      token,
      json: { scope_prefix: scopePrefix, items },
    },
  );
}

interface UpsertDocumentParams {
  path: string;
  tags: string[];
  clientSha256: string;
  // 只有真的需要新內容（新增/內容變更）時才要帶；純改標籤或掛到既有內容不需要上傳檔案。
  file?: File;
}

// 新增/更新內容/改標籤/掛到既有內容統一走這支：doc_id 完全不需要呼叫端提供，
// 後端依路徑跟雜湊自己判斷要做什麼事（見 contracts.md）。
export async function upsertDocument(
  token: string,
  chatbotId: string,
  params: UpsertDocumentParams,
): Promise<DocumentInfo> {
  const formData = new FormData();
  params.tags.forEach((tag) => formData.append("tags", tag));
  formData.append("client_sha256", params.clientSha256);
  if (params.file) formData.append("file", params.file);
  return requestAdminApi<DocumentInfo>(
    `/api/admin/documents/${encodePathForUrl(params.path)}?chatbot_id=${encodeURIComponent(chatbotId)}`,
    {
      method: "PUT",
      token,
      body: formData,
    },
  );
}

export async function deleteDocument(
  token: string,
  chatbotId: string,
  path: string,
): Promise<void> {
  await requestAdminApi<void>(
    `/api/admin/documents/${encodePathForUrl(path)}?chatbot_id=${encodeURIComponent(chatbotId)}`,
    {
      method: "DELETE",
      token,
    },
  );
}
