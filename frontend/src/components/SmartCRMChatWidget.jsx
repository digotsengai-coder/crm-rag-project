import { useState, useRef, useEffect } from "react";
import { MessageCircle, X, Send, Sparkles, Package, Truck, CheckCircle2, Clock } from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const ORDER_STAGES = [
  { key: "placed", label: "已下單", icon: Clock },
  { key: "shipped", label: "備貨出貨", icon: Package },
  { key: "delivering", label: "配送中", icon: Truck },
  { key: "done", label: "已送達", icon: CheckCircle2 },
];

const QUICK_REPLIES = ["無線滑鼠支援多少 DPI？", "查詢訂單 A12345", "退貨要幾天內申請？"];

async function askBackend(message, history, provider) {
  const res = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, provider }),
  });
  if (!res.ok) {
    throw new Error(`後端回應錯誤：${res.status}`);
  }
  return res.json();
}

async function fetchProviders() {
  const res = await fetch(`${API_BASE_URL}/api/providers`);
  if (!res.ok) throw new Error(`後端回應錯誤：${res.status}`);
  return res.json();
}

// 訂單卡片沒有單一文字內容（type == "order"），不適合塞進對話歷史給 LLM，直接略過；
// 只有文字類回覆（type == "text" | "product"）才會被記進歷史，讓機器人記得上下文。
function buildHistory(messages) {
  return messages
    .filter((m) => typeof m.text === "string" && m.text.length > 0)
    .map((m) => ({ role: m.role === "user" ? "user" : "assistant", content: m.text }));
}

function TypingIndicator() {
  return (
    <div className="ccw-row ccw-row-bot">
      <div className="ccw-bubble ccw-bubble-bot ccw-typing">
        <span className="ccw-dot" />
        <span className="ccw-dot" />
        <span className="ccw-dot" />
      </div>
    </div>
  );
}

function ProductAnswer({ text, source }) {
  return (
    <div className="ccw-row ccw-row-bot">
      <div className="ccw-bubble ccw-bubble-bot">
        <p className="ccw-bubble-text">{text}</p>
        {source && <span className="ccw-source-tag">相關主題：{source}</span>}
      </div>
    </div>
  );
}

