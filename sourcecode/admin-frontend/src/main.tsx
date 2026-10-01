import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import ConfigProvider from "antd/es/config-provider";
import zhTW from "antd/locale/zh_TW";
import App from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { adminTheme } from "./theme/adminTheme";
import { queryClient } from "./queryClient";
import "./styles.css";

const root = document.getElementById("root");
if (!root) throw new Error("找不到 React 掛載節點 #root");

createRoot(root).render(
  <StrictMode>
    <ConfigProvider locale={zhTW} theme={adminTheme}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </QueryClientProvider>
    </ConfigProvider>
  </StrictMode>,
);
