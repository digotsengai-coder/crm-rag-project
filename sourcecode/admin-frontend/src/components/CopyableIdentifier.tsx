import Typography from "antd/es/typography";
import { ui } from "../uiStyles";

const { Text } = Typography;

interface CopyableIdentifierProps {
  label: string;
  value: string;
  contentClassName?: string;
}

export default function CopyableIdentifier({
  label,
  value,
  contentClassName,
}: CopyableIdentifierProps) {
  return (
    <Text
      className={ui.copyableIdentifier}
      copyable={{
        text: value,
        tooltips: ["複製識別碼", "已複製識別碼"],
      }}
    >
      <span className={contentClassName}>
        {label ? `${label}：` : null}
        {value}
      </span>
    </Text>
  );
}
