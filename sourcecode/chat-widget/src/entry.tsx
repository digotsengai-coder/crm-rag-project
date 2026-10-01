import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import SmartCRMChatWidget from "./SmartCRMChatWidget";
import widgetStyles from "./widget.css?inline";

declare global {
  interface Window {
    __CRM_CHAT_WIDGET_MOUNTED__?: boolean;
  }
}

const scriptElement = document.currentScript as HTMLScriptElement | null;
const clientId = scriptElement?.dataset.clientId?.trim() ?? "";

function mountWidget() {
  if (window.__CRM_CHAT_WIDGET_MOUNTED__) return;
  if (!clientId || clientId.length > 128) {
    console.error(
      "[CRM Chat Widget] data-client-id 必填，且長度不得超過 128 個字元。",
    );
    return;
  }

  const host = document.createElement("div");
  host.dataset.crmChatWidgetHost = "";
  const shadowRoot = host.attachShadow({ mode: "open" });
  const styleElement = document.createElement("style");
  styleElement.textContent = widgetStyles;
  const mountElement = document.createElement("div");
  shadowRoot.append(styleElement, mountElement);
  document.body.append(host);

  window.__CRM_CHAT_WIDGET_MOUNTED__ = true;
  createRoot(mountElement).render(
    <StrictMode>
      <SmartCRMChatWidget clientId={clientId} />
    </StrictMode>,
  );
}

if (document.body) {
  mountWidget();
} else {
  window.addEventListener("DOMContentLoaded", mountWidget, { once: true });
}
