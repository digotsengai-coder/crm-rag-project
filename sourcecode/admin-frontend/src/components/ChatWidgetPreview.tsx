import { useEffect } from "react";

const WIDGET_SRC =
  import.meta.env.VITE_CHAT_WIDGET_URL ||
  "http://localhost:5175/chat-widget.js";

declare global {
  interface Window {
    __CRM_CHAT_WIDGET_MOUNTED__?: boolean;
  }
}

/**
 * chat-widget.js 設計成「整個頁面生命週期只掛載一次」（見 chat-widget/src/entry.tsx 的
 * window.__CRM_CHAT_WIDGET_MOUNTED__ guard），本來是給客戶網站單一公司使用的固定嵌入方式。
 * 這裡在管理後台的 RAG 頁面重新利用同一支 script，讓管理者可以直接測試「目前選定公司」
 * 的聊天/RAG 回答；因為 SPA 換公司不會整頁重新整理，所以換公司時要手動清掉舊的 widget
 * DOM 節點跟 script 標籤、重置掛載旗標，才能重新掛載成新公司的 client id。
 */
export default function ChatWidgetPreview({
  chatbotId,
}: {
  chatbotId: string | null;
}) {
  useEffect(() => {
    if (!chatbotId) return;

    function cleanup() {
      document
        .querySelectorAll("[data-crm-chat-widget-host]")
        .forEach((el) => el.remove());
      document
        .querySelectorAll("script[data-crm-chat-widget-loader]")
        .forEach((el) => el.remove());
      window.__CRM_CHAT_WIDGET_MOUNTED__ = false;
    }

    cleanup();
    const script = document.createElement("script");
    script.src = WIDGET_SRC;
    script.dataset.clientId = chatbotId;
    script.dataset.crmChatWidgetLoader = "";
    script.defer = true;
    document.body.appendChild(script);

    return cleanup;
  }, [chatbotId]);

  return null;
}
