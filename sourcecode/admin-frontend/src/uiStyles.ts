import { tw } from "./utils/tw";

const menu = tw(
    "[&_.ant-menu]:min-h-0 [&_.ant-menu]:flex-1 [&_.ant-menu]:[scrollbar-width:thin] [&_.ant-menu]:[scrollbar-color:#c5d0df_transparent] [&_.ant-menu]:overflow-x-hidden [&_.ant-menu]:overflow-y-auto [&_.ant-menu]:border-e-0! [&_.ant-menu]:bg-transparent [&_.ant-menu]:px-2 [&_.ant-menu]:py-1 [&_.ant-menu-item]:my-1 [&_.ant-menu-item]:font-semibold [&_.ant-menu::-webkit-scrollbar]:w-1.5 [&_.ant-menu::-webkit-scrollbar-thumb]:rounded-full [&_.ant-menu::-webkit-scrollbar-thumb]:bg-[#c5d0df] [&_.ant-menu::-webkit-scrollbar-track]:bg-transparent",
  ),
  reducedMotion = tw(
    "motion-reduce:[&_*]:scroll-auto motion-reduce:[&_*]:duration-[.01ms] motion-reduce:[&_*::after]:duration-[.01ms] motion-reduce:[&_*::before]:duration-[.01ms]",
  );

