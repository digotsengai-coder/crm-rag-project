import { tw } from "./utils/tw";

export const widgetUi = {
  root: tw(
    "fixed right-6 bottom-6 z-[1000] flex min-h-0 w-auto items-end justify-end bg-transparent p-0 font-widget text-(--ccw-text) max-[480px]:right-0 max-[480px]:bottom-0 max-[480px]:min-h-0 max-[480px]:items-stretch max-[480px]:justify-stretch [&_*]:box-border [&_*::after]:box-border [&_*::before]:box-border",
  ),
  launcher: tw(
    "flex size-14 cursor-pointer items-center justify-center rounded-full border-0 bg-(--ccw-primary) text-widget-on-primary shadow-widget-launcher transition-transform duration-150 ease-in-out hover:-translate-y-0.5 focus-visible:outline-[3px] focus-visible:outline-offset-3 focus-visible:outline-(--ccw-focus) max-[480px]:mr-4 max-[480px]:mb-4",
  ),
  panel: tw(
    "flex h-[min(580px,calc(100dvh-48px))] w-[380px] max-w-full animate-widget-pop flex-col overflow-hidden rounded-(--ccw-border-radius) bg-(--ccw-surface) shadow-widget-panel motion-reduce:animate-none max-[480px]:h-dvh max-[480px]:w-screen max-[480px]:rounded-none",
  ),
  quickReplies: tw("flex shrink-0 flex-wrap gap-2"),
  chip: tw(
    "cursor-pointer rounded-full border border-solid border-widget-border bg-(--ccw-surface) px-3 py-1.5 text-chip text-(--ccw-primary-strong) hover:border-(--ccw-primary) focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-(--ccw-focus)",
  ),
  header: tw(
    "flex items-center justify-between bg-(--ccw-primary) px-widget-panel py-4 text-widget-on-primary",
  ),
  headerBrand: tw("flex items-center gap-2.5"),
  headerIcon: tw(
    "flex size-widget-icon items-center justify-center rounded-control bg-white/12",
  ),
  headerLogo: tw("size-6 object-contain"),
  headerTitle: tw(
    "font-widget-display text-widget-title leading-[1.2] font-semibold",
  ),
  headerStatus: tw(
    "mt-0.5 flex items-center gap-widget-icon-gap text-xs text-widget-on-primary",
  ),
  statusDot: tw("inline-block size-1.5 rounded-full bg-widget-success"),
  closeButton: tw(
    "flex size-11 cursor-pointer items-center justify-center rounded-lg border-0 bg-transparent text-widget-on-primary hover:bg-white/10 focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-(--ccw-focus)",
  ),
  modelBar: tw(
    "flex items-center gap-2 border-b border-widget-border bg-(--ccw-surface) px-3.5 py-2 text-xs [&_label]:shrink-0 [&_label]:text-widget-muted",
  ),
  modelSelect: tw(
    "w-0 flex-1 rounded-lg! border! border-solid! border-widget-border! bg-(--ccw-surface) px-2 py-1 text-xs text-(--ccw-text) focus-visible:outline-[3px] focus-visible:outline-offset-1 focus-visible:outline-(--ccw-focus)",
  ),
  messages: tw(
    "flex flex-1 flex-col gap-3 overflow-y-auto bg-widget-background p-widget-panel",
  ),
  row: tw("flex"),
  rowUser: tw("justify-end"),
  rowBot: tw("justify-start"),
  bubble: tw(
    "max-w-[80%] rounded-message px-widget-message py-2.5 text-sm leading-[1.55]",
  ),
  bubbleUser: tw("rounded-br-1 bg-(--ccw-primary) text-widget-on-primary"),
  bubbleBot: tw(
    "rounded-bl-1 border border-solid border-widget-border bg-(--ccw-surface) text-(--ccw-text)",
  ),
  bubbleText: tw("m-0 whitespace-pre-wrap"),
  sourceTag: tw(
    "flex w-full p-0 text-label text-widget-muted [background:none]",
  ),
  typing: tw("flex items-center gap-1 p-widget-message"),
  dot: tw(
    "size-1.5 animate-widget-bounce rounded-full bg-widget-subtle motion-reduce:animate-none",
  ),
  dotSecond: tw("[animation-delay:150ms]"),
  dotThird: tw("[animation-delay:300ms]"),
  orderCard: tw(
    "max-w-[88%] rounded-message border border-solid border-widget-border bg-(--ccw-surface) px-4 pt-3.5 pb-4",
  ),
  orderHead: tw("mb-1 flex items-baseline justify-between"),
  orderCode: tw(
    "font-widget-display text-caption font-semibold text-(--ccw-primary-strong)",
  ),
  orderEta: tw("text-xs font-semibold text-(--ccw-primary-strong)"),
  orderItems: tw("mt-0 mb-3.5 text-caption text-widget-muted"),
  timeline: tw("flex items-start"),
  timelineStep: tw("relative flex flex-1 flex-col items-center text-center"),
  timelineNode: tw(
    "z-1 flex size-widget-node items-center justify-center rounded-full",
  ),
  nodeDone: tw("bg-widget-success text-widget-on-primary"),
  nodeActive: tw("bg-(--ccw-primary) text-widget-on-primary"),
  nodePending: tw("bg-widget-border text-widget-subtle"),
  timelineLabel: tw("mt-1.5 text-micro whitespace-nowrap text-widget-muted"),
  labelActive: tw("font-semibold text-(--ccw-primary-strong)"),
  labelDone: tw("font-semibold text-widget-success"),
  timelineBar: tw(
    "absolute top-widget-message left-1/2 h-0.5 w-full bg-widget-border",
  ),
  timelineBarDone: tw("bg-widget-success"),
  inputBar: tw(
    "flex items-end gap-2 border-t border-widget-border bg-(--ccw-surface) px-3.5 py-3",
  ),
  input: tw(
    "max-h-widget-input-max min-h-10 flex-1 resize-none rounded-field! border! border-solid! border-widget-border! bg-(--ccw-surface) px-widget-message py-2.5 text-sm leading-widget text-(--ccw-text) outline-none focus-visible:border-(--ccw-primary)! focus-visible:shadow-[0_0_0_3px_color-mix(in_srgb,var(--ccw-focus)_24%,transparent)]",
  ),
  sendButton: tw(
    "flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-control border-0 bg-(--ccw-primary) text-widget-on-primary hover:brightness-92 focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-(--ccw-focus) disabled:cursor-not-allowed disabled:bg-widget-border disabled:text-widget-subtle",
  ),
};
