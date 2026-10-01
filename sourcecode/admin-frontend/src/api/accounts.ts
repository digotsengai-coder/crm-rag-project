import type { Account, AccountRole } from "../types/auth";
import { requestAdminApi } from "./apiClient";

// 帶 chatbotId：查這家公司綁定的商家帳號（公司設定頁「管理帳號」用，不含管理者帳號）。
// 不帶：查全部管理者帳號（「管理者帳號」頁籤用，僅限 platform 角色）。
export async function listAccounts(
  token: string,
  chatbotId?: string,
): Promise<Account[]> {
  const path = chatbotId
    ? `/api/admin/accounts?chatbot_id=${encodeURIComponent(chatbotId)}`
    : "/api/admin/accounts";
  const data = await requestAdminApi<{ accounts: Account[] }>(path, {
    token,
  });
  return data.accounts;
}

export async function createAccount(
  token: string,
  params: { email: string; role: AccountRole; chatbot_id?: string },
): Promise<Account> {
  return requestAdminApi<Account>("/api/admin/accounts", {
    method: "POST",
    token,
    json: params,
  });
}

// 帶 chatbotId：只把這個帳號從這家公司移除協作關係，不刪除帳號本身（他可能還在管別家公司）。
// 不帶：刪除整個帳號（「管理者帳號」頁籤用）。
export async function deleteAccount(
  token: string,
  accountId: string,
  chatbotId?: string,
): Promise<void> {
  const path = chatbotId
    ? `/api/admin/accounts/${encodeURIComponent(accountId)}?chatbot_id=${encodeURIComponent(chatbotId)}`
    : `/api/admin/accounts/${encodeURIComponent(accountId)}`;
  await requestAdminApi<void>(path, {
    method: "DELETE",
    token,
  });
}
