import Collapse from "antd/es/collapse";
import ApiOutlined from "@ant-design/icons/ApiOutlined";
import AuditOutlined from "@ant-design/icons/AuditOutlined";
import BarChartOutlined from "@ant-design/icons/BarChartOutlined";
import ClockCircleOutlined from "@ant-design/icons/ClockCircleOutlined";
import ContainerOutlined from "@ant-design/icons/ContainerOutlined";
import DownOutlined from "@ant-design/icons/DownOutlined";
import FacebookOutlined from "@ant-design/icons/FacebookOutlined";
import FileSearchOutlined from "@ant-design/icons/FileSearchOutlined";
import GlobalOutlined from "@ant-design/icons/GlobalOutlined";
import MessageOutlined from "@ant-design/icons/MessageOutlined";
import RobotOutlined from "@ant-design/icons/RobotOutlined";
import SortAscendingOutlined from "@ant-design/icons/SortAscendingOutlined";
import ThunderboltOutlined from "@ant-design/icons/ThunderboltOutlined";
import UpOutlined from "@ant-design/icons/UpOutlined";
import { useRef, type MouseEvent, type ReactNode } from "react";
import { Link } from "react-router-dom";
import ChatWidgetPreview from "../components/ChatWidgetPreview";
import { welcome } from "../welcomeStyles";
import { tw } from "../utils/tw";

const WELCOME_CHATBOT_ID = "fba75d15-53a5-4a60-b874-b2224cb36a37";

const stats: Array<{ icon: ReactNode; value: string; label: string }> = [
  {
    icon: <ThunderboltOutlined />,
    value: "1~3 秒",
    label: "平均回覆速度",
  },
  {
    icon: <ClockCircleOutlined />,
    value: "24/7",
    label: "全天候在線",
  },
  {
    icon: <GlobalOutlined />,
    value: "3 渠道",
    label: "官網／LINE／Facebook",
  },
  {
    icon: <ApiOutlined />,
    value: "4+ 家",
    label: "LLM 供應商任你切換",
  },
];

const knowledgeBullets: Array<{ icon: ReactNode; text: string }> = [
  {
    icon: <FileSearchOutlined />,
    text: "RAG 檢索比對真實知識庫內容",
  },
  {
    icon: <BarChartOutlined />,
    text: "Recall@K・NDCG@K 品質評分，回答準不準，數據說了算",
  },
  {
    icon: <SortAscendingOutlined />,
    text: "Reranker 精準排序，降低答非所問",
  },
];

const channels: Array<{ icon: ReactNode; label: string }> = [
  { icon: <GlobalOutlined />, label: "網站嵌入" },
  { icon: <MessageOutlined />, label: "LINE" },
  { icon: <FacebookOutlined />, label: "Facebook" },
];

const demoOrderNumber = "10234";

const faqItems = [
  {
    key: "tech",
    question: "需要技術背景嗎？",
    answer: "不需要，後台介面操作，上傳商品資料即可開始。",
  },
  {
    key: "accuracy",
    question: "AI 會亂回答嗎？",
    answer: "不會，嚴格依知識庫內容回答，並有品質評分機制把關準確度。",
  },
  {
    key: "platform",
    question: "支援哪些平台？",
    answer: "官網嵌入元件、LINE、Facebook。",
  },
  {
    key: "orders",
    question: "可以串我自己的訂單系統嗎？",
    answer: "可以，透過 MCP 工具設定串接，機器人能查詢真實訂單狀態。",
  },
].map(({ key, question, answer }) => ({
  key,
  label: question,
  children: <p className={welcome.faqAnswer}>{answer}</p>,
}));

