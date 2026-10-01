import type { AccountRole } from "../types/auth";

export type AccountRoleTagColor = "primary" | "default";

interface AccountRoleDisplay {
  label: string;
  tagColor: AccountRoleTagColor;
}

export const ACCOUNT_ROLE_DISPLAY: Record<AccountRole, AccountRoleDisplay> = {
  platform_primary: { label: "主管理者", tagColor: "primary" },
  platform_secondary: { label: "副管理者", tagColor: "default" },
  tenant_primary: { label: "主帳號", tagColor: "primary" },
  tenant_secondary: { label: "協作帳號", tagColor: "default" },
};
