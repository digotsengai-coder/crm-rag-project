import CopyOutlined from "@ant-design/icons/CopyOutlined";
import Button from "antd/es/button";
import Card from "antd/es/card";
import Form from "antd/es/form";
import Input from "antd/es/input";
import message from "antd/es/message";
import Tooltip from "antd/es/tooltip";
import Typography from "antd/es/typography";
import { Navigate, useLocation } from "react-router-dom";
import { useSelectedChatbot } from "../hooks/useSelectedChatbot";
import ChatbotSettingsTabs from "../components/ChatbotSettingsTabs";
import AdminPageLayout from "../components/AdminPageLayout";
import { ui } from "../uiStyles";

const pageContent: Record<string, { title: string; description: string }> = {
  "/chatbots/linebot-settings": {
    title: "LineBot 設定",
    description: "設定 ChatBot 與 LINE 官方帳號的連線方式。",
  },
  "/chatbots/script-settings": {
    title: "腳本設定",
    description: "程式碼嵌入商家網站，讓網站載入目前商家的聊天機器人。",
  },
};

const { Paragraph, Text } = Typography;

export default function ChatbotPlaceholderPage() {
  const location = useLocation();
  const { selectedChatbotId, chatbot } = useSelectedChatbot();
  const [messageApi, contextHolder] = message.useMessage();
  const content = pageContent[location.pathname];

  if (!selectedChatbotId) return <Navigate to="/chatbots" replace />;
  if (!content) return <Navigate to="/chatbots" replace />;

  const adminFrontendUrl = (
    import.meta.env.VITE_ADMIN_FRONTEND_URL || "http://localhost:5174/"
  ).replace(/\/$/, "");
  const embedScript = chatbot
    ? `<script src="${adminFrontendUrl}/chat-widget.js" data-client-id="${chatbot.id}" defer></script>`
    : "";

  async function copyEmbedScript() {
    try {
      await navigator.clipboard.writeText(embedScript);
      messageApi.success("已複製嵌入程式碼");
    } catch {
      messageApi.error("複製失敗，請手動複製內容");
    }
  }

  return (
    <AdminPageLayout
      title={content.title}
      description={content.description}
      beforeHeader={contextHolder}
    >
      <ChatbotSettingsTabs />
      <Card className={ui.settingsCard} title="嵌入程式碼">
        {location.pathname === "/chatbots/script-settings" && chatbot ? (
          <>
            <Form component={false} layout="vertical">
              <Form.Item label="嵌入程式碼">
                <Input.Search
                  aria-label="嵌入程式碼"
                  className="font-mono"
                  readOnly
                  value={embedScript}
                  enterButton={
                    <Button
                      aria-label="複製嵌入程式碼"
                      color="default"
                      icon={
                        <Tooltip title="複製嵌入程式碼">
                          <CopyOutlined />
                        </Tooltip>
                      }
                      variant="outlined"
                    />
                  }
                  onSearch={() => void copyEmbedScript()}
                />
              </Form.Item>
            </Form>
            <Paragraph>
              請將上面程式碼貼到網站的 <Text code>&lt;html&gt;</Text> 標籤內。
            </Paragraph>
            <pre className="mb-4 overflow-x-auto rounded-lg bg-slate-950 p-4 text-sm text-slate-100">
              <code>{`<html>\n  ...\n  ${embedScript}\n</html>`}</code>
            </pre>
          </>
        ) : (
          <div className={ui.settingsPlaceholder}>
            此功能目前尚未支援，待 API 完成後開放。
          </div>
        )}
      </Card>
    </AdminPageLayout>
  );
}
