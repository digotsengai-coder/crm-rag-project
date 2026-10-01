import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// 本機商店與 Widget 預覽共用此公開 Client ID，避免兩個開發入口查詢不同資料。
// 正式環境仍由 Cloud Build 傳入的 VITE_CHAT_WIDGET_CLIENT_ID 覆寫；此值不是授權憑證。
const LOCAL_CHAT_WIDGET_CLIENT_ID = "fa0e0ad1-ae3b-4ade-bc09-ae1f552ef55e";

function widgetEmbedPlugin(widgetUrl: string, clientId: string): Plugin {
  return {
    name: "widget-embed",
    transformIndexHtml: {
      order: "pre",
      handler(html) {
        return html
          .replace("__CHAT_WIDGET_URL__", widgetUrl)
          .replace("__CHAT_WIDGET_CLIENT_ID__", clientId);
      },
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "VITE_");
  const widgetUrl = env.VITE_CHAT_WIDGET_URL || "/src/chat-widget.js";
  const clientId =
    mode === "development"
      ? LOCAL_CHAT_WIDGET_CLIENT_ID
      : env.VITE_CHAT_WIDGET_CLIENT_ID;

  return {
    plugins: [widgetEmbedPlugin(widgetUrl, clientId), tailwindcss(), react()],
    server: {
      port: 5173,
    },
  };
});