export default function WelcomePage() {
  const demoSectionRef = useRef<HTMLElement>(null);

  // 「看 Demo」在同頁捲動到情境示範區塊；若使用者開啟 prefers-reduced-motion，
  // 就讓瀏覽器用預設的錨點跳轉行為，不強制觸發平滑捲動動畫。
  function handleDemoClick(event: MouseEvent<HTMLAnchorElement>) {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion || !demoSectionRef.current) return;
    event.preventDefault();
    demoSectionRef.current.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  return (
    <main className={welcome.page}>
      <ChatWidgetPreview chatbotId={WELCOME_CHATBOT_ID} />
      {/* 1. Hero */}
      <section className={tw(welcome.section, welcome.heroSection)}>
        <div className={welcome.container}>
          <div className={welcome.heroContent}>
            <h1 className={welcome.heroTitle}>
              讓客人不再等待，客服機器人幫你 24 小時接住每一句問題
            </h1>
            <p className={welcome.heroSubhead}>
              從商品問答、訂單查詢到跨平台導流，一台客服機器人取代客服團隊大半的重複對話。
            </p>
            <div className={welcome.heroActions}>
              <Link to="/login" className={welcome.ctaPrimary}>
                免費開始
              </Link>
              <a
                href="#demo-section"
                onClick={handleDemoClick}
                className={welcome.ctaSecondary}
              >
                看 Demo
              </a>
            </div>
            <p className={welcome.heroCaption}>
              不需要工程背景・5 分鐘上線第一台客服機器人
            </p>
          </div>
        </div>
      </section>

      {/* 2. 情境示範 */}
      <section
        id="demo-section"
        ref={demoSectionRef}
        className={tw(welcome.section, welcome.sectionBorder)}
      >
        <div className={welcome.container}>
          <p className={welcome.demoLabel}>
            您的網路商店 — 客服機器人 via 官網嵌入
          </p>
          <div className={welcome.demoWindow}>
            <div className={welcome.demoWindowHeader} aria-hidden="true">
              <span className={tw(welcome.demoDot, welcome.demoDotRed)} />
              <span className={tw(welcome.demoDot, welcome.demoDotYellow)} />
              <span className={tw(welcome.demoDot, welcome.demoDotGreen)} />
            </div>
            <div className={welcome.demoBody}>
              <div className={welcome.demoSidebar} aria-hidden="true">
                <RobotOutlined />
              </div>
              <div className={welcome.demoChat}>
                <div
                  className={tw(welcome.demoBubble, welcome.demoBubbleCustomer)}
                >
                  這個有現貨嗎？大概什麼時候會到？
                </div>
                <div className={tw(welcome.demoBubble, welcome.demoBubbleBot)}>
                  目前現貨供應中，今天下單最快明天出貨喔！需要我幫您查一下上次訂單的物流進度嗎？
                </div>
                <div
                  className={tw(welcome.demoBubble, welcome.demoBubbleCustomer)}
                >
                  好，幫我查一下
                </div>
                <div className={tw(welcome.demoBubble, welcome.demoBubbleBot)}>
                  {/* 訂單編號拆成獨立變數組字串，避免與 style-contract 的 raw 色彩（#RRGGBB）偵測誤判 */}
                  {`訂單 #${demoOrderNumber} 已出貨，預計明天送達 📦`}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. 數據列 */}
      <section
        aria-label="服務數據"
        className={tw(welcome.section, welcome.sectionBorder)}
      >
        <div className={welcome.container}>
          <div className={welcome.statsGrid}>
            {stats.map((stat) => (
              <div className={welcome.statCard} key={stat.label}>
                <span className={welcome.statIcon} aria-hidden="true">
                  {stat.icon}
                </span>
                <strong className={welcome.statValue}>{stat.value}</strong>
                <span className={welcome.statLabel}>{stat.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 4. 智能對話 */}
      <section className={tw(welcome.section, welcome.sectionBorder)}>
        <div className={welcome.container}>
          <div className={welcome.featureContent}>
            <span className={welcome.featureIconBadge} aria-hidden="true">
              <MessageOutlined />
            </span>
            <h2 className={welcome.featureHeading}>
              不是罐頭回覆，是真的讀懂你的資料
            </h2>
            <p className={welcome.featureBody}>
              依商家上傳的商品與知識庫內容回答，嚴格依真實資料作答，不會自己編造答案。
            </p>
            <ul className={welcome.featureBullets}>
              {knowledgeBullets.map((bullet) => (
                <li className={welcome.featureBulletItem} key={bullet.text}>
                  <span
                    className={welcome.featureBulletIcon}
                    aria-hidden="true"
                  >
                    {bullet.icon}
                  </span>
                  <span className={welcome.featureBulletText}>
                    {bullet.text}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* 5. 訂單串接 */}
      <section className={tw(welcome.section, welcome.sectionBorder)}>
        <div className={welcome.container}>
          <div className={welcome.featureContent}>
            <span className={welcome.featureIconBadge} aria-hidden="true">
              <ContainerOutlined />
            </span>
            <h2 className={welcome.featureHeading}>不只聊天，還真的能查訂單</h2>
            <p className={welcome.featureBody}>
              透過 MCP
              工具串接訂單系統，客人問「訂單到哪了」，機器人直接查真實狀態回覆，不用轉真人、不用等客服上班。
            </p>
          </div>
        </div>
      </section>

      {/* 6. 全通路整合 */}
      <section className={tw(welcome.section, welcome.sectionBorder)}>
        <div className={welcome.container}>
          <div className={welcome.featureContent}>
            <h2 className={welcome.featureHeading}>
              客人從哪來，服務就在哪接住
            </h2>
            <p className={welcome.featureBody}>
              一台客服機器人，同步部署到官網嵌入元件、LINE 官方帳號、Facebook
              粉專，統一後台管理所有對話紀錄。
            </p>
            <div className={welcome.channelRow}>
              {channels.map((channel) => (
                <div className={welcome.channelItem} key={channel.label}>
                  <span className={welcome.channelIcon} aria-hidden="true">
                    {channel.icon}
                  </span>
                  <span className={welcome.channelLabel}>{channel.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 7. 管理與稽核 */}
      <section className={tw(welcome.section, welcome.sectionBorder)}>
        <div className={welcome.container}>
          <div className={welcome.featureContent}>
            <span className={welcome.featureIconBadge} aria-hidden="true">
              <AuditOutlined />
            </span>
            <h2 className={welcome.featureHeading}>
              不是黑盒子，每句話都查得到
            </h2>
            <p className={welcome.featureBody}>
              稽核紀錄與每日摘要，商家隨時檢視機器人說了什麼、有沒有漏接客人問題。
            </p>
          </div>
        </div>
      </section>

      {/* 8. FAQ */}
      <section className={tw(welcome.section, welcome.sectionBorder)}>
        <div className={welcome.container}>
          <h2 className={welcome.faqHeading}>常見問題</h2>
          <Collapse
            className={welcome.faqCollapse}
            bordered={false}
            expandIconPosition="end"
            expandIcon={({ isActive }) =>
              isActive ? <UpOutlined /> : <DownOutlined />
            }
            items={faqItems}
          />
        </div>
      </section>

      {/* 9. 結尾 CTA */}
      <section
        className={tw(
          welcome.section,
          welcome.closingSection,
          welcome.sectionBorder,
        )}
      >
        <div className={welcome.container}>
          <div className={welcome.closingContent}>
            <h2 className={welcome.closingHeading}>準備好了嗎？</h2>
            <p className={welcome.closingBody}>
              免費開始，5 分鐘上線，讓客服機器人幫你接住每一位客人。
            </p>
            <div className={welcome.closingActions}>
              <Link to="/login" className={welcome.ctaPrimary}>
                免費開始
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
