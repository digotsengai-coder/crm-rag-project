import Spin from "antd/es/spin";
import { standardSpinProps } from "../config/spin";
import { ui } from "../uiStyles";

export default function CardLoading({
  label = "資料讀取中",
}: {
  label?: string;
}) {
  return (
    <div className={ui.cardLoading} role="status" aria-label={label}>
      <Spin {...standardSpinProps} />
    </div>
  );
}
