import CopyOutlined from "@ant-design/icons/CopyOutlined";
import Button from "antd/es/button";
import Card from "antd/es/card";
import Form from "antd/es/form";
import Input from "antd/es/input";
import message from "antd/es/message";
import Popconfirm from "antd/es/popconfirm";
import Tooltip from "antd/es/tooltip";
import Typography from "antd/es/typography";
import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { createAccount, deleteAccount } from "../api/accounts";
import { getChatbotMcpToken } from "../api/chatbots";
import { useAuth } from "../auth/AuthContext";
import AccountManagementCard from "../components/AccountManagementCard";
import AdminPageLayout from "../components/AdminPageLayout";
import ChatbotSettingsTabs from "../components/ChatbotSettingsTabs";
import type { Account } from "../types/auth";
import { ui } from "../uiStyles";
import { queryClient } from "../queryClient";
import { queryKeys } from "../api/queryKeys";
import {
  useAccountsQuery,
  useDeleteChatbotMutation,
  useUpdateChatbotMutation,
} from "../hooks/useAdminQueries";
import { useSelectedChatbot } from "../hooks/useSelectedChatbot";

const { Text } = Typography;
const { TextArea } = Input;
const DEFAULT_MCP_TRIGGER_NAME = "MCP";
const DEFAULT_QUICK_REPLIES = ["無線滑鼠支援多少 DPI？", "退貨要幾天內申請？"];
const CHAT_WIDGET_PREVIEW_ORIGIN = (
  import.meta.env.VITE_CHAT_WIDGET_URL || "http://localhost:5175/chat-widget.js"
).replace(/\/chat-widget\.js$/, "");

interface ChatbotSettingsForm {
  name: string;
  mcp_url?: string;
  mcp_token?: string;
  mcp_trigger_name?: string;
  welcome_message?: string;
  quick_replies?: string;
}

