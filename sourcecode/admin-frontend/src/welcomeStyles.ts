import { tw } from "./utils/tw";

// 遵循 uiStyles.ts 既有的 reducedMotion 寫法：尊重 prefers-reduced-motion，
// 關閉這個頁面上的漸層/位移類動畫與 transition。
const reducedMotion = tw(
    "motion-reduce:transition-none motion-reduce:[&_*]:animate-none motion-reduce:[&_*]:transition-none",
  ),
  ctaBase = tw(
    "inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-lg px-6 text-sm font-semibold transition-colors duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-welcome-accent",
    reducedMotion,
  );

export const welcome = {
  page: tw("min-h-screen bg-welcome-bg text-welcome-text", reducedMotion),
  container: tw("mx-auto w-full max-w-6xl px-6 max-[767px]:px-5"),
  section: tw("py-20 max-[1023px]:py-16 max-[767px]:py-12"),
  sectionBorder: tw("border-t border-welcome-border"),

  // 1. Hero
  heroSection: tw("pt-24 pb-20 max-[1023px]:pt-18 max-[767px]:pt-14"),
  heroContent: tw("mx-auto grid max-w-[46rem] gap-6 text-center"),
  heroTitle: tw(
    "text-[clamp(28px,4.2vw,48px)] leading-[1.25] font-extrabold tracking-[-0.02em] text-white",
  ),
  heroSubhead: tw(
    "mx-auto max-w-[38rem] text-lg leading-relaxed text-welcome-text max-[767px]:text-base",
  ),
  heroActions: tw(
    "mt-2 flex flex-wrap items-center justify-center gap-4 max-[480px]:flex-col max-[480px]:items-stretch",
  ),
  heroCaption: tw("mt-1 text-sm text-welcome-text-muted"),
  ctaPrimary: tw(
    ctaBase,
    "border border-solid border-transparent bg-welcome-accent text-welcome-accent-text hover:bg-welcome-accent/90",
  ),
  ctaSecondary: tw(
    ctaBase,
    "border border-solid border-welcome-border bg-transparent text-white hover:border-welcome-accent hover:text-welcome-accent",
  ),

  // 2. 情境示範
  demoLabel: tw("mb-4 text-center text-sm font-medium text-welcome-text-muted"),
  demoWindow: tw(
    "mx-auto max-w-[42rem] overflow-hidden rounded-xl border border-solid border-welcome-border bg-welcome-bg-card shadow-[0_24px_60px_rgb(0_0_0/0.35)]",
  ),
  demoWindowHeader: tw(
    "flex items-center gap-1.5 border-b border-welcome-border px-4 py-3",
  ),
  demoDot: tw("size-3 rounded-full"),
  demoDotRed: tw("bg-red-500"),
  demoDotYellow: tw("bg-amber-400"),
  demoDotGreen: tw("bg-emerald-500"),
  demoBody: tw("flex max-[480px]:flex-col"),
  demoSidebar: tw(
    "grid w-14 shrink-0 place-items-center border-r border-welcome-border bg-welcome-bg text-xl text-welcome-accent max-[480px]:hidden",
  ),
  demoChat: tw("grid min-w-0 flex-1 gap-3 p-5 max-[767px]:p-4"),
  demoBubble: tw(
    "max-w-[80%] rounded-lg px-4 py-2.5 text-sm leading-relaxed break-words",
  ),
  demoBubbleCustomer: tw(
    "justify-self-end bg-welcome-accent text-welcome-accent-text",
  ),
  demoBubbleBot: tw("justify-self-start bg-welcome-bg text-white"),

  // 3. 數據列
  statsGrid: tw(
    "grid grid-cols-4 gap-4 max-[1023px]:grid-cols-2 max-[480px]:grid-cols-1",
  ),
  statCard: tw(
    "grid gap-3 rounded-xl border border-solid border-welcome-border bg-welcome-bg-card p-6 text-center",
  ),
  statIcon: tw(
    "mx-auto grid size-11 place-items-center rounded-lg bg-welcome-accent/10 text-xl text-welcome-accent",
  ),
  statValue: tw("text-3xl font-extrabold text-welcome-accent"),
  statLabel: tw("text-sm text-welcome-text-muted"),

  // 4-7. Feature sections（智能對話／訂單串接／全通路整合／管理與稽核）
  featureContent: tw("mx-auto grid max-w-[42rem] gap-5 text-center"),
  featureIconBadge: tw(
    "mx-auto grid size-12 place-items-center rounded-lg bg-welcome-accent/10 text-2xl text-welcome-accent",
  ),
  featureHeading: tw(
    "text-2xl leading-snug font-bold text-white max-[767px]:text-xl",
  ),
  featureBody: tw("text-base leading-relaxed text-welcome-text"),
  featureBullets: tw("mt-2 grid gap-3 text-left"),
  featureBulletItem: tw(
    "flex items-start gap-3 rounded-lg border border-solid border-welcome-border bg-welcome-bg-card p-4",
  ),
  featureBulletIcon: tw("mt-0.5 shrink-0 text-lg text-welcome-accent"),
  featureBulletText: tw("text-sm leading-relaxed text-welcome-text"),
  channelRow: tw(
    "mt-2 flex flex-wrap items-center justify-center gap-6 max-[480px]:flex-col",
  ),
  channelItem: tw("grid place-items-center gap-2"),
  channelIcon: tw(
    "grid size-14 place-items-center rounded-lg border border-solid border-welcome-border bg-welcome-bg-card text-2xl text-welcome-accent",
  ),
  channelLabel: tw("text-sm text-welcome-text-muted"),

  // 8. FAQ
  faqHeading: tw(
    "mb-8 text-center text-2xl font-bold text-white max-[767px]:text-xl",
  ),
  faqAnswer: tw("text-sm leading-relaxed text-welcome-text-muted"),
  faqCollapse: tw(
    "mx-auto max-w-[42rem] rounded-xl! border! border-solid! border-welcome-border! bg-welcome-bg-card! [&_.ant-collapse-content]:bg-transparent! [&_.ant-collapse-content-box]:text-welcome-text-muted! [&_.ant-collapse-expand-icon]:text-welcome-text-muted! [&_.ant-collapse-header]:text-base! [&_.ant-collapse-header]:font-semibold! [&_.ant-collapse-header]:text-white! [&_.ant-collapse-item]:border-welcome-border!",
  ),

  // 9. 結尾 CTA
  closingSection: tw("text-center"),
  closingContent: tw("mx-auto grid max-w-[38rem] gap-5"),
  closingHeading: tw("text-3xl font-extrabold text-white max-[767px]:text-2xl"),
  closingBody: tw("text-base leading-relaxed text-welcome-text"),
  closingActions: tw("mt-2 flex justify-center"),
};
