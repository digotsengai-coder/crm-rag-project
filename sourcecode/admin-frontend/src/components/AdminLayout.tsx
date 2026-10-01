import HomeOutlined from "@ant-design/icons/HomeOutlined";
import LogoutOutlined from "@ant-design/icons/LogoutOutlined";
import MenuOutlined from "@ant-design/icons/MenuOutlined";
import RobotOutlined from "@ant-design/icons/RobotOutlined";
import ShoppingOutlined from "@ant-design/icons/ShoppingOutlined";
import TeamOutlined from "@ant-design/icons/TeamOutlined";
import UserOutlined from "@ant-design/icons/UserOutlined";
import Avatar from "antd/es/avatar";
import Button from "antd/es/button";
import Drawer from "antd/es/drawer";
import Dropdown from "antd/es/dropdown";
import Layout from "antd/es/layout";
import Menu from "antd/es/menu";
import Tooltip from "antd/es/tooltip";
import { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ACCOUNT_ROLE_DISPLAY } from "../config/accountRoles";
import { ui } from "../uiStyles";
import BrandMark from "./BrandMark";

const { Header, Sider, Content } = Layout;

const navigationItems = [
  { key: "/chatbots", icon: <RobotOutlined />, label: "ChatBot" },
  // { key: "/dashboard", icon: <HomeOutlined />, label: "儀表板" },
  // { key: "/orders", icon: <ShoppingOutlined />, label: "訂單管理" },
];

// 「管理者帳號」頁籤只給 platform_primary／platform_secondary 看，商家帳號完全看不到這個入口。
const ADMIN_ACCOUNTS_ITEM = {
  key: "/admin-accounts",
  icon: <TeamOutlined />,
  label: "管理者帳號",
};

function resolveSelectedKey(pathname: string) {
  if (pathname.startsWith("/orders")) return "/orders";
  if (pathname.startsWith("/chatbots")) return "/chatbots";
  if (pathname.startsWith("/dashboard")) return "/dashboard";
  if (pathname.startsWith("/admin-accounts")) return "/admin-accounts";
  return "/chatbots";
}

function getAccountName(email?: string) {
  if (!email) return "-";
  const atIndex = email.indexOf("@");
  return atIndex > 0 ? email.slice(0, atIndex) : email;
}

export default function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { account, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 900);
  const selectedKey = resolveSelectedKey(location.pathname);
  const isPlatformRole =
    account?.role === "platform_primary" ||
    account?.role === "platform_secondary";
  const menuItems = isPlatformRole
    ? [...navigationItems, ADMIN_ACCOUNTS_ITEM]
    : navigationItems;
  const accountRoleDisplay = account
    ? ACCOUNT_ROLE_DISPLAY[account.role]
    : null;
  const accountName = getAccountName(account?.email);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  useEffect(() => {
    const media = window.matchMedia("(max-width: 899px)");
    const handleChange = () => setIsMobile(media.matches);
    handleChange();
    media.addEventListener("change", handleChange);
    return () => media.removeEventListener("change", handleChange);
  }, []);

  const navigation = (
    <>
      <div className={ui.siderBrand}>
        <BrandMark compact={collapsed && !isMobile} />
      </div>
      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        items={menuItems}
        inlineCollapsed={collapsed && !isMobile}
        onClick={({ key }) => {
          navigate(key);
          setMobileOpen(false);
        }}
      />
      {(!collapsed || isMobile) && (
        <div className={ui.siderCaption}>
          CRM Console
          <br />
          v0.1.0
        </div>
      )}
    </>
  );

  return (
    <Layout className={ui.adminShell}>
      {!isMobile && (
        <Sider
          width={224}
          collapsedWidth={76}
          collapsed={collapsed}
          theme="light"
          className={ui.desktopSider}
        >
          {navigation}
        </Sider>
      )}
      <Drawer
        placement="left"
        width={260}
        open={isMobile && mobileOpen}
        onClose={() => setMobileOpen(false)}
        closable={false}
        classNames={{ body: "p-0!" }}
      >
        <div className={ui.mobileNavigation}>{navigation}</div>
      </Drawer>
      <Layout>
        <Header className={ui.adminHeader}>
          <Tooltip
            title={isMobile ? "開啟選單" : collapsed ? "展開選單" : "收合選單"}
          >
            <Button
              className={ui.menuToggle}
              type="text"
              icon={<MenuOutlined />}
              aria-label={
                isMobile ? "開啟選單" : collapsed ? "展開選單" : "收合選單"
              }
              onClick={() =>
                isMobile ? setMobileOpen(true) : setCollapsed((value) => !value)
              }
            />
          </Tooltip>
          <Dropdown
            rootClassName={ui.accountDropdown}
            menu={{
              items: [
                {
                  key: "account-email",
                  className: ui.accountDropdownEmail,
                  disabled: true,
                  label: account?.email ?? "-",
                },
                { type: "divider" },
                { key: "logout", icon: <LogoutOutlined />, label: "登出" },
              ],
              onClick: ({ key }) => {
                if (key === "logout") handleLogout();
              },
            }}
          >
            <Button
              aria-haspopup="menu"
              aria-label="帳號選單"
              className={ui.account}
              type="text"
            >
              <Avatar icon={<UserOutlined />} />
              <span>
                <strong>{accountName}</strong>
                <small className="text-admin-text-secondary">
                  {accountRoleDisplay?.label ?? ""}
                </small>
              </span>
            </Button>
          </Dropdown>
        </Header>
        <Content className={ui.adminContent}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
