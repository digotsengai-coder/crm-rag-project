import DeleteOutlined from "@ant-design/icons/DeleteOutlined";
import MoreOutlined from "@ant-design/icons/MoreOutlined";
import PlusOutlined from "@ant-design/icons/PlusOutlined";
import SettingOutlined from "@ant-design/icons/SettingOutlined";
import Button from "antd/es/button";
import Card from "antd/es/card";
import Dropdown from "antd/es/dropdown";
import Empty from "antd/es/empty";
import Form from "antd/es/form";
import Input from "antd/es/input";
import message from "antd/es/message";
import Modal from "antd/es/modal";
import Spin from "antd/es/spin";
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { standardSpinProps } from "../config/spin";
import AdminPageLayout from "../components/AdminPageLayout";
import CopyableIdentifier from "../components/CopyableIdentifier";
import {
  useChatbotsQuery,
  useCreateChatbotMutation,
  useDeleteChatbotMutation,
} from "../hooks/useAdminQueries";
import { ui } from "../uiStyles";

function formatLastEditedAt(value: string | null): string {
  // API 尚未提供 updated_at，先以 created_at 作為設計稿欄位的示意資料。
  if (!value) return "--";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("zh-TW", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function getInitial(name: string): string {
  return name.trim().slice(0, 1).toUpperCase() || "C";
}

export default function ChatbotsPage() {
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();
  const { token, selectedChatbotId, selectChatbot } = useAuth();
  const chatbotsQuery = useChatbotsQuery(token);
  const [form] = Form.useForm<{ name: string }>();
  const [createOpen, setCreateOpen] = useState(false);
  const createMutation = useCreateChatbotMutation(token ?? "");
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const deleteMutation = useDeleteChatbotMutation(token ?? "");
  const chatbots = chatbotsQuery.data ?? [];

  if (!token) return <Navigate to="/login" replace />;
  const authToken = token;

  function goToSettings(chatbotId: string) {
    selectChatbot(chatbotId);
    navigate("/chatbots/settings");
  }

  function openCreateModal() {
    form.resetFields();
    setCreateOpen(true);
  }

  async function handleCreate() {
    let values: { name: string };
    try {
      values = await form.validateFields();
    } catch {
      return;
    }

    try {
      const created = await createMutation.mutateAsync({
        name: values.name.trim(),
      });
      selectChatbot(created.id);
      setCreateOpen(false);
      messageApi.success("已新增 ChatBot");
      navigate("/chatbots/settings");
    } catch (error) {
      messageApi.error(
        error instanceof Error ? error.message : "新增 ChatBot 失敗",
      );
    }
  }

  async function handleDelete() {
    if (!pendingDeleteId) return;

    try {
      await deleteMutation.mutateAsync(pendingDeleteId);
      if (selectedChatbotId === pendingDeleteId) selectChatbot(null);
      setPendingDeleteId(null);
      messageApi.success("已刪除 ChatBot");
    } catch (err) {
      messageApi.error(
        err instanceof Error ? err.message : "刪除 ChatBot 失敗",
      );
    }
  }

  return (
    <AdminPageLayout
      title="ChatBot"
      description="建立並設定商家的 AI Agent，管理角色、模型、知識庫與自動化工具。"
      beforeHeader={contextHolder}
    >
      <div className={ui.chatbotsCardHeader}>
        <h2>ChatBot 列表</h2>
        <Button
          icon={<PlusOutlined />}
          type="primary"
          onClick={openCreateModal}
        >
          新增 ChatBot
        </Button>
      </div>

      {chatbotsQuery.isLoading ? (
        <div className={ui.routeLoading} role="status">
          <Spin {...standardSpinProps} />
          <span>載入 ChatBot 列表…</span>
        </div>
      ) : chatbots.length === 0 ? (
        <Empty className="my-10" description="目前沒有可管理的 ChatBot">
          {/* <Button
            icon={<PlusOutlined />}
            type="primary"
            onClick={openCreateModal}
          >
            新增第一個 ChatBot
          </Button> */}
        </Empty>
      ) : (
        <section aria-labelledby="published-chatbots-heading">
          <div className={ui.chatbotsGrid}>
            {chatbots.map((chatbot) => (
              <article className={ui.chatbotCard} key={chatbot.id}>
                <div className={ui.chatbotCardTitle}>
                  <div aria-hidden="true" className={ui.chatbotAvatar}>
                    {getInitial(chatbot.name)}
                  </div>
                  <h3>
                    <Button
                      aria-label={`設定 ${chatbot.name}`}
                      className={ui.chatbotTitleButton}
                      title={chatbot.name}
                      type="link"
                      onClick={() => goToSettings(chatbot.id)}
                    >
                      {chatbot.name}
                    </Button>
                  </h3>
                  <Dropdown
                    rootClassName={ui.chatbotDropdown}
                    menu={{
                      items: [
                        {
                          key: "settings",
                          icon: <SettingOutlined />,
                          label: "前往設定",
                        },
                        {
                          danger: true,
                          key: "delete",
                          icon: <DeleteOutlined />,
                          label: "刪除 ChatBot",
                        },
                      ],
                      onClick: ({ key }) => {
                        if (key === "settings") goToSettings(chatbot.id);
                        if (key === "delete") setPendingDeleteId(chatbot.id);
                      },
                    }}
                    trigger={["click"]}
                  >
                    <Button
                      aria-label={`操作 ${chatbot.name}`}
                      aria-haspopup="menu"
                      className={ui.chatbotMenu}
                      icon={<MoreOutlined />}
                      type="text"
                    />
                  </Dropdown>
                </div>
                <div className={ui.chatbotMetadata}>
                  <CopyableIdentifier label="ID" value={chatbot.id} />
                  <span>
                    最後編輯：{formatLastEditedAt(chatbot.created_at)}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
      <Modal
        cancelText="取消"
        confirmLoading={createMutation.isPending}
        okText="新增"
        onCancel={() => setCreateOpen(false)}
        onOk={handleCreate}
        open={createOpen}
        title="新增 ChatBot"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="ChatBot 名稱"
            name="name"
            rules={[
              { required: true, message: "請輸入 ChatBot 名稱" },
              { max: 200, message: "名稱不可超過 200 個字元" },
            ]}
          >
            <Input autoFocus placeholder="例如：客服 ChatBot" />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        cancelText="取消"
        confirmLoading={deleteMutation.isPending}
        okButtonProps={{ danger: true }}
        okText="刪除"
        onCancel={() => setPendingDeleteId(null)}
        onOk={handleDelete}
        open={pendingDeleteId !== null}
        title="確定要刪除這個 ChatBot 嗎？"
      >
        <p>刪除後會連同該 ChatBot 的知識庫與相關資料一起移除，且無法復原。</p>
      </Modal>
    </AdminPageLayout>
  );
}
