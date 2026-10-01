import { requestAdminApi } from "./apiClient";

export interface AuditLogEntry {
  id: number;
  actor_email: string | null;
  action: string;
  target_type: string;
  target_id: string | null;
  detail: unknown;
  created_at: string | null;
}

export async function listAuditLog(
  token: string,
  chatbotId: string,
): Promise<AuditLogEntry[]> {
  const data = await requestAdminApi<{ entries: AuditLogEntry[] }>(
    `/api/admin/audit-log?chatbot_id=${encodeURIComponent(chatbotId)}`,
    { token },
  );
  return data.entries;
}
