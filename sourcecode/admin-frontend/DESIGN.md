---
version: "alpha"
name: CRM Console Admin
description: Light enterprise CRM administration interface built with Tailwind CSS v4 and Ant Design 5.
colors:
  primary: "#1769e0"
  canvas: "#f5f8fc"
  surface: "#ffffff"
  surface-subtle: "#f7f9fc"
  text: "#16213e"
  heading: "#0f2148"
  heading-secondary: "#152750"
  text-secondary: "#53617a"
  muted: "#71809a"
  text-subtle: "#7b889d"
  border: "#e2e8f0"
  agent-action: "#142671"
  agent-avatar: "#1769e0"
  agent-avatar-background: "#e6f1ff"
  agent-border: "#d7e3f8"
  agent-title: "#0a0a0a"
typography:
  label:
    fontFamily: "Noto Sans TC, PingFang TC, Microsoft JhengHei, sans-serif"
    fontSize: "0.6875rem"
  caption:
    fontFamily: "Noto Sans TC, PingFang TC, Microsoft JhengHei, sans-serif"
    fontSize: "0.8125rem"
  nav-title:
    fontFamily: "Noto Sans TC, PingFang TC, Microsoft JhengHei, sans-serif"
    fontSize: "1.0625rem"
  icon-control:
    fontFamily: "Noto Sans TC, PingFang TC, Microsoft JhengHei, sans-serif"
    fontSize: "1.1875rem"
  card-heading:
    fontFamily: "Noto Sans TC, PingFang TC, Microsoft JhengHei, sans-serif"
    fontSize: "1.375rem"
rounded:
  compact: "9px"
  control: "10px"
  default: "12px"
  metric: "14px"
  surface: "15px"
  agent-card: "16px"
  pill: "999px"
spacing:
  0: "0px"
  1: "4px"
  2: "8px"
  3: "12px"
  4: "16px"
  5: "20px"
  6: "24px"
  7: "28px"
  8: "32px"
  10: "40px"
components:
  app-shell:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.text}"
  page-heading:
    textColor: "{colors.heading}"
  section-heading:
    textColor: "{colors.heading-secondary}"
  secondary-text:
    textColor: "{colors.text-secondary}"
  muted-text:
    textColor: "{colors.muted}"
  subtle-text:
    textColor: "{colors.text-subtle}"
  table-header:
    backgroundColor: "{colors.surface-subtle}"
    textColor: "{colors.text-secondary}"
  bordered-surface:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.surface}"
  divider:
    backgroundColor: "{colors.border}"
  chatbot-action:
    textColor: "{colors.agent-action}"
  chatbot-avatar:
    backgroundColor: "{colors.agent-avatar-background}"
    textColor: "{colors.agent-avatar}"
  chatbot-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.agent-title}"
    rounded: "{rounded.agent-card}"
  chatbot-card-border:
    backgroundColor: "{colors.agent-border}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
  button-default:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.surface}"
    padding: "{spacing.6}"
  content-surface:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.surface}"
  status-tag:
    rounded: "{rounded.pill}"
---

## Overview

CRM Console Admin is a restrained, light enterprise administration interface. It prioritizes scanability, predictable form and table behavior, and clear information hierarchy over decorative effects. Navy text establishes hierarchy, blue identifies primary actions, and a small blue-to-teal gradient is reserved for the brand mark.

The UI uses two coordinated styling systems:

- **Tailwind CSS v4** owns page layout, responsive behavior, custom surfaces, spacing, typography utilities, and narrowly scoped overrides.
- **Ant Design 5** owns controls and interaction-heavy components such as buttons, forms, inputs, selects, tables, cards, drawers, modals, dropdowns, pagination, alerts, empty states, and loading indicators.

The runtime sources of truth are `src/styles.css`, `src/theme/adminTheme.ts`, `src/uiStyles.ts`, and the shared components under `src/components`. This is the Admin frontend's canonical design specification; it records the current system and does not introduce a new visual direction.

## Colors

### Core palette

- **Primary (`#1769e0`)** — primary calls to action, selected navigation, active tabs, links, and focus emphasis.
- **Canvas (`#f5f8fc`)** — application background behind all content surfaces.
- **Surface (`#ffffff`)** — cards, drawers, menus, inputs, headers, and other elevated content.
- **Surface subtle (`#f7f9fc`)** — table headers, secondary groups, chart tracks, and quiet backgrounds.
- **Text (`#16213e`)** — standard high-emphasis body content.
- **Heading (`#0f2148`)** and **heading secondary (`#152750`)** — page and section hierarchy.
- **Text secondary (`#53617a`)**, **muted (`#71809a`)**, and **text subtle (`#7b889d`)** — descriptions, metadata, hints, and supporting information.
- **Border (`#e2e8f0`)** — default low-contrast outlines and separators.

