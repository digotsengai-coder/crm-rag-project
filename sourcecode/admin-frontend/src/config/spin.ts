import type { SpinProps } from "antd/es/spin";

export const standardSpinProps = {
  size: "large",
} satisfies SpinProps;

export const fullscreenSpinProps = {
  ...standardSpinProps,
  tip: "載入中…",
  fullscreen: true,
} satisfies SpinProps;
