import Space from "antd/es/space";
import type { ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { useSelectedChatbot } from "../hooks/useSelectedChatbot";
import { ui } from "../uiStyles";
import { tw } from "../utils/tw";

interface AdminPageLayoutProps {
  title: ReactNode;
  description: ReactNode;
  headerExtra?: ReactNode;
  headerLeading?: ReactNode;
  beforeHeader?: ReactNode;
  variant?: "default" | "detail";
  children: ReactNode;
}

export default function AdminPageLayout({
  title,
  description,
  headerExtra,
  headerLeading,
  beforeHeader,
  variant = "default",
  children,
}: AdminPageLayoutProps) {
  const location = useLocation();
  const { chatbot } = useSelectedChatbot();
  const selectedChatbotName = chatbot?.name;

  return (
    <main className={ui.pageContent}>
      {beforeHeader}
      <div className={ui.pageHeaderGroup}>
        <div
          className={tw(
            ui.pageHeading,
            variant === "detail" && ui.detailHeading,
          )}
        >
          <div>
            {headerLeading}
            <h1>{title}</h1>
            <p>{description}</p>
          </div>
          {headerExtra}
        </div>
        {location.pathname.startsWith("/chatbots/") && selectedChatbotName ? (
          <strong className={ui.currentChatbotName}>
            目前商家：{selectedChatbotName}
          </strong>
        ) : null}
      </div>

      <Space className={ui.fullWidth} direction="vertical" size={16}>
        {children}
      </Space>
    </main>
  );
}