export default function ChatbotSettingsPage() {
  const navigate = useNavigate();
  const {
    token,
    account: currentAccount,
    selectedChatbotId,
    selectChatbot,
  } = useAuth();
  const { chatbot } = useSelectedChatbot();
  const [messageApi, contextHolder] = message.useMessage();
  const [form] = Form.useForm<ChatbotSettingsForm>();
  const [accountForm] = Form.useForm<{ email: string }>();
  const [saving, setSaving] = useState(false);
  const [revealedMcpToken, setRevealedMcpToken] = useState<string | null>(null);
  const [revealingToken, setRevealingToken] = useState(false);
  const [clearingToken, setClearingToken] = useState(false);
  const accountsQuery = useAccountsQuery(token, selectedChatbotId ?? undefined);
  const accounts = accountsQuery.data ?? [];
  const updateMutation = useUpdateChatbotMutation(token ?? "");
  const deleteMutation = useDeleteChatbotMutation(token ?? "");
  const [addingAccount, setAddingAccount] = useState(false);
  const triggerNameInput = Form.useWatch("mcp_trigger_name", form);
  const triggerName =
    (triggerNameInput ?? "").trim().replace(/^[@＠]+/, "") ||
    DEFAULT_MCP_TRIGGER_NAME;
  useEffect(() => {
    setRevealedMcpToken(null);
  }, [selectedChatbotId]);

  useEffect(() => {
    if (!chatbot) return;
    form.setFieldsValue({
      name: chatbot.name,
      mcp_url: chatbot.mcp_url ?? "",
      mcp_trigger_name: chatbot.mcp_trigger_name ?? DEFAULT_MCP_TRIGGER_NAME,
      welcome_message: chatbot.welcome_message ?? "",
      quick_replies: (chatbot.quick_replies ?? DEFAULT_QUICK_REPLIES).join(
        "\n",
      ),
    });
  }, [chatbot, form]);

  if (!token) return <Navigate to="/login" replace />;
  if (!selectedChatbotId) {
    return <Navigate to="/chatbots" replace />;
  }

  async function handleSave(values: ChatbotSettingsForm) {
    if (!token) return;
    setSaving(true);
    try {
      const quickReplies = (values.quick_replies ?? "")
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);

      if (!selectedChatbotId) return;
      await updateMutation.mutateAsync({
        chatbotId: selectedChatbotId,
        params: {
          name: values.name.trim(),
          mcp_url: values.mcp_url ?? "",
          mcp_trigger_name: values.mcp_trigger_name ?? "",
          ...(values.mcp_token ? { mcp_token: values.mcp_token } : {}),
          welcome_message: values.welcome_message ?? "",
          quick_replies: quickReplies,
        },
      });
      form.setFieldValue("mcp_token", "");
      setRevealedMcpToken(null);
      messageApi.success("已儲存 ChatBot 設定");
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "儲存失敗");
    } finally {
      setSaving(false);
    }
  }

  async function handleRevealMcpToken() {
    if (!token || !selectedChatbotId) return;
    setRevealingToken(true);
    try {
      setRevealedMcpToken(
        (await getChatbotMcpToken(token, selectedChatbotId)) ?? "",
      );
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "查看金鑰失敗");
    } finally {
      setRevealingToken(false);
    }
  }

  async function handleClearMcpToken() {
    if (!token || !selectedChatbotId) return;
    setClearingToken(true);
    try {
      await updateMutation.mutateAsync({
        chatbotId: selectedChatbotId,
        params: { mcp_token: "" },
      });
      setRevealedMcpToken(null);
      messageApi.success("已清除 MCP 金鑰");
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "清除金鑰失敗");
    } finally {
      setClearingToken(false);
    }
  }

  async function handleAddAccount(values: { email: string }) {
    if (!token || !selectedChatbotId) return;
    setAddingAccount(true);
    try {
      await createAccount(token, {
        email: values.email,
        role: "tenant_secondary",
        chatbot_id: selectedChatbotId,
      });
      accountForm.resetFields();
      await queryClient.invalidateQueries({
        queryKey: queryKeys.accounts.byChatbot(selectedChatbotId),
      });
      messageApi.success("已新增管理帳號");
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "新增失敗");
    } finally {
      setAddingAccount(false);
    }
  }

  async function handleRemoveAccount(accountId: string) {
    if (!token || !selectedChatbotId) return;
    try {
      await deleteAccount(token, accountId, selectedChatbotId);
      await queryClient.invalidateQueries({
        queryKey: queryKeys.accounts.byChatbot(selectedChatbotId),
      });
      messageApi.success("已移除管理帳號");
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "移除失敗");
    }
  }

  async function handleDeleteChatbot() {
    if (!token || !selectedChatbotId) return;
    try {
      await deleteMutation.mutateAsync(selectedChatbotId);
      selectChatbot(null);
      messageApi.success("已刪除商家服務");
      navigate("/chatbots", { replace: true });
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "刪除失敗");
    }
  }

  async function copyValue(value: string, label: string) {
    try {
      await navigator.clipboard.writeText(value);
      messageApi.success(`已複製${label}`);
    } catch {
      messageApi.error("複製失敗，請手動複製內容");
    }
  }

  const isPlatformRole =
    currentAccount?.role === "platform_primary" ||
    currentAccount?.role === "platform_secondary";
  const canManageAccounts = isPlatformRole || chatbot?.your_role === "primary";

  const basicContent = (
    <div className={ui.settingsCardGrid}>
      <Card className={ui.settingsCard} title="基本資料">
        <Form.Item
          name="name"
          label="名稱"
          rules={[
            { required: true, message: "請輸入 ChatBot 名稱" },
            { max: 200, message: "名稱不可超過 200 個字元" },
          ]}
        >
          <Input placeholder="例如：客服 ChatBot" />
        </Form.Item>
        {chatbot ? (
          <Form.Item label="商家識別碼">
            <Input.Search
              aria-label="商家識別碼"
              readOnly
              value={chatbot.id}
              enterButton={
                <Button
                  aria-label="複製商家識別碼"
                  color="default"
                  icon={
                    <Tooltip title="複製商家識別碼">
                      <CopyOutlined />
                    </Tooltip>
                  }
                  variant="outlined"
                />
              }
              onSearch={() => void copyValue(chatbot.id, "商家識別碼")}
            />
          </Form.Item>
        ) : null}

        {chatbot ? (
          <>
            <Form.Item label="機器人網址">
              <Input.Search
                aria-label="機器人網址"
                readOnly
                value={`${CHAT_WIDGET_PREVIEW_ORIGIN}/?clientId=${chatbot.id}`}
                enterButton={
                  <Button
                    aria-label="複製機器人網址"
                    color="default"
                    icon={
                      <Tooltip title="複製機器人網址">
                        <CopyOutlined />
                      </Tooltip>
                    }
                    variant="outlined"
                  />
                }
                onSearch={() =>
                  void copyValue(
                    `${CHAT_WIDGET_PREVIEW_ORIGIN}/?clientId=${chatbot.id}`,
                    "機器人網址",
                  )
                }
              />
            </Form.Item>
          </>
        ) : null}
      </Card>

      <Card className={ui.settingsCard} title="對話內容">
        <Form.Item
          name="welcome_message"
          label="聊天機器人開頭語"
          extra="留空時使用系統預設的開頭語。"
        >
          <TextArea rows={3} />
        </Form.Item>
        <Form.Item
          name="quick_replies"
          label="開場快速提問"
          extra="一行一個，顯示在聊天視窗剛打開時的快速提問按鈕。"
        >
          <TextArea rows={3} />
        </Form.Item>
      </Card>

      <Card className={ui.settingsCard} title="MCP 連線">
        <Form.Item
          name="mcp_url"
          label="MCP URL"
          extra={`使用者訊息以 @${triggerName} 開頭時，聊天機器人會透過這個位址呼叫 MCP server。`}
        >
          <Input placeholder="例如 http://localhost:8001/mcp" />
        </Form.Item>
        <Form.Item
          name="mcp_trigger_name"
          label="MCP 機器人名稱"
          rules={[
            { max: 20, message: "名稱最多 20 個字" },
            { pattern: /^[^\s@＠]*$/, message: "名稱不能包含空白或 @" },
          ]}
        >
          <Input prefix="@" maxLength={20} />
        </Form.Item>
        <Form.Item
          name="mcp_token"
          label="MCP 金鑰"
          extra="留空表示不變更；已設定的金鑰可在下方查看。"
        >
          <Input.Password
            autoComplete="new-password"
            placeholder={
              chatbot?.has_mcp_token ? "已設定，留空表示不變更" : "尚未設定"
            }
          />
        </Form.Item>
        {chatbot?.has_mcp_token ? (
          <div className={ui.inlineActions}>
            {revealedMcpToken === null ? (
              <Button loading={revealingToken} onClick={handleRevealMcpToken}>
                查看金鑰
              </Button>
            ) : (
              <>
                <Form.Item label="MCP 金鑰">
                  <Input.Search
                    aria-label="MCP 金鑰"
                    readOnly
                    value={revealedMcpToken}
                    enterButton={
                      <Button
                        aria-label="複製 MCP 金鑰"
                        color="default"
                        icon={
                          <Tooltip title="複製 MCP 金鑰">
                            <CopyOutlined />
                          </Tooltip>
                        }
                        variant="outlined"
                      />
                    }
                    onSearch={() =>
                      void copyValue(revealedMcpToken, "MCP 金鑰")
                    }
                  />
                </Form.Item>
                <Button onClick={() => setRevealedMcpToken(null)}>隱藏</Button>
              </>
            )}
            <Popconfirm
              title="確定要清除這家商家的 MCP 金鑰嗎？"
              onConfirm={handleClearMcpToken}
              okButtonProps={{ danger: true }}
            >
              <Button danger loading={clearingToken}>
                清除金鑰
              </Button>
            </Popconfirm>
          </div>
        ) : null}
      </Card>

      <AccountManagementCard
        title="管理商家帳號"
        accounts={accounts}
        loading={accountsQuery.isLoading}
        loadingLabel="商家帳號讀取中"
        adding={addingAccount}
        canManage={canManageAccounts}
        currentAccountId={currentAccount?.id}
        emptyText="目前只有你自己在管理這家商家服務。"
        readonlyText="只有主帳號能新增或移除協作帳號。"
        inputPlaceholder="要新增的 gmail 地址"
        addButtonText="新增帳號"
        removeConfirmTitle="確定要移除這個帳號嗎？"
        form={accountForm}
        getRoleLabel={(account) =>
          account.chatbot_role === "primary" ? "主帳號" : "協作帳號"
        }
        getRoleTagColor={(account) =>
          account.chatbot_role === "primary" ? "primary" : "default"
        }
        onAdd={handleAddAccount}
        onRemove={handleRemoveAccount}
      />

      <div className={ui.settingsActions}>
        {/* <Popconfirm
          title="確定要刪除這家商家服務嗎？"
          description="會連同 RAG 知識庫文件與向量資料一起刪除，無法復原。"
          onConfirm={handleDeleteChatbot}
          okButtonProps={{ danger: true }}
        >
          <Button danger loading={deleteMutation.isPending}>
            刪除這家商家服務
          </Button>
        </Popconfirm> */}
        <Button type="primary" loading={saving} onClick={() => form.submit()}>
          儲存基本設定
        </Button>
      </div>
    </div>
  );

  return (
    <AdminPageLayout
      title="基本設定"
      description="管理目前選定 ChatBot 的基本資料、對話內容與 MCP 連線。"
      beforeHeader={contextHolder}
    >
      {chatbot ? (
        <>
          <ChatbotSettingsTabs />
          <Form
            component={false}
            form={form}
            layout="vertical"
            onFinish={handleSave}
          >
            {basicContent}
          </Form>
        </>
      ) : (
        <Card className={ui.settingsCard}>
          <Text type="secondary">查無這個 ChatBot 的資料。</Text>
        </Card>
      )}
    </AdminPageLayout>
  );
}
