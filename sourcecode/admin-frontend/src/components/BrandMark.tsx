import CustomerServiceFilled from "@ant-design/icons/CustomerServiceFilled";
import { ui } from "../uiStyles";
import { tw } from "../utils/tw";

export default function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={tw(ui.brandMark, compact && ui.brandMarkCompact)}
      aria-label="CRM Console"
    >
      <span className={ui.brandIcon}>
        <CustomerServiceFilled />
      </span>
      {!compact && <strong>CRM Console</strong>}
    </div>
  );
}
