import CopyOutlined from "@ant-design/icons/CopyOutlined";
import Button from "antd/es/button";
import Card from "antd/es/card";
import Form from "antd/es/form";
import Input from "antd/es/input";
import message from "antd/es/message";
import Tooltip from "antd/es/tooltip";
import Typography from "antd/es/typography";
import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { updateChatbot } from "../api/chatbots";
import { useAuth } from "../auth/AuthContext";
import AdminPageLayout from "../components/AdminPageLayout";
import ChatbotSettingsTabs from "../components/ChatbotSettingsTabs";
import { ui } from "../uiStyles";
import { useUpdateChatbotMutation } from "../hooks/useAdminQueries";
import { useSelectedChatbot } from "../hooks/useSelectedChatbot";

const { Text } = Typography;

const API_BASE_URL =
  import.meta.env.VITE_RAG_API_URL || "http://localhost:8000";

interface LineBotSettingsForm {
  line_channel_id?: string;
  line_channel_secret?: string;
  line_channel_access_token?: string;
}

export default function LineBotSettingsPage() {
  const { token } = useAuth();
  const { chatbot, selectedChatbotId } = useSelectedChatbot();
  const updateMutation = useUpdateChatbotMutation(token ?? "");

  const [messageApi, contextHolder] = message.useMessage();
  const [form] = Form.useForm<LineBotSettingsForm>();
  const [saving, setSaving] = useState(false);

  const webhookUrl = selectedChatbotId
    ? `${API_BASE_URL}/line/webhook/${encodeURIComponent(selectedChatbotId)}`
    : "";

  useEffect(() => {
    if (!chatbot) return;

    form.setFieldsValue({
      line_channel_id: chatbot.line_channel_id ?? "",
      line_channel_secret: "",
      line_channel_access_token: "",
    });
  }, [chatbot, form]);

  if (!token) return <Navigate to="/login" replace />;
  if (!selectedChatbotId) {
    return <Navigate to="/chatbots" replace />;
  }

  async function handleSave(values: LineBotSettingsForm) {
    if (!token || !selectedChatbotId) return;

    setSaving(true);

    try {
      await updateMutation.mutateAsync({
        chatbotId: selectedChatbotId,
        params: {
          line_channel_id: values.line_channel_id ?? "",

          ...(values.line_channel_secret
            ? { line_channel_secret: values.line_channel_secret }
            : {}),

          ...(values.line_channel_access_token
            ? { line_channel_access_token: values.line_channel_access_token }
            : {}),
        },
      });

      form.setFieldsValue({
        line_channel_secret: "",
        line_channel_access_token: "",
      });

      messageApi.success("已儲存 LINE BOT 設定");
    } catch (error) {
      messageApi.error(
        error instanceof Error ? error.message : "LINE BOT 設定儲存失敗",
      );
    } finally {
      setSaving(false);
    }
  }

  async function copyWebhookUrl() {
    try {
      await navigator.clipboard.writeText(webhookUrl);
      messageApi.success("已複製 Webhook URL");
    } catch {
      messageApi.error("複製失敗，請手動複製內容");
    }
  }

  return (
    <AdminPageLayout
      title="LINE BOT 設定"
      description="設定目前選定 ChatBot 與 LINE 官方帳號的連線資訊。"
      beforeHeader={contextHolder}
    >
      <ChatbotSettingsTabs />

      {chatbot ? (
        <Form
          className={ui.settingsCardGrid}
          form={form}
          layout="vertical"
          onFinish={handleSave}
        >
          <Card className={ui.settingsCard} title="LINE Messaging API">
            <Form.Item
              name="line_channel_id"
              label="Channel ID"
              extra="僅供 CRM 記錄，不參與 Webhook 驗證。"
            >
              <Input placeholder="請輸入 Channel ID" />
            </Form.Item>

            <Form.Item
              name="line_channel_secret"
              label="Channel Secret"
              extra="留空表示不變更目前設定。"
            >
              <Input.Password
                autoComplete="new-password"
                placeholder="請輸入 Channel Secret"
              />
            </Form.Item>

            <Form.Item
              name="line_channel_access_token"
              label="Channel Access Token"
              extra="留空表示不變更目前設定。"
            >
              <Input.Password
                autoComplete="new-password"
                placeholder="請輸入 Channel Access Token"
              />
            </Form.Item>

            <Form.Item
              label="Webhook URL"
              extra="將此網址複製到 LINE Developers 的 Webhook URL。"
            >
              <Input.Search
                aria-label="Webhook URL"
                readOnly
                value={webhookUrl}
                enterButton={
                  <Button
                    aria-label="複製 Webhook URL"
                    color="default"
                    icon={
                      <Tooltip title="複製 Webhook URL">
                        <CopyOutlined />
                      </Tooltip>
                    }
                    variant="outlined"
                  />
                }
                onSearch={() => void copyWebhookUrl()}
              />
            </Form.Item>
          </Card>

          <div className={ui.settingsActions}>
            <Button type="primary" htmlType="submit" loading={saving}>
              儲存 LINE BOT 設定
            </Button>
          </div>
        </Form>
      ) : (
        <Card className={ui.settingsCard}>
          <Text type="secondary">查無這個 ChatBot 的資料。</Text>
        </Card>
      )}
    </AdminPageLayout>
  );
}