function OrderCard({ code, status, eta, items }) {
  return (
    <div className="ccw-row ccw-row-bot">
      <div className="ccw-order-card">
        <div className="ccw-order-head">
          <span className="ccw-order-code">訂單 #{code}</span>
          <span className="ccw-order-eta">預計 {eta} 送達</span>
        </div>
        <p className="ccw-order-items">{items}</p>
        <div className="ccw-timeline">
          {ORDER_STAGES.map((stage, i) => {
            const Icon = stage.icon;
            const state = i < status ? "done" : i === status ? "active" : "pending";
            return (
              <div className="ccw-timeline-step" key={stage.key}>
                <div className={`ccw-timeline-node ccw-node-${state}`}>
                  <Icon size={14} strokeWidth={2.4} />
                </div>
                <span className={`ccw-timeline-label ccw-label-${state}`}>{stage.label}</span>
                {i < ORDER_STAGES.length - 1 && (
                  <div className={`ccw-timeline-bar ${i < status ? "ccw-bar-done" : ""}`} />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default function SmartCRMChatWidget() {
  const [isOpen, setIsOpen] = useState(true);
  const [messages, setMessages] = useState([
    {
      role: "bot",
      type: "text",
      text: "您好，我是線上客服，可以問我任何產品的規格、特色，或是輸入訂單編號查詢配送狀態喔。",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [providers, setProviders] = useState([{ id: "local", label: "本地 1.5B/7B（免費，速度較慢）", configured: true }]);
  const [provider, setProvider] = useState("local");
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  useEffect(() => {
    fetchProviders()
      .then(setProviders)
      .catch(() => {
        // 拿不到 provider 清單就維持預設只有本地模型，不影響聊天功能
      });
  }, []);

  async function sendMessage(text) {
    const trimmed = text.trim();
    if (!trimmed || isTyping) return;
    const history = buildHistory(messages);
    setMessages((prev) => [...prev, { role: "user", type: "text", text: trimmed }]);
    setInput("");
    setIsTyping(true);
    try {
      const reply = await askBackend(trimmed, history, provider);
      setMessages((prev) => [...prev, { role: "bot", ...reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          type: "text",
          text: "客服暫時無法連線，請確認後端服務是否已啟動，或稍後再試一次。",
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  return (
    <div className="ccw-root">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700&display=swap');

        .ccw-root {
          --navy: #1E3A5F;
          --navy-dark: #16293F;
          --amber: #E8963C;
          --amber-dark: #C97A2B;
          --bg: #EEF1F4;
          --surface: #FFFFFF;
          --text: #1B1F24;
          --text-muted: #6B7280;
          --success: #2F855A;
          --border: #E1E5EA;
          font-family: system-ui, -apple-system, "PingFang TC", "Noto Sans TC", "Microsoft JhengHei", sans-serif;
          position: relative;
          width: 100%;
          min-height: 620px;
          display: flex;
          align-items: flex-end;
          justify-content: flex-end;
          padding: 24px;
          box-sizing: border-box;
          background: radial-gradient(circle at 20% 20%, #F5F7F9 0%, var(--bg) 60%);
        }

        .ccw-launcher {
          width: 56px;
          height: 56px;
          border-radius: 50%;
          background: var(--navy);
          color: #fff;
          border: none;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          box-shadow: 0 8px 20px rgba(30, 58, 95, 0.35);
          transition: transform 0.15s ease;
        }
        .ccw-launcher:hover { transform: translateY(-2px); }
        .ccw-launcher:focus-visible { outline: 2px solid var(--amber); outline-offset: 3px; }

        .ccw-panel {
          width: 380px;
          max-width: 100%;
          height: 580px;
          background: var(--surface);
          border-radius: 20px;
          box-shadow: 0 20px 50px rgba(20, 30, 45, 0.18);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          animation: ccw-pop 0.22s ease;
        }
        @keyframes ccw-pop {
          from { opacity: 0; transform: translateY(12px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @media (prefers-reduced-motion: reduce) {
          .ccw-panel { animation: none; }
        }

        .ccw-header {
          background: var(--navy);
          color: #fff;
          padding: 16px 18px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .ccw-header-brand { display: flex; align-items: center; gap: 10px; }
        .ccw-header-icon {
          width: 34px; height: 34px; border-radius: 10px;
          background: rgba(255,255,255,0.12);
          display: flex; align-items: center; justify-content: center;
        }
        .ccw-header-title {
          font-family: 'Sora', system-ui, sans-serif;
          font-weight: 600;
          font-size: 15px;
          line-height: 1.2;
        }
        .ccw-header-status {
          font-size: 12px;
          color: #B9C7D6;
          display: flex;
          align-items: center;
          gap: 5px;
          margin-top: 2px;
        }
        .ccw-status-dot {
          width: 6px; height: 6px; border-radius: 50%;
          background: #6FCF97;
          display: inline-block;
        }
        .ccw-close-btn {
          background: none; border: none; color: #DCE4EC; cursor: pointer;
          width: 30px; height: 30px; border-radius: 8px;
          display: flex; align-items: center; justify-content: center;
        }
        .ccw-close-btn:hover { background: rgba(255,255,255,0.1); }
        .ccw-close-btn:focus-visible { outline: 2px solid var(--amber); outline-offset: 2px; }

        .ccw-model-bar {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 14px;
          background: var(--surface);
          border-bottom: 1px solid var(--border);
          font-size: 12px;
        }
        .ccw-model-bar label { color: var(--text-muted); flex-shrink: 0; }
        .ccw-model-select {
          flex: 1;
          border: 1px solid var(--border);
          border-radius: 8px;
          padding: 4px 8px;
          font-size: 12px;
          font-family: inherit;
          color: var(--text);
          background: var(--surface);
        }
        .ccw-model-select:focus-visible { outline: 2px solid var(--amber); outline-offset: 1px; }

        .ccw-messages {
          flex: 1;
          overflow-y: auto;
          padding: 18px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          background: var(--bg);
        }

        .ccw-row { display: flex; }
        .ccw-row-user { justify-content: flex-end; }
        .ccw-row-bot { justify-content: flex-start; }

        .ccw-bubble {
          max-width: 80%;
          padding: 10px 13px;
          border-radius: 14px;
          font-size: 14px;
          line-height: 1.55;
        }
        .ccw-bubble-user {
          background: var(--navy);
          color: #fff;
          border-bottom-right-radius: 4px;
        }
        .ccw-bubble-bot {
          background: var(--surface);
          color: var(--text);
          border: 1px solid var(--border);
          border-bottom-left-radius: 4px;
        }
        .ccw-bubble-text { margin: 0; white-space: pre-wrap; }
        .ccw-source-tag {
          display: inline-block;
          margin-top: 8px;
          font-size: 11px;
          color: var(--text-muted);
          background: #F1F3F6;
          border-radius: 999px;
          padding: 2px 9px;
        }

        .ccw-typing { display: flex; gap: 4px; align-items: center; padding: 13px; }
        .ccw-dot {
          width: 6px; height: 6px; border-radius: 50%;
          background: #A7B1BC;
          animation: ccw-bounce 1.1s infinite ease-in-out;
        }
        .ccw-dot:nth-child(2) { animation-delay: 0.15s; }
        .ccw-dot:nth-child(3) { animation-delay: 0.3s; }
        @keyframes ccw-bounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
          30% { transform: translateY(-4px); opacity: 1; }
        }

        .ccw-order-card {
          max-width: 88%;
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: 14px;
          padding: 14px 16px 16px;
        }
        .ccw-order-head {
          display: flex; justify-content: space-between; align-items: baseline;
          margin-bottom: 4px;
        }
        .ccw-order-code {
          font-family: 'Sora', system-ui, sans-serif;
          font-weight: 600;
          font-size: 13px;
          color: var(--navy);
        }
        .ccw-order-eta { font-size: 12px; color: var(--amber-dark); font-weight: 600; }
        .ccw-order-items { margin: 0 0 14px; font-size: 13px; color: var(--text-muted); }

        .ccw-timeline { display: flex; align-items: flex-start; }
        .ccw-timeline-step {
          position: relative;
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
        }
        .ccw-timeline-node {
          width: 26px; height: 26px; border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          z-index: 1;
        }
        .ccw-node-done { background: var(--success); color: #fff; }
        .ccw-node-active { background: var(--amber); color: #fff; }
        .ccw-node-pending { background: #E7EAEE; color: #9AA4AF; }
        .ccw-timeline-label {
          font-size: 10.5px;
          margin-top: 6px;
          color: var(--text-muted);
          white-space: nowrap;
        }
        .ccw-label-active { color: var(--amber-dark); font-weight: 600; }
        .ccw-label-done { color: var(--success); font-weight: 600; }
        .ccw-timeline-bar {
          position: absolute;
          top: 13px;
          left: 50%;
          width: 100%;
          height: 2px;
          background: #E7EAEE;
        }
        .ccw-bar-done { background: var(--success); }

        .ccw-quick-replies {
          display: flex;
          gap: 8px;
          padding: 10px 14px 0;
          flex-wrap: wrap;
        }
        .ccw-chip {
          border: 1px solid var(--border);
          background: var(--surface);
          color: var(--navy);
          font-size: 12.5px;
          padding: 6px 12px;
          border-radius: 999px;
          cursor: pointer;
        }
        .ccw-chip:hover { border-color: var(--amber); }
        .ccw-chip:focus-visible { outline: 2px solid var(--amber); outline-offset: 2px; }

        .ccw-input-bar {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 14px;
          border-top: 1px solid var(--border);
          background: var(--surface);
        }
        .ccw-input {
          flex: 1;
          border: 1px solid var(--border);
          border-radius: 12px;
          padding: 10px 13px;
          font-size: 14px;
          font-family: inherit;
          color: var(--text);
          outline: none;
        }
        .ccw-input:focus-visible { border-color: var(--amber); }
        .ccw-send-btn {
          width: 38px; height: 38px;
          border-radius: 10px;
          background: var(--amber);
          border: none;
          color: #fff;
          display: flex; align-items: center; justify-content: center;
          cursor: pointer;
          flex-shrink: 0;
        }
        .ccw-send-btn:hover { background: var(--amber-dark); }
        .ccw-send-btn:focus-visible { outline: 2px solid var(--navy); outline-offset: 2px; }
        .ccw-send-btn:disabled { background: #D8DEE4; cursor: not-allowed; }

        @media (max-width: 480px) {
          .ccw-root { padding: 0; align-items: stretch; justify-content: stretch; min-height: 100vh; }
          .ccw-panel { width: 100%; height: 100vh; border-radius: 0; }
        }
      `}</style>

      {isOpen ? (
        <div className="ccw-panel">
          <div className="ccw-header">
            <div className="ccw-header-brand">
              <div className="ccw-header-icon">
                <Sparkles size={17} />
              </div>
              <div>
                <div className="ccw-header-title">智慧家電客服</div>
                <div className="ccw-header-status">
                  <span className="ccw-status-dot" />
                  線上服務中
                </div>
              </div>
            </div>
            <button className="ccw-close-btn" aria-label="收合聊天視窗" onClick={() => setIsOpen(false)}>
              <X size={18} />
            </button>
          </div>

          <div className="ccw-model-bar">
            <label htmlFor="ccw-model-select">回答模型</label>
            <select
              id="ccw-model-select"
              className="ccw-model-select"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              {providers.map((p) => (
                <option key={p.id} value={p.id} disabled={!p.configured}>
                  {p.label}
                  {!p.configured ? "（尚未設定 API key）" : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="ccw-messages" ref={listRef}>
            {messages.map((m, i) => {
              if (m.role === "user") {
                return (
                  <div className="ccw-row ccw-row-user" key={i}>
                    <div className="ccw-bubble ccw-bubble-user">
                      <p className="ccw-bubble-text">{m.text}</p>
                    </div>
                  </div>
                );
              }
              if (m.type === "product") {
                return <ProductAnswer key={i} text={m.text} source={m.source} />;
              }
              if (m.type === "order") {
                return <OrderCard key={i} code={m.code} status={m.status} eta={m.eta} items={m.items} />;
              }
              return (
                <div className="ccw-row ccw-row-bot" key={i}>
                  <div className="ccw-bubble ccw-bubble-bot">
                    <p className="ccw-bubble-text">{m.text}</p>
                  </div>
                </div>
              );
            })}
            {isTyping && <TypingIndicator />}
          </div>

          {messages.length < 2 && (
            <div className="ccw-quick-replies">
              {QUICK_REPLIES.map((q) => (
                <button key={q} className="ccw-chip" onClick={() => sendMessage(q)}>
                  {q}
                </button>
              ))}
            </div>
          )}

          <div className="ccw-input-bar">
            <input
              className="ccw-input"
              value={input}
              placeholder="輸入您的問題或訂單編號…"
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              aria-label="輸入訊息"
            />
            <button
              className="ccw-send-btn"
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isTyping}
              aria-label="送出訊息"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      ) : (
        <button className="ccw-launcher" aria-label="開啟客服聊天視窗" onClick={() => setIsOpen(true)}>
          <MessageCircle size={24} />
        </button>
      )}
    </div>
  );
}
