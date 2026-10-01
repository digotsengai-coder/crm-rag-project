import Tag from "antd/es/tag";
import type { ReactNode } from "react";
import type { AccountRoleTagColor } from "../config/accountRoles";
import { ui } from "../uiStyles";

const ACCOUNT_ROLE_TAG_CLASS_NAMES: Record<AccountRoleTagColor, string> = {
  primary: ui.accountRoleTagPrimary,
  default: ui.accountRoleTagDefault,
};

interface AccountRoleTagProps {
  color: AccountRoleTagColor;
  children: ReactNode;
}

export default function AccountRoleTag({
  color,
  children,
}: AccountRoleTagProps) {
  return (
    <Tag className={ACCOUNT_ROLE_TAG_CLASS_NAMES[color]} bordered={false}>
      {children}
    </Tag>
  );
}
