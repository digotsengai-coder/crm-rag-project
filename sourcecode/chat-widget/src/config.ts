import type { CSSProperties } from "react";

export interface WidgetTheme {
  primaryColor: string;
  surfaceColor: string;
  textColor: string;
  borderRadius: number;
}

export interface WidgetConfig {
  brandName: string;
  welcomeMessage: string;
  logoUrl: string | null;
  theme: WidgetTheme;
  quickReplies: string[];
}

export const DEFAULT_WIDGET_CONFIG: WidgetConfig = {
  brandName: "線上客服",
  welcomeMessage:
    "您好，我是線上客服，可以問我任何產品的規格、特色，或是輸入訂單編號查詢配送狀態喔。",
  logoUrl: null,
  theme: {
    primaryColor: "#315b7d",
    surfaceColor: "#ffffff",
    textColor: "#17212b",
    borderRadius: 20,
  },
  quickReplies: [
    "無線滑鼠支援多少 DPI？",
    "查詢訂單 A12345",
    "退貨要幾天內申請？",
  ],
};

type ThemeStyle = CSSProperties & Record<`--ccw-${string}`, string>;

export function toThemeStyle(theme: WidgetTheme): ThemeStyle {
  return {
    "--ccw-primary": theme.primaryColor,
    "--ccw-primary-strong": theme.primaryColor,
    "--ccw-focus": theme.primaryColor,
    "--ccw-surface": theme.surfaceColor,
    "--ccw-text": theme.textColor,
    "--ccw-border-radius": `${theme.borderRadius}px`,
  };
}