### Feature accents

ChatBot cards use a contained family of agent colors: `agent-action`, `agent-avatar`, `agent-avatar-background`, `agent-border`, and `agent-title`. Metric cards additionally use teal, blue, indigo, and orange variants already defined in `uiStyles.ts`; these variants are limited to metric icon treatments and must not become new primary colors.

The brand mark is the only established gradient: teal `#11b9af` to blue `#1878ed`. Do not apply this gradient to buttons, cards, page backgrounds, or charts.

Status colors come from Ant Design semantic values (`success`, `processing`, `warning`, `error`, and `default`). Status meaning must always include visible text; color alone is not sufficient. Order status mappings belong in `StatusTag` rather than page-local mappings.

## Typography

The font stack is `Noto Sans TC`, `PingFang TC`, `Microsoft JhengHei`, then `sans-serif`. It is shared by Tailwind and the root Ant Design theme.

- Page titles use a responsive `27–34px` size, deep navy, and slightly tight tracking.
- Section headings use approximately `18px` and the secondary heading color.
- Standard body and control text is generally `13–14px`.
- Captions and table content use `13px` (`caption`).
- Auxiliary labels use `11–12px`; `label` is `11px`.
- Card headings use `22px` only in centered authentication and selection cards.
- Data values and monetary columns should use tabular figures when alignment matters.

Use weight to communicate hierarchy: bold or semibold for headings and key values, medium or semibold for labels and navigation, and regular weight for prose. Avoid tight tracking on body text.

## Layout

### Application shell

`AdminLayout` is the only application shell. Do not create page-specific headers or sidebars.

- Desktop sidebar: `224px` expanded and `76px` collapsed; sticky and full viewport height.
- Header: `65px` high, sticky, translucent white with a subtle blur and bottom border.
- Main content: desktop padding `22px 28px 40px`; at `899px` and below it becomes `20px 16px 32px`.
- At `899px` and below, the sidebar is removed and navigation appears in a `260px` Ant Design Drawer.
- The navigation area scrolls independently when items exceed its height so the brand mark and version caption remain available.

### Page composition

Authenticated content pages should use `AdminPageLayout`, which provides the single `<main>`, page heading, description, optional leading/extra content, selected merchant context, and a `16px` vertical stack.

Use `ui.surface` for generic content sections and `ui.settingsCard` for settings-oriented Ant Design Cards. Repeated settings cards use `ui.settingsCardGrid`. Detail pages use `variant="detail"` and `ui.detailSurface`.

Page hierarchy is:

1. Application Header and Sidebar or Drawer.
2. One page title and description.
3. Optional merchant context or settings tabs.
4. Cards, surfaces, tables, or detail sections.
5. Primary page action aligned to the lower right when it applies to the complete form.

## Spacing

Spacing follows Tailwind's 4px base rhythm, with established half and quarter steps where the current interface requires them. Prefer the common machine-readable scale in the frontmatter for new work.

- Page-level and sibling-card gap: usually `16px`.
- Card body padding: `24px` desktop, `16px` at `620px` and below.
- Section heading padding: approximately `22–24px` horizontally and on top, `12px` below.
- Form field spacing: Ant Design vertical Form defaults unless a shared `ui.*` pattern specifies otherwise.
- Inline action gap: `8–12px`.
- Table toolbar bottom gap: `18px`.
- Mobile layouts stack toolbars and page actions rather than compressing controls.

Do not add margins directly to neighboring Cards to construct page rhythm. Let `AdminPageLayout`, `Space`, grid, or flex gap own the relationship.

## Elevation & Depth

Depth is intentionally shallow. Layout is communicated primarily with surface color and low-contrast borders.

- Standard surfaces have a border and little or no shadow.
- Settings cards use `0 1px 2px rgb(15 33 72 / 0.06)`.
- Login and ChatBot selection cards use `0 20px 40px rgb(15 33 72 / 0.08)`.
- Dropdown menus use `0 16px 36px rgb(15 33 72 / 0.14)`.
- The brand mark uses a small colored shadow tied to its icon.
- RAG drag-active feedback may temporarily use a stronger blue focus ring and deeper shadow to communicate the drop target.

Avoid stacking multiple shadows on neighboring surfaces, heavy dark shadows, decorative glow, glassmorphism, or blur outside established header/modal behavior.

## Shapes

Rounded corners are soft but controlled:

- Compact chips and dense rows: `9px`.
- Buttons, inputs, selects, pagination, and standard controls: `10px`.
- Ant Design global fallback radius: `12px`.
- Metric cards: `14px`.
- Standard surfaces and settings cards: `15px`.
- ChatBot cards and centered login/selection cards: `16px`.
- Tags and status pills: fully rounded.

