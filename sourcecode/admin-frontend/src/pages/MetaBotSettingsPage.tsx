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

interface MetaBotSettingsForm {
  facebook_app_secret?: string;
  facebook_verify_token?: string;
  facebook_page_id?: string;
  facebook_page_access_token?: string;
  instagram_business_id?: string;
  instagram_access_token?: string;
  instagram_app_secret?: string;
}

export default function MetaBotSettingsPage() {
  const { token } = useAuth();
  const { chatbot, selectedChatbotId } = useSelectedChatbot();
  const updateMutation = useUpdateChatbotMutation(token ?? "");

  const [messageApi, contextHolder] = message.useMessage();
  const [form] = Form.useForm<MetaBotSettingsForm>();
  const [saving, setSaving] = useState(false);

  const webhookUrl = selectedChatbotId
    ? `${API_BASE_URL}/meta/webhook/${encodeURIComponent(selectedChatbotId)}`
    : "";

  useEffect(() => {
    if (!chatbot) return;

    form.setFieldsValue({
      facebook_app_secret: "",
      facebook_verify_token: "",
      facebook_page_id: chatbot.facebook_page_id ?? "",
      facebook_page_access_token: "",
      instagram_business_id: chatbot.instagram_business_id ?? "",
      instagram_access_token: "",
      instagram_app_secret: "",
    });
  }, [chatbot, form]);

  if (!token) return <Navigate to="/login" replace />;
  if (!selectedChatbotId) {
    return <Navigate to="/chatbots" replace />;
  }

  async function handleSave(values: MetaBotSettingsForm) {
    if (!token || !selectedChatbotId) return;

    setSaving(true);

    try {
      await updateMutation.mutateAsync({
        chatbotId: selectedChatbotId,
        params: {
          facebook_page_id: values.facebook_page_id ?? "",
          instagram_business_id: values.instagram_business_id ?? "",

          ...(values.facebook_app_secret
            ? { facebook_app_secret: values.facebook_app_secret }
            : {}),

          ...(values.facebook_verify_token
            ? { facebook_verify_token: values.facebook_verify_token }
            : {}),

          ...(values.facebook_page_access_token
            ? { facebook_page_access_token: values.facebook_page_access_token }
            : {}),

          ...(values.instagram_access_token
            ? { instagram_access_token: values.instagram_access_token }
            : {}),

          ...(values.instagram_app_secret
            ? { instagram_app_secret: values.instagram_app_secret }
            : {}),
        },
      });

      form.setFieldsValue({
        facebook_app_secret: "",
        facebook_verify_token: "",
        facebook_page_access_token: "",
        instagram_access_token: "",
        instagram_app_secret: "",
      });

      messageApi.success("已儲存 Facebook / Instagram 設定");
    } catch (error) {
      messageApi.error(
        error instanceof Error
          ? error.message
          : "Facebook / Instagram 設定儲存失敗",
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
      title="Facebook / Instagram 設定"
      description="設定目前選定 ChatBot 與 Facebook 粉絲專頁、Instagram 私訊的連線資訊。"
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
          <Card className={ui.settingsCard} title="Meta App 設定">
            <Form.Item
              name="facebook_app_secret"
              label="App Secret"
              extra="Facebook 與 Instagram 共用同一個 Meta App，留空表示不變更目前設定。"
            >
              <Input.Password
                autoComplete="new-password"
                placeholder="請輸入 Meta App 的 App Secret"
              />
            </Form.Item>

            <Form.Item
              name="facebook_verify_token"
              label="Verify Token"
              extra="請自訂一組字串，稍後設定 Meta Webhook 時要填回同一組值；留空表示不變更目前設定。"
            >
              <Input.Password
                autoComplete="new-password"
                placeholder="請自訂 Verify Token"
              />
            </Form.Item>

            <Form.Item
              label="Webhook URL"
              extra="將此網址複製到 Meta for Developers 的 Webhook 設定；此網址同時用於 Facebook 粉專與 Instagram 私訊。"
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

          <Card className={ui.settingsCard} title="Facebook Messenger">
            <Form.Item
              name="facebook_page_id"
              label="Page ID"
              extra="僅供 CRM 記錄，不參與 Webhook 驗證。"
            >
              <Input placeholder="請輸入粉絲專頁 Page ID" />
            </Form.Item>

            <Form.Item
              name="facebook_page_access_token"
              label="Page Access Token"
              extra="留空表示不變更目前設定。"
            >
              <Input.Password
                autoComplete="new-password"
                placeholder="請輸入粉絲專頁的 Page Access Token"
              />
            </Form.Item>
          </Card>

          <Card className={ui.settingsCard} title="Instagram">
            <Form.Item
              name="instagram_business_id"
              label="Instagram Business ID"
              extra="僅供 CRM 記錄，不參與 Webhook 驗證。"
            >
              <Input placeholder="請輸入 Instagram Business Account ID" />
            </Form.Item>

            <Form.Item
              name="instagram_app_secret"
              label="Instagram App Secret"
              extra="Meta 後台「Instagram API」子產品自己的 App Secret，跟上面 Meta App 設定的 App Secret 不同，用於驗證 Instagram 訊息的 Webhook 簽章；留空表示不變更目前設定。"
            >
              <Input.Password
                autoComplete="new-password"
                placeholder="請輸入 Instagram App Secret"
              />
            </Form.Item>

            <Form.Item
              name="instagram_access_token"
              label="Instagram Access Token"
              extra="留空表示不變更目前設定。"
            >
              <Input.Password
                autoComplete="new-password"
                placeholder="請輸入 Instagram Access Token"
              />
            </Form.Item>
          </Card>

          <div className={ui.settingsActions}>
            <Button type="primary" htmlType="submit" loading={saving}>
              儲存 Facebook / Instagram 設定
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
