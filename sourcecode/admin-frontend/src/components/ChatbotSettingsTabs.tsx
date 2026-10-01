import BookOutlined from "@ant-design/icons/BookOutlined";
import CodeOutlined from "@ant-design/icons/CodeOutlined";
import CustomerServiceOutlined from "@ant-design/icons/CustomerServiceOutlined";
import FacebookOutlined from "@ant-design/icons/FacebookOutlined";
import FileTextOutlined from "@ant-design/icons/FileTextOutlined";
import MessageOutlined from "@ant-design/icons/MessageOutlined";
import SettingOutlined from "@ant-design/icons/SettingOutlined";
import Tabs from "antd/es/tabs";
import { useLocation, useNavigate } from "react-router-dom";
import { ui } from "../uiStyles";

const items = [
  {
    key: "/chatbots/settings",
    label: (
      <span>
        <SettingOutlined />
        基本設定
      </span>
    ),
  },
  {
    key: "/chatbots/knowledge",
    label: (
      <span>
        <BookOutlined />
        知識管理
      </span>
    ),
  },
  {
    key: "/chatbots/linebot-settings",
    label: (
      <span>
        <MessageOutlined />
        LINE BOT 設定
      </span>
    ),
  },
  {
    key: "/chatbots/meta-settings",
    label: (
      <span>
        <FacebookOutlined />
        Facebook / Instagram 設定
      </span>
    ),
  },
  {
    key: "/chatbots/script-settings",
    label: (
      <span>
        <CodeOutlined />
        腳本設定
      </span>
    ),
  },
  {
    key: "/chatbots/summary",
    label: (
      <span>
        <CustomerServiceOutlined />
        客服摘要
      </span>
    ),
  },
  {
    key: "/chatbots/audit-log",
    label: (
      <span>
        <FileTextOutlined />
        稽核紀錄
      </span>
    ),
  },
];

export default function ChatbotSettingsTabs() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Tabs
      activeKey={location.pathname}
      className={ui.settingsTabs}
      items={items}
      onChange={navigate}
    />
  );
}