export const ui = {
  adminShell: tw("min-h-screen", reducedMotion),
  desktopSider: tw(
    "sticky! top-0 h-screen border-r border-admin-border bg-white/94! [&_.ant-layout-sider-children]:relative [&_.ant-layout-sider-children]:flex [&_.ant-layout-sider-children]:min-h-full [&_.ant-layout-sider-children]:flex-col",
    menu,
  ),
  mobileNavigation: tw(
    "relative flex min-h-full flex-col max-[899px]:h-screen max-[899px]:bg-white",
    menu,
  ),
  siderBrand: tw(
    "flex min-h-16.25 items-center border-b border-[#e6ebf2] px-5.5 py-0",
  ),
  brandMark: tw(
    "flex items-center gap-2.5 whitespace-nowrap text-[#0c1e45] [&_strong]:text-xl [&_strong]:tracking-[-.04em]",
  ),
  brandMarkCompact: tw("[&_strong]:hidden"),
  brandIcon: tw(
    "grid size-7.5 place-items-center rounded-compact bg-[linear-gradient(135deg,#11b9af,#1878ed)] text-nav-title text-white shadow-[0_6px_16px_rgb(24_120_237/.18)]",
  ),
  tenantBlock: tw(
    "grid gap-1 px-6 pt-5.5 pb-3.5 [&_span]:text-xs [&_span]:text-[#91a0b7] [&_strong]:text-sm [&_strong]:text-[#293958]",
  ),
  tenantSwitcher: tw("inline-flex cursor-pointer items-center gap-1"),
  tenantManageLink: tw(
    "mt-0.5 cursor-pointer justify-self-start border-0 bg-transparent p-0 text-xs font-semibold text-admin-primary hover:underline",
  ),
  siderCaption: tw("mt-auto p-6 text-xs leading-[1.75] text-[#9aa9bd]"),
  adminHeader: tw(
    "sticky top-0 z-20 flex h-16.25! items-center justify-between border-b border-[#e6ebf2] bg-[rgba(255,255,255,.9)]! py-0! pr-7! pl-3.5! backdrop-blur-[14px] max-[899px]:pr-4.5! max-[899px]:pl-3.5!",
  ),
  menuToggle: tw(
    "h-10.5! w-10.5! rounded-control! border! border-solid! border-[#dce4ee]! text-icon-control! text-[#173664]! hover:bg-[#eef5ff]! hover:text-admin-primary!",
  ),
  account: tw(
    "h-auto! border-0! bg-transparent! p-0! text-left! text-[#738099] hover:bg-transparent! [&_.ant-avatar]:bg-[#c8d0dc] [&_small]:text-xs [&_span]:grid [&_span]:leading-[1.25] max-[620px]:[&_span]:hidden [&_strong]:text-caption",
  ),
  accountDropdown: tw(
    "w-40! max-w-40! min-w-40! [&_.ant-dropdown-menu]:w-full!",
  ),
  accountDropdownEmail: tw(
    "cursor-default! text-xs! text-admin-text-subtle! opacity-100! [&_.ant-dropdown-menu-title-content]:break-all",
  ),
  adminContent: tw(
    "min-w-0 px-7 pt-5.5 pb-10 max-[899px]:px-4 max-[899px]:pt-5 max-[899px]:pb-8",
  ),
  routeLoading: tw(
    "grid min-h-60 place-items-center font-bold text-admin-muted",
  ),
  centeredPage: tw("grid min-h-screen place-items-center p-6"),
  loginCard: tw(
    "grid w-full max-w-[420px] gap-4 rounded-2xl bg-white p-8 shadow-[0_20px_40px_rgb(15_33_72/.08)] [&_h1]:m-0 [&_h1]:text-card-heading [&_h1]:text-admin-heading",
  ),
  loginActions: tw("flex flex-wrap items-center gap-3"),
  chatbotSelectCard: tw(
    "grid w-full max-w-[640px] gap-4 rounded-2xl bg-white p-8 shadow-[0_20px_40px_rgb(15_33_72/.08)] [&_h1]:m-0 [&_h1]:text-card-heading [&_h1]:text-admin-heading",
  ),
  chatbotsCardHeader: tw(
    "flex items-center justify-between gap-4 max-[620px]:items-start [&_h2]:m-0 [&_h2]:text-lg [&_h2]:text-admin-agent-title",
  ),
  chatbotsGrid: tw("mt-2.5 grid grid-cols-2 gap-3.5 max-[760px]:grid-cols-1"),
  chatbotCard: tw(
    "grid min-h-[138px] min-w-0 gap-2 rounded-agent-card border border-solid border-admin-agent-border bg-white p-3",
  ),
  chatbotCardTitle: tw(
    "flex min-w-0 items-center gap-3 [&_h3]:m-0 [&_h3]:overflow-hidden [&_h3]:text-base [&_h3]:text-ellipsis [&_h3]:whitespace-nowrap [&_h3]:text-admin-agent-title",
  ),
  chatbotTitleButton: tw(
    "block! h-auto! max-w-full! overflow-hidden! p-0! text-left! text-base! font-bold! text-ellipsis! whitespace-nowrap! text-admin-agent-title! hover:text-admin-agent-action!",
  ),
  chatbotAvatar: tw(
    "grid size-10 shrink-0 place-items-center rounded-full bg-admin-agent-avatar-bg text-base text-admin-agent-avatar",
  ),
  chatbotMenu: tw(
    "ml-auto size-10! shrink-0 rounded-control! border! border-solid! border-transparent! text-xl! text-admin-text-subtle hover:border-admin-border! hover:bg-admin-surface-subtle! [&[aria-expanded=true]]:border-admin-primary! [&[aria-expanded=true]]:bg-white! [&[aria-expanded=true]]:text-admin-primary!",
  ),
  chatbotDropdown: tw(
    "[&_.ant-dropdown-menu]:min-w-40! [&_.ant-dropdown-menu]:rounded-surface! [&_.ant-dropdown-menu]:border! [&_.ant-dropdown-menu]:border-solid! [&_.ant-dropdown-menu]:border-admin-border! [&_.ant-dropdown-menu]:bg-white! [&_.ant-dropdown-menu]:p-2! [&_.ant-dropdown-menu]:shadow-[0_16px_36px_rgb(15_33_72/.14)]! [&_.ant-dropdown-menu-item]:min-h-11! [&_.ant-dropdown-menu-item]:rounded-control! [&_.ant-dropdown-menu-item]:px-4! [&_.ant-dropdown-menu-item]:py-2.5! [&_.ant-dropdown-menu-item]:text-sm! [&_.ant-dropdown-menu-item]:font-medium! [&_.ant-dropdown-menu-item]:text-admin-heading! [&_.ant-dropdown-menu-item-danger.ant-dropdown-menu-item-active]:text-white! [&_.ant-dropdown-menu-item-danger.ant-dropdown-menu-item-active_.anticon]:text-white! [&_.ant-dropdown-menu-item-danger:hover]:text-white! [&_.ant-dropdown-menu-item-danger:hover_.anticon]:text-white! [&_.ant-dropdown-menu-item:not(.ant-dropdown-menu-item-danger):hover]:bg-admin-surface-subtle! [&_.ant-dropdown-menu-item:not(.ant-dropdown-menu-item-danger):hover]:text-admin-primary!",
  ),
  chatbotMetadata: tw(
    "grid text-caption leading-none text-admin-text-subtle [&_code]:w-fit [&_code]:max-w-full [&_code]:overflow-hidden [&_code]:text-ellipsis [&_code]:whitespace-nowrap",
  ),
  copyableIdentifier: tw(
    "inline-flex! max-w-full items-center text-caption! leading-normal! text-admin-text-subtle! [&_.ant-typography-copy]:rounded-sm! [&_.ant-typography-copy]:px-2! [&_.ant-typography-copy]:py-1! [&_.ant-typography-copy]:text-base! [&_.ant-typography-copy]:text-admin-text-subtle! [&_.ant-typography-copy]:hover:bg-admin-surface-subtle! [&>span]:min-w-0 [&>span]:break-all",
  ),
  settingsTabs: tw(
    "[&_.ant-tabs-ink-bar]:bg-admin-primary [&_.ant-tabs-nav]:mb-4 [&_.ant-tabs-nav]:overflow-x-auto [&_.ant-tabs-nav-list]:min-w-max [&_.ant-tabs-tab]:px-2 [&_.ant-tabs-tab]:py-3 [&_.ant-tabs-tab-active_.ant-tabs-tab-btn]:text-admin-primary! [&_.ant-tabs-tab-btn]:text-admin-text-subtle [&_.ant-tabs-tab-btn_span]:flex [&_.ant-tabs-tab-btn_span]:items-center [&_.ant-tabs-tab-btn_span]:gap-2",
  ),
  settingsCardGrid: tw("grid gap-4"),
  settingsCard: tw(
    "rounded-surface border border-solid border-admin-border bg-white text-admin-text-subtle shadow-[0_1px_2px_rgb(15_33_72/.06)] [&_.ant-card-body]:p-6 max-[620px]:[&_.ant-card-body]:p-4 [&_.ant-card-head]:border-admin-border [&_.ant-card-head]:px-6 max-[620px]:[&_.ant-card-head]:px-4",
  ),
  settingsPlaceholder: tw(
    "grid min-h-28 place-items-center rounded-control border border-dashed border-admin-border bg-admin-surface-subtle px-4 text-center text-caption text-admin-text-subtle",
  ),
  settingsActions: tw(
    "flex items-center justify-end gap-3 pt-1 max-[620px]:flex-col-reverse max-[620px]:items-stretch [&_.ant-btn]:min-w-24",
  ),
  auditLogTableToolbar: tw(
    "mb-4.5 flex items-center justify-end gap-2 max-[620px]:items-stretch max-[620px]:[&_.ant-select]:w-full",
  ),
  settingsAccountForm: tw(
    "mb-4! flex gap-2 max-[620px]:flex-col [&_.ant-form-item]:mb-0 max-[620px]:[&_.ant-form-item]:w-full max-[620px]:[&_.ant-input]:w-full",
  ),
  accountRoleTagPrimary: tw(
    "m-0! rounded-full! bg-admin-agent-avatar-bg! px-3! py-1! text-caption! font-semibold! text-admin-agent-avatar!",
  ),
  accountRoleTagDefault: tw(
    "m-0! rounded-full! bg-admin-surface-subtle! px-3! py-1! text-caption! font-semibold! text-admin-text-subtle!",
  ),
  pageHeading: tw(
    "flex min-h-19 items-start justify-between gap-6 [&_h1]:mt-0 [&_h1]:mb-1.25 [&_h1]:text-[clamp(27px,2.3vw,34px)] [&_h1]:tracking-[-.035em] [&_h1]:text-admin-heading [&_p]:m-0 [&_p]:text-sm [&_p]:text-admin-muted [&_time]:pt-2.5 [&_time]:text-caption [&_time]:text-admin-muted max-[899px]:[&_time]:hidden",
  ),
  pageHeaderGroup: tw("grid gap-1"),
  currentChatbotName: tw("py-2 text-sm text-[#556a94]"),
  pageContent: tw("flex w-full flex-col gap-4"),
  detailHeading: tw(
    "items-center [&_.ant-btn]:mt-0 [&_.ant-btn]:mr-0 [&_.ant-btn]:mb-2 [&_.ant-btn]:-ml-3 [&_.ant-btn]:text-[#62718a]",
  ),
  metricGrid: tw(
    "grid grid-cols-4 gap-3.5 max-[1180px]:grid-cols-2 max-[620px]:grid-cols-1",
  ),
  metricCard: tw(
    "flex min-h-[138px] items-center gap-4 rounded-metric border border-solid border-admin-border bg-white/88 p-5 max-[620px]:min-h-28 [&_div>span]:text-caption [&_div>span]:font-semibold [&_div>span]:text-admin-text-secondary [&_small]:text-label [&_small]:whitespace-nowrap [&_small]:text-[#93a0b4] [&_strong]:text-[28px] [&_strong]:leading-[1.2] [&_strong]:text-[#10234b] [&>div]:grid [&>div]:min-w-0 [&>div]:gap-0.75",
  ),
  metricIcon: tw(
    "grid size-13.5 shrink-0 place-items-center rounded-surface text-2xl",
  ),
  metricTeal: tw("bg-[#e5f8f7] text-[#039e9a]"),
  metricBlue: tw("bg-[#e9f2ff] text-admin-primary"),
  metricIndigo: tw("bg-[#edf0ff] text-[#505bdc]"),
  metricOrange: tw("bg-[#fff2e7] text-[#ed7b22]"),
  surface: tw(
    "overflow-hidden rounded-surface border border-solid border-admin-border bg-white/92",
  ),
  sectionHeading: tw(
    "flex items-center justify-between gap-5 px-6 pt-5.5 pb-3 max-[620px]:items-start max-[620px]:p-4.5 [&_a]:text-caption [&_a]:font-semibold [&_a]:whitespace-nowrap [&_a]:text-admin-primary [&_h2]:mt-0 [&_h2]:mb-1 [&_h2]:text-lg [&_h2]:text-admin-heading-secondary [&_p]:m-0 [&_p]:text-caption [&_p]:text-admin-text-subtle max-[620px]:[&_p]:max-w-[30ch]",
  ),
  periodChip: tw(
    "rounded-compact border border-solid border-[#dce4ee] px-3.25 py-2.25 text-xs text-[#65748c] max-[620px]:hidden",
  ),
  insightPlaceholder: tw(
    "min-h-[292px] [&_.ant-empty]:my-8.75 [&_.ant-empty-description]:grid [&_.ant-empty-description]:justify-items-center [&_.ant-empty-description]:gap-1.75 [&_.ant-empty-description]:text-[#8794a8]! [&_.ant-empty-description_span]:block [&_.ant-empty-description_span]:text-caption [&_.ant-empty-description_strong]:text-base [&_.ant-empty-description_strong]:text-[#1d3159]",
  ),
  recentOrders: tw(
    "min-h-[300px] [&_.ant-alert]:mx-6 [&_.ant-alert]:mt-4.5 [&_.ant-alert]:mb-6",
  ),
  ordersSurface: tw("p-5 max-[620px]:p-3.5"),
  orderTable: tw(
    "[&_.ant-btn-link]:px-0 [&_.ant-btn-link]:text-caption [&_.ant-table]:text-[#334360] [&_.ant-table-cell]:text-caption [&_.ant-tag]:m-0 [&_.ant-tag]:rounded-full [&_.ant-tag]:border-0 [&_.ant-tag]:font-semibold",
  ),
  tableTools: tw(
    "flex items-center justify-between gap-5 pb-4.5 max-[620px]:flex-col max-[620px]:items-stretch! [&_.ant-input-affix-wrapper]:max-w-[360px] max-[620px]:[&_.ant-input-affix-wrapper]:max-w-none",
  ),
  resultCount: tw("text-caption text-admin-text-subtle"),
  detailSurface: tw(
    "p-6 max-[620px]:p-3.5 [&_h2]:mt-0 [&_h2]:mb-1 [&_h2]:text-lg [&_h2]:text-admin-heading-secondary [&_h2:not(:first-child)]:mt-7",
  ),
  marginTop4: tw("mt-4"),
  inlineActions: tw("flex flex-wrap items-center gap-2"),
  fullWidth: tw("w-full [&>.ant-space-item]:w-full"),
  preWrap: tw("mt-4 whitespace-pre-wrap"),
  headingTag: tw(
    "mt-2.5 rounded-full border-0 px-3 py-1.25 font-semibold max-[620px]:hidden",
  ),
  ragUploadCollapse: tw(
    "rounded-surface bg-white/92! [&_.ant-collapse-expand-icon]:text-admin-text-secondary [&_.ant-collapse-expand-icon_.anticon]:text-base! [&>.ant-collapse-item]:border-b-0 [&>.ant-collapse-item>.ant-collapse-header]:min-h-14.5 [&>.ant-collapse-item>.ant-collapse-header]:items-center [&>.ant-collapse-item>.ant-collapse-header]:text-nav-title [&>.ant-collapse-item>.ant-collapse-header]:font-semibold [&>.ant-collapse-item>.ant-collapse-header]:text-admin-heading-secondary",
  ),
  ragDocumentsCard: tw(
    "rounded-surface bg-white/92 [&_.ant-btn-text.ant-btn-dangerous]:px-1 [&_.ant-btn-text.ant-btn-dangerous]:text-caption [&_.ant-table-cell]:text-caption [&_.ant-tag]:me-0 [&_.ant-tag]:rounded-full [&_.ant-tag]:border-0",
  ),
  ragField: tw(
    "grid min-w-0 gap-2 [&>.ant-typography]:text-xs [&>.ant-typography]:font-semibold",
  ),
  visuallyHidden: tw(
    "absolute size-px overflow-hidden whitespace-nowrap [clip-path:inset(50%)] [clip:rect(0_0_0_0)]",
  ),
  ragDragOverlay: tw(
    "pointer-events-none fixed inset-0 z-[1000] animate-rag-overlay-in bg-slate-900/42 backdrop-blur-[1px] motion-reduce:animate-none",
  ),
  ragDragging: tw(
    "relative z-[1001] [&.ant-upload-wrapper_.ant-upload-drag]:border-admin-primary [&.ant-upload-wrapper_.ant-upload-drag]:bg-[#f7fbff] [&.ant-upload-wrapper_.ant-upload-drag]:shadow-[0_0_0_4px_rgb(23_105_224/.18),0_18px_48px_rgb(7_28_62/.24)]",
  ),
  ragDragger: tw(
    "[&_.ant-upload-drag-icon]:mb-2.5! [&_.ant-upload-drag-icon_.anticon]:text-[42px]! [&_.ant-upload-drag-icon_.anticon]:text-admin-primary! [&_.ant-upload-hint]:text-xs! [&_.ant-upload-hint]:text-[#7c899d]! [&_.ant-upload-hint]:select-none [&_.ant-upload-text]:text-base! [&_.ant-upload-text]:font-[650]! [&_.ant-upload-text]:text-[#20345e]! [&_.ant-upload-text]:select-none [&.ant-upload-wrapper_.ant-upload-btn]:px-5 [&.ant-upload-wrapper_.ant-upload-btn]:pt-6.5 [&.ant-upload-wrapper_.ant-upload-btn]:pb-5.5 max-[620px]:[&.ant-upload-wrapper_.ant-upload-btn]:px-3.5 [&.ant-upload-wrapper_.ant-upload-drag]:rounded-surface [&.ant-upload-wrapper_.ant-upload-drag]:border-admin-border [&.ant-upload-wrapper_.ant-upload-drag]:bg-[linear-gradient(145deg,#f8fbff,#f4f8fd)] [&.ant-upload-wrapper_.ant-upload-drag:hover]:border-admin-primary [&.ant-upload-wrapper_.ant-upload-drag:hover]:bg-[#f2f7ff]",
  ),
  ragPickerActions: tw(
    "mt-4 justify-center max-[620px]:grid [&_.ant-btn]:min-w-33 [&_.ant-btn]:bg-white/86 max-[620px]:[&_.ant-btn]:w-full",
  ),
  ragUploadOptions: tw(
    "mt-4.5 grid grid-cols-2 gap-4.5 max-[620px]:grid-cols-1",
  ),
  ragSelectedFiles: tw(
    "mt-4.5 grid max-h-[238px] [scrollbar-width:thin] [scrollbar-color:#c5d0df_transparent] gap-1.75 overflow-y-auto pr-1",
  ),
  ragSelectedFile: tw(
    "grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2.75 rounded-compact border border-solid border-admin-border bg-white pt-2.25 pr-2.5 pb-2.25 pl-3.25 [&>.anticon]:text-[#4b73ae] [&>div]:flex [&>div]:min-w-0 [&>div]:items-center [&>div]:justify-between [&>div]:gap-3 max-[620px]:[&>div]:flex-col max-[620px]:[&>div]:items-start max-[620px]:[&>div]:gap-0.5 [&>div_.ant-typography:first-child]:min-w-0 [&>div_.ant-typography:first-child]:overflow-hidden [&>div_.ant-typography:first-child]:text-caption [&>div_.ant-typography:first-child]:text-ellipsis [&>div_.ant-typography:first-child]:whitespace-nowrap [&>div_.ant-typography:first-child]:text-[#30415f] [&>div_.ant-typography:last-child]:shrink-0 [&>div_.ant-typography:last-child]:text-label",
  ),
  ragSelectionSummary: tw(
    "mt-4.5 flex items-center justify-between gap-5 rounded-control bg-admin-surface-subtle px-4 py-3.5 max-[620px]:flex-col max-[620px]:items-stretch",
  ),
  ragReview: tw(
    "mt-5.5 grid gap-5.5 border-t border-admin-border pt-5.5 [&_.ant-table-cell]:text-caption [&_.ant-tag]:me-0 [&_.ant-tag]:rounded-full [&_.ant-tag]:border-0",
  ),
  ragReviewSection: tw("min-w-0"),
  ragDuplicateList: tw(
    "mt-2 mb-0 grid gap-1.25 pl-5 [&_li]:text-caption [&_li]:[overflow-wrap:anywhere] [&_li]:text-[#765b1b]",
  ),
  ragSubheading: tw(
    "mb-3 [&_h3]:mt-0 [&_h3]:mb-0.75 [&_h3]:text-sm [&_h3]:text-[#20345e] [&_p]:m-0 [&_p]:text-xs [&_p]:text-[#8390a4]",
  ),
  ragStaleList: tw("grid gap-2"),
  ragStaleRow: tw(
    "flex min-w-0 items-center gap-2.5 rounded-compact border border-solid border-admin-border! px-3 py-2.5 max-[620px]:flex-wrap max-[620px]:items-start [&_.ant-checkbox-wrapper]:min-w-0 [&_.ant-checkbox-wrapper]:flex-1 [&_.ant-checkbox-wrapper]:[overflow-wrap:anywhere] [&_.ant-checkbox-wrapper]:text-[#334360]",
  ),
  ragTableTools: tw(
    "mb-4.5 grid grid-cols-[minmax(220px,1.2fr)_minmax(220px,1fr)_auto] gap-3 max-[620px]:grid-cols-1",
  ),
  summaryPeriodControl: tw(
    "mb-4.5 flex items-center justify-between gap-3 max-[620px]:flex-col max-[620px]:items-stretch",
  ),
  summaryTable: tw(
    "[&_.ant-table-cell]:align-top [&_.ant-table-cell:first-child]:font-medium [&_.ant-table-cell:first-child]:text-[#20345e]",
  ),
  summaryChartLayout: tw(
    "grid min-w-0 grid-cols-[minmax(0,1.25fr)_minmax(260px,0.75fr)] gap-5 max-[760px]:grid-cols-1",
  ),
  summaryChart: tw(
    "grid min-w-0 gap-3 overflow-hidden rounded-none [&_.g2-legend]:max-w-full [&_.g2-legend]:flex-wrap [&+section]:border-admin-border max-[760px]:[&+section]:border-t min-[760px]:[&+section]:border-l",
  ),
  summaryPieChart: tw(
    "max-w-full min-w-0 max-[620px]:[&_.g2-legend-item]:text-caption [&_canvas]:max-w-full",
  ),
  summaryChartDetails: tw("p-3.5"),
  summaryChartDetailsHeading: tw(
    "flex items-start justify-between gap-3 max-[620px]:flex-wrap",
  ),
  summaryTableParagraph: tw("m-0! whitespace-pre-wrap"),
  summaryTableList: tw(
    "m-0 list-none p-0 [&_li]:pt-2 [&_li]:text-caption [&_li]:text-[#334360]",
  ),
  cardLoading: tw("grid min-h-60 place-items-center"),
};
