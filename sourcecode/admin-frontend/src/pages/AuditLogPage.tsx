import Card from "antd/es/card";
import message from "antd/es/message";
import Select from "antd/es/select";
import Table from "antd/es/table";
import Tag from "antd/es/tag";
import Typography from "antd/es/typography";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import type { AuditLogEntry } from "../api/auditLog";
import { useAuth } from "../auth/AuthContext";
import AdminPageLayout from "../components/AdminPageLayout";
import ChatbotSettingsTabs from "../components/ChatbotSettingsTabs";
import { ui } from "../uiStyles";
import { useAuditLogQuery } from "../hooks/useAdminQueries";

const { Paragraph, Text } = Typography;

const ACTION_LABELS: Record<string, string> = {
  create_chatbot: "建立商家服務",
  update_chatbot: "更新商家設定",
  reveal_mcp_token: "查看 MCP 金鑰",
  delete_chatbot: "刪除商家服務",
  create_account: "新增帳號",
  delete_account: "移除帳號",
  self_register: "帳號自助註冊",
  upsert_document: "上傳/更新知識庫文件",
  delete_document: "刪除知識庫文件",
  bind_existing_account: "加入既有帳號",
  unbind_account_from_chatbot: "移除協作帳號",
  dev_login: "開發登入",
};

const ACTION_TAG_COLORS: Record<string, string> = {
  create_chatbot: "green",
  create_account: "cyan",
  self_register: "purple",
  bind_existing_account: "lime",
  update_chatbot: "blue",
  upsert_document: "geekblue",
  reveal_mcp_token: "gold",
  delete_chatbot: "red",
  delete_account: "volcano",
  delete_document: "magenta",
  unbind_account_from_chatbot: "orange",
  dev_login: "purple",
};

const TARGET_TYPE_LABELS: Record<string, string> = {
  account: "帳號",
  chatbot: "商家服務",
  kb_document: "知識庫文件",
};

function formatCreatedAt(value: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

export default function AuditLogPage() {
  const { token, selectedChatbotId } = useAuth();
  const [, contextHolder] = message.useMessage();
  const auditLogQuery = useAuditLogQuery(token, selectedChatbotId);
  const entries = auditLogQuery.data ?? [];
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  if (!token) return <Navigate to="/login" replace />;
  if (!selectedChatbotId) return <Navigate to="/chatbots" replace />;

  return (
    <AdminPageLayout
      title="稽核紀錄"
      description="查看目前 ChatBot 設定與資源的異動紀錄。"
      beforeHeader={contextHolder}
    >
      <ChatbotSettingsTabs />
      <Card className={ui.settingsCard}>
        <Paragraph type="secondary">
          商家服務最近的異動紀錄：建立或刪除、設定變更、知識庫文件及協作帳號異動。
        </Paragraph>
        <div className={ui.auditLogTableToolbar}>
          <Text type="secondary">每頁顯示</Text>
          <Select
            value={pageSize}
            onChange={(value) => {
              setCurrentPage(1);
              setPageSize(value);
            }}
            options={[10, 20, 50, 100].map((value) => ({
              label: `${value} 筆`,
              value,
            }))}
          />
        </div>
        <Table<AuditLogEntry>
          rowKey="id"
          dataSource={entries}
          loading={auditLogQuery.isLoading}
          pagination={{
            current: currentPage,
            pageSize,
            showSizeChanger: false,
            onChange: (page) => setCurrentPage(page),
            showTotal: (total) => `共 ${total} 筆紀錄`,
          }}
          locale={{ emptyText: "目前沒有紀錄。" }}
          scroll={{ x: 720 }}
          columns={[
            {
              title: "操作者",
              dataIndex: "actor_email",
              key: "actor_email",
              width: 220,
              render: (email: string | null) => email ?? "未知帳號",
            },
            {
              title: "動作",
              dataIndex: "action",
              key: "action",
              width: 180,
              render: (action: string) => (
                <Tag color={ACTION_TAG_COLORS[action]}>
                  {ACTION_LABELS[action] ?? action}
                </Tag>
              ),
            },
            {
              title: "目標",
              dataIndex: "target_type",
              key: "target_type",
              width: 220,
              render: (targetType: string, entry) => (
                <div>
                  <div>{TARGET_TYPE_LABELS[targetType] ?? targetType}</div>
                  <Text type="secondary">{entry.target_id ?? "-"}</Text>
                </div>
              ),
            },
            {
              title: "時間",
              dataIndex: "created_at",
              key: "created_at",
              width: 190,
              render: formatCreatedAt,
            },
          ]}
        />
      </Card>
    </AdminPageLayout>
  );
}