Borders are normally `1px`, solid, and use the shared border color. A one-sided Tailwind border (`border-t`, `border-r`, `border-b`, or `border-l`) must not be combined with `border-solid`, because that can cause browser-default widths on the other sides.

## Components

### Layout, navigation, and header

- Use `AdminLayout` for the shell and `AdminPageLayout` for authenticated pages.
- Navigation uses Ant Design `Menu`; active items use the primary blue on a pale blue background.
- Settings subsections use `ChatbotSettingsTabs`. Tabs may horizontally scroll rather than wrap when space is limited.
- The account menu and sidebar toggle live in the shared Header. Icon-only controls require an accessible name and a Tooltip.
- Navigation icons use `@ant-design/icons`; do not mix emoji or a second icon family at the same hierarchy.

### Cards and surfaces

- Use Ant Design `Card` with `ui.settingsCard` for settings forms, configuration summaries, and audit content.
- Use `ui.surface` plus `ui.sectionHeading` for dashboard and table sections that need a custom internal header.
- Use `ui.metricGrid`, `ui.metricCard`, and one of the four existing metric icon variants for dashboard metrics.
- Adjacent cards must share radius, border, background, shadow, and padding behavior.

### Buttons

- Use Ant Design `Button`; do not recreate buttons with styled `div` or `span` elements.
- Use `type="primary"` for the single dominant page or form action.
- Use default buttons for secondary actions, `type="link"` for low-emphasis table navigation, and `danger` only for destructive actions.
- Async actions show `loading` and remain disabled through Ant Design's loading behavior.
- Icon-only buttons require `aria-label`; add Tooltip text when the meaning is not already visible.
- Keep action order stable. On narrow settings pages, action groups stretch and stack with the primary action remaining visually dominant.

### Forms, inputs, and selects

- Use Ant Design `Form` with `layout="vertical"` for settings and modal forms.
- Every editable or copyable field should appear inside a `Form.Item` with a visible label. Use `extra` for persistent help or constraints.
- Use Ant Design `Input`, `Input.Password`, `InputNumber`, `Select`, `Checkbox`, and `Switch`; rely on global theme tokens for their base appearance.
- Validation messages belong to the related `Form.Item` and should explain the correction.
- Read-only copy fields use the current `Input.Search` pattern: value on the left and an outlined, icon-only copy `Button` on the right. The button must be passed directly to `enterButton` so Ant Design preserves its Search layout.
- `CopyableIdentifier` remains the compact metadata pattern used in the ChatBot list; it is not the settings-form copy field.
- Radio has no project-specific variant. If introduced, use Ant Design defaults and the existing form rhythm before defining any new styling.

### Tables, lists, and descriptions

- Reuse `OrderTable` for order data and preserve horizontal scrolling for wide tables.
- Toolbars place search/filter controls first and counts or secondary actions last; below `620px`, they become a single column.
- Table cells and tags use compact typography. Actions remain visibly actionable and keyboard operable.
- Order details use Ant Design `Descriptions` inside `ui.detailSurface`, grouped under meaningful `h2` headings.
- Lists use Ant Design `List` and should supply a useful empty message.

### Modal, drawer, dropdown, and confirmation

- Use Ant Design `Modal`, `Drawer`, `Dropdown`, and `Popconfirm` instead of custom overlays.
- Modal forms use vertical layout and retain Ant Design focus management.
- Destructive actions require `Popconfirm` or a Modal with explicit destructive copy.
- Dropdown triggers must be semantic, keyboard-focusable controls.
- Mobile navigation is the established left Drawer; do not introduce a separate mobile navigation pattern.

### Status, badges, and tags

- Use Ant Design `Tag` for statuses and compact category labels.
- Reuse `StatusTag` for order status mapping.
- Tags are pill-shaped, compact, and normally borderless in data tables.
- Never rely on the fill color without visible text.

### Pagination

- Use Ant Design Table pagination for tabular data.
- The current order pattern uses `10` rows per page, hides the size changer, and places pagination at the bottom right.
- Preserve the globally themed `10px` radius and white active background.

### Empty, loading, and error states

- Use Ant Design `Empty` when no data or feature content is available, with a short explanation and a relevant next action when possible.
- Use Table `loading`, `Spin`, or `Skeleton` for page data. Route-level Suspense uses a text status with `role="status"`.
- Use `Alert` for recoverable inline failures and `Result` for full-page failures.
- Retryable failures should expose a visible retry action.
- Do not represent loading, emptiness, success, or failure with an icon alone.

### Charts

- The current chart language is a compact horizontal bar chart built with CSS for small category datasets.
- Use the primary blue for bars, subtle surface color for tracks, and visible labels plus numeric counts.
- Dynamic bar width may remain a runtime inline style; static chart presentation belongs in `uiStyles.ts`.
- Do not add a chart library for a small static comparison unless interaction or scale requires it.

### Icons

