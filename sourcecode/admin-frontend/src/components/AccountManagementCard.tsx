import { DeleteOutlined } from "@ant-design/icons";
import Button from "antd/es/button";
import Card from "antd/es/card";
import Form, { type FormInstance } from "antd/es/form";
import Input from "antd/es/input";
import Popconfirm from "antd/es/popconfirm";
import Table from "antd/es/table";
import Typography from "antd/es/typography";
import type { ReactNode } from "react";
import type { AccountRoleTagColor } from "../config/accountRoles";
import type { Account } from "../types/auth";
import { ui } from "../uiStyles";
import AccountRoleTag from "./AccountRoleTag";
import CardLoading from "./CardLoading";

const { Paragraph } = Typography;

interface AccountFormValues {
  email: string;
}

interface AccountManagementCardProps {
  title?: ReactNode;
  accounts: Account[];
  loading: boolean;
  loadingLabel: string;
  adding: boolean;
  canManage: boolean;
  currentAccountId?: string;
  emptyText: string;
  readonlyText: string;
  inputPlaceholder: string;
  addButtonText: string;
  removeConfirmTitle: string;
  removeConfirmDescription?: string;
  form: FormInstance<AccountFormValues>;
  getRoleLabel: (account: Account) => ReactNode;
  getRoleTagColor: (account: Account) => AccountRoleTagColor;
  onAdd: (values: AccountFormValues) => void | Promise<void>;
  onRemove: (accountId: string) => void | Promise<void>;
}

export default function AccountManagementCard({
  title,
  accounts,
  loading,
  loadingLabel,
  adding,
  canManage,
  currentAccountId,
  emptyText,
  readonlyText,
  inputPlaceholder,
  addButtonText,
  removeConfirmTitle,
  removeConfirmDescription,
  form,
  getRoleLabel,
  getRoleTagColor,
  onAdd,
  onRemove,
}: AccountManagementCardProps) {
  return (
    <Card className={ui.settingsCard} title={title}>
      {loading ? (
        <CardLoading label={loadingLabel} />
      ) : (
        <>
          {canManage ? (
            <Form
              className={ui.settingsAccountForm}
              form={form}
              layout="inline"
              onFinish={onAdd}
            >
              <Form.Item
                name="email"
                rules={[
                  {
                    required: true,
                    type: "email",
                    message: "請輸入有效的 gmail 地址",
                  },
                ]}
              >
                <Input placeholder={inputPlaceholder} />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={adding}>
                  {addButtonText}
                </Button>
              </Form.Item>
            </Form>
          ) : (
            <Paragraph className={ui.marginTop4} type="secondary">
              {readonlyText}
            </Paragraph>
          )}
          <Table<Account>
            rowKey="id"
            dataSource={accounts}
            pagination={false}
            locale={{ emptyText }}
            scroll={{ x: 560 }}
            columns={[
              {
                title: "角色",
                key: "role",
                width: 160,
                render: (_, account) => (
                  <AccountRoleTag color={getRoleTagColor(account)}>
                    {getRoleLabel(account)}
                  </AccountRoleTag>
                ),
              },
              {
                title: "信箱",
                dataIndex: "email",
                key: "email",
              },
              {
                title: "操作",
                key: "action",
                width: 120,
                align: "right",
                render: (_, account) =>
                  canManage && account.id !== currentAccountId ? (
                    <Popconfirm
                      title={removeConfirmTitle}
                      description={removeConfirmDescription}
                      onConfirm={() => onRemove(account.id)}
                    >
                      <Button danger type="text" icon={<DeleteOutlined />}>
                        移除
                      </Button>
                    </Popconfirm>
                  ) : null,
              },
            ]}
          />
        </>
      )}
    </Card>
  );
}
