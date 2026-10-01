import { useEffect, useState } from "react";
import { MessageCircle } from "lucide-react";
import ChatHeader from "./components/ChatHeader";
import ProviderSelect from "./components/ProviderSelect";
import MessageList from "./components/MessageList";
import ChatComposer from "./components/ChatComposer";
import { useChat } from "./hooks/useChat";
import { useProviders } from "./hooks/useProviders";
import { fetchWidgetConfig } from "./api/chat";
import {
  DEFAULT_WIDGET_CONFIG,
  toThemeStyle,
  type WidgetConfig,
} from "./config";
import { widgetUi } from "./widgetStyles";

export default function SmartCRMChatWidget({ clientId }: { clientId: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [config, setConfig] = useState<WidgetConfig>(DEFAULT_WIDGET_CONFIG);
  const { messages, isSending, sendMessage } = useChat(
    clientId,
    config.welcomeMessage,
  );
  const { providers, provider, setProvider } = useProviders(clientId);

  useEffect(() => {
    let active = true;
    void fetchWidgetConfig(clientId)
      .then((nextConfig) => {
        if (active) setConfig(nextConfig);
      })
      .catch(() => {
        // 客戶設定無法載入時保留內建樣式，避免聊天功能被非必要設定阻擋。
      });
    return () => {
      active = false;
    };
  }, [clientId]);

  function handleSend(text: string) {
    if (sendMessage(text, provider)) setInput("");
  }
  return (
    <div className={widgetUi.root} style={toThemeStyle(config.theme)}>
      {isOpen ? (
        <div className={widgetUi.panel}>
          <ChatHeader
            brandName={config.brandName}
            logoUrl={config.logoUrl}
            onClose={() => setIsOpen(false)}
          />
          {providers.length > 0 && (
            <ProviderSelect
              providers={providers}
              value={provider}
              onChange={setProvider}
            />
          )}
          <MessageList
            messages={messages}
            isSending={isSending}
            header={
              <div className={widgetUi.quickReplies}>
                {config.quickReplies.map((question) => (
                  <button
                    key={question}
                    className={widgetUi.chip}
                    onClick={() => handleSend(question)}
                  >
                    {question}
                  </button>
                ))}
              </div>
            }
          />
          <ChatComposer
            value={input}
            onChange={setInput}
            onSend={() => handleSend(input)}
            isSending={isSending}
          />
        </div>
      ) : (
        <button
          className={widgetUi.launcher}
          aria-label="開啟客服聊天視窗"
          onClick={() => setIsOpen(true)}
        >
          <MessageCircle size={24} />
        </button>
      )}
    </div>
  );
}