- Use `@ant-design/icons` consistently.
- Navigation and labeled actions may pair an icon with visible text.
- Decorative icons beside visible labels should not carry unique meaning.
- Standalone interactive icons need `aria-label`, keyboard access, and a visible focus state.

## Responsive Design

The current system is desktop-first in implementation but provides explicit compact behavior:

- **At `1180px` and below:** dashboard metric cards change from four columns to two.
- **At `899px` and below:** desktop Sidebar becomes a Drawer, content padding decreases, and secondary page-header date text is hidden.
- **At `760px` and below:** the ChatBot card grid changes from two columns to one. This is an existing page-specific breakpoint and should not be copied to unrelated layouts.
- **At `620px` and below:** metric cards use one column; card padding shrinks; table tools, RAG filters, settings actions, and other multi-control groups stack vertically; low-priority decorative/header information may be hidden.

Wide tables retain horizontal scrolling. Long identifiers, URLs, file paths, and labels must either wrap safely or use ellipsis with access to the full value. New responsive behavior should reuse `1180px`, `899px`, and `620px` unless a component has a demonstrated need for a distinct breakpoint.

## Interaction States

- Ant Design supplies the default hover, active, focus, loading, disabled, validation, and selected states for controls.
- Tailwind overrides may refine these states only within a narrowly scoped shared `ui.*` style.
- Primary blue communicates selection and primary action; destructive red is reserved for destructive actions.
- Hover must not be the only way to discover or perform an action.
- Keyboard focus must remain visible. Do not remove Ant Design focus outlines unless an equivalent accessible focus indicator replaces them.
- The global shell applies reduced-motion behavior to descendant transitions and scrolling. RAG overlay animation is disabled under `prefers-reduced-motion`.
- Copy actions show success or failure through the page's Ant Design message API.
- Form submissions and network actions display loading feedback and prevent duplicate activation.

## Do's and Don'ts

### Do

- Reuse `AdminLayout`, `AdminPageLayout`, `ChatbotSettingsTabs`, `OrderTable`, `StatusTag`, and existing `ui.*` patterns before creating a new abstraction.
- Use the Tailwind theme tokens and the root Ant Design theme for recurring colors, radii, typography, and control appearance.
- Keep complete, statically scannable utility strings in `uiStyles.ts` and compose them through `tw()`.
- Use Ant Design props, global/component tokens, `className`, `rootClassName`, and `classNames` in that order; use scoped descendant variants only when the public API is insufficient.
- Keep one primary CTA per screen or form and place it consistently.
- Provide visible labels, helper text, validation, loading, empty, error, hover, focus, and disabled states.
- Test the established `1180px`, `899px`, and `620px` breakpoints after UI changes.
- Run formatting, type checking, the Admin style contract, and production build after style changes.

### Don't

- Do not load Tailwind Preflight or add traditional selector classes to `styles.css`.
- Do not dynamically construct Tailwind utility names.
- Do not add page-level or nested Ant Design `ConfigProvider` themes.
- Do not pass CSS variables into Ant theme seed tokens; Ant needs concrete color values to derive interaction states.
- Do not use static inline styles when a Tailwind utility can express the value. Runtime widths, image URLs, and runtime theme values are the exceptions.
- Do not introduce new primary colors, gradients, fonts, shadows, radii, or nearby breakpoints for one page.
- Do not duplicate status maps or rebuild Ant Design controls with non-semantic HTML.
- Do not apply broad `!important` rules; use the important modifier only for the property Ant Design otherwise overrides.
- Do not combine a one-sided border utility with `border-solid`.
- Do not add glassmorphism, large decorative gradients, heavy elevation, or a second icon language.

## New Page Checklist

- Use `AdminLayout`, `AdminPageLayout`, and the established surface or section-heading pattern for authenticated content pages.
- Reuse existing shared components and Ant Design controls before creating page-specific replacements.
- Keep styling in `ui.*` mappings with static Tailwind utilities; do not add selector classes or duplicate available tokens.
- Run `npm run format`, `npm run style:check`, and the relevant production build after styling changes.
- Reuse the existing color, type, radius, spacing, state, loading, empty, and error patterns.
- Verify the `1180px`, `899px`, and `620px` breakpoints plus keyboard access for interactive controls.
- Do not include personal information or local absolute paths in documentation, screenshots, or test fixtures.

### Current inconsistencies to preserve as findings, not patterns

- `uiStyles.ts` contains several page-specific raw colors. They describe the current UI but should not be copied when an existing semantic token serves the same role.
- `760px` is used only by the ChatBot grid while the documented shared breakpoints are `1180px`, `899px`, and `620px`.
- The ChatBot avatar blue on its pale blue background measures `4.45:1` in the Google `design.md` linter, narrowly below its `4.5:1` WCAG AA text threshold; preserve the current values until a deliberate token correction is approved.
