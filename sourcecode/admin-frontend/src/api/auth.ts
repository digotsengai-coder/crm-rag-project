import type { Account, ChatbotInfo } from "../types/auth";
import { requestAdminApi } from "./apiClient";

interface MeResponse {
  account: Account;
  chatbots: ChatbotInfo[];
}

interface LoginResponse {
  token: string;
  account: Account;
}

export async function loginWithGoogle(idToken: string): Promise<LoginResponse> {
  return requestAdminApi<LoginResponse>("/api/auth/google", {
    method: "POST",
    json: { id_token: idToken },
  });
}

/** 開發用一鍵登入（後端預設關閉，只有本機且明確開啟時才有作用，否則回 404）。 */
export async function loginWithDevAccount(): Promise<LoginResponse> {
  return requestAdminApi<LoginResponse>("/api/auth/dev-login", {
    method: "POST",
  });
}

export async function logout(token: string): Promise<void> {
  await requestAdminApi<void>("/api/auth/logout", {
    method: "POST",
    token,
  });
}

export async function getMe(token: string): Promise<MeResponse> {
  return requestAdminApi<MeResponse>("/api/auth/me", {
    token,
  });
}
