import Form from "antd/es/form";
import message from "antd/es/message";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { createAccount, deleteAccount } from "../api/accounts";
import AccountManagementCard from "../components/AccountManagementCard";
import AdminPageLayout from "../components/AdminPageLayout";
import { ACCOUNT_ROLE_DISPLAY } from "../config/accountRoles";
import type { Account } from "../types/auth";
import { queryClient } from "../queryClient";
import { queryKeys } from "../api/queryKeys";
import { useAccountsQuery } from "../hooks/useAdminQueries";

/**
 * 管理者帳號頁籤：只有 platform_primary／platform_secondary 看得到，跟商家帳號完全分開
 * （不會出現在公司設定頁的「管理帳號」清單，也看不到這個頁籤）。新增/移除副管理者僅限
 * platform_primary（比照 ChatbotSettingsPage 商家主帳號能管理次帳號的權限模型）。
 */
export default function AdminAccountsPage() {
  const { token, account: currentAccount } = useAuth();
  const [messageApi, contextHolder] = message.useMessage();
  const accountsQuery = useAccountsQuery(token);
  const accounts = accountsQuery.data ?? [];
  const [form] = Form.useForm<{ email: string }>();
  const [adding, setAdding] = useState(false);

  const isPrimary = currentAccount?.role === "platform_primary";

  if (!token) return <Navigate to="/login" replace />;
  if (
    currentAccount &&
    currentAccount.role !== "platform_primary" &&
    currentAccount.role !== "platform_secondary"
  ) {
    return <Navigate to="/" replace />;
  }

  async function handleAdd(values: { email: string }) {
    if (!token) return;
    setAdding(true);
    try {
      await createAccount(token, {
        email: values.email,
        role: "platform_secondary",
      });
      form.resetFields();
      await queryClient.invalidateQueries({
        queryKey: queryKeys.accounts.platform,
      });
      messageApi.success("已新增副管理者帳號");
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "新增失敗");
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(accountId: string) {
    if (!token) return;
    try {
      await deleteAccount(token, accountId);
      await queryClient.invalidateQueries({
        queryKey: queryKeys.accounts.platform,
      });
      messageApi.success("已移除帳號");
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "移除失敗");
    }
  }

  return (
    <AdminPageLayout
      title="管理者帳號"
      description="平台維運帳號，預設對所有商家服務都有存取權限，不受單一 Chatbot 綁定限制。"
      beforeHeader={contextHolder}
    >
      <AccountManagementCard
        accounts={accounts}
        loading={accountsQuery.isLoading}
        loadingLabel="管理者帳號讀取中"
        adding={adding}
        canManage={isPrimary}
        currentAccountId={currentAccount?.id}
        emptyText="目前沒有管理者帳號。"
        readonlyText="只有主管理者帳號能新增/移除副管理者。"
        inputPlaceholder="要新增的副管理者 gmail 地址"
        addButtonText="新增副管理者"
        removeConfirmTitle="確定要移除這個管理者帳號嗎？"
        removeConfirmDescription="移除後該帳號會立刻無法登入。"
        form={form}
        getRoleLabel={(account) => ACCOUNT_ROLE_DISPLAY[account.role].label}
        getRoleTagColor={(account) =>
          ACCOUNT_ROLE_DISPLAY[account.role].tagColor
        }
        onAdd={handleAdd}
        onRemove={handleRemove}
      />
    </AdminPageLayout>
  );
}
