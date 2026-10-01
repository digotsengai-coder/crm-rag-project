import type { ThemeConfig } from "antd/es/config-provider";

export const adminThemeValues = {
  primary: "#1769e0",
  text: "#16213e",
  heading: "#0f2148",
  textSecondary: "#53617a",
  muted: "#71809a",
  canvas: "#f5f8fc",
  surface: "#ffffff",
  surfaceSubtle: "#f7f9fc",
  border: "#e2e8f0",
} as const;

export const adminTheme = {
  token: {
    colorPrimary: adminThemeValues.primary,
    colorText: adminThemeValues.text,
    colorTextHeading: adminThemeValues.heading,
    colorTextSecondary: adminThemeValues.muted,
    colorTextDescription: adminThemeValues.muted,
    colorBgLayout: adminThemeValues.canvas,
    colorBgContainer: adminThemeValues.surface,
    colorBgElevated: adminThemeValues.surface,
    colorBorder: adminThemeValues.border,
    colorBorderSecondary: adminThemeValues.border,
    colorSplit: adminThemeValues.border,
    borderRadius: 12,
    fontFamily:
      '"Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif',
  },
  components: {
    Layout: {
      bodyBg: adminThemeValues.canvas,
      headerBg: adminThemeValues.surface,
      siderBg: adminThemeValues.surface,
      lightSiderBg: adminThemeValues.surface,
    },
    Menu: {
      itemBorderRadius: 10,
      itemHeight: 48,
      itemColor: "#42516c",
      itemSelectedColor: adminThemeValues.primary,
      itemSelectedBg: "#e8f3ff",
    },
    Card: {
      headerBg: "transparent",
      headerFontSize: 17,
      headerHeight: 58,
      headerPadding: 24,
      colorBorderSecondary: adminThemeValues.border,
    },
    Collapse: {
      headerBg: "transparent",
      contentBg: "transparent",
      headerPadding: "12px 24px",
      contentPadding: 24,
      colorBorder: adminThemeValues.border,
      colorTextHeading: "#152750",
    },
    Table: {
      headerBg: adminThemeValues.surfaceSubtle,
      headerColor: adminThemeValues.textSecondary,
      borderColor: adminThemeValues.border,
    },
    Button: { borderRadius: 10 },
    Input: { borderRadius: 10, colorBorder: adminThemeValues.border },
    Select: { borderRadius: 10, colorBorder: adminThemeValues.border },
    Drawer: { colorBgElevated: adminThemeValues.surface },
    Pagination: { borderRadius: 10, itemActiveBg: adminThemeValues.surface },
    Tag: { borderRadiusSM: 999 },
    Upload: { colorBorder: adminThemeValues.border },
  },
} satisfies ThemeConfig;
