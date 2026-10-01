import {
  Package,
  Truck,
  CheckCircle2,
  Clock,
  type LucideIcon,
} from "lucide-react";
import { tw } from "../utils/tw";
import { widgetUi } from "../widgetStyles";

interface OrderStage {
  key: string;
  label: string;
  icon: LucideIcon;
}

interface OrderCardProps {
  code: string;
  status: number;
  eta: string;
  items: string;
}

const ORDER_STAGES: OrderStage[] = [
  { key: "placed", label: "已下單", icon: Clock },
  { key: "shipped", label: "備貨出貨", icon: Package },
  { key: "delivering", label: "配送中", icon: Truck },
  { key: "done", label: "已送達", icon: CheckCircle2 },
];

const nodeStateStyles = {
  done: widgetUi.nodeDone,
  active: widgetUi.nodeActive,
  pending: widgetUi.nodePending,
} as const;

const labelStateStyles = {
  done: widgetUi.labelDone,
  active: widgetUi.labelActive,
  pending: "",
} as const;

export default function OrderCard({
  code,
  status,
  eta,
  items,
}: OrderCardProps) {
  return (
    <div className={tw(widgetUi.row, widgetUi.rowBot)}>
      <div className={widgetUi.orderCard}>
        <div className={widgetUi.orderHead}>
          <span className={widgetUi.orderCode}>訂單 #{code}</span>
          <span className={widgetUi.orderEta}>預計 {eta} 送達</span>
        </div>
        <p className={widgetUi.orderItems}>{items}</p>
        <div className={widgetUi.timeline}>
          {ORDER_STAGES.map((stage, stageIndex) => {
            const Icon = stage.icon;
            const state =
              stageIndex < status
                ? "done"
                : stageIndex === status
                  ? "active"
                  : "pending";
            return (
              <div className={widgetUi.timelineStep} key={stage.key}>
                <div
                  className={tw(widgetUi.timelineNode, nodeStateStyles[state])}
                >
                  <Icon size={14} strokeWidth={2.4} />
                </div>
                <span
                  className={tw(
                    widgetUi.timelineLabel,
                    labelStateStyles[state],
                  )}
                >
                  {stage.label}
                </span>
                {stageIndex < ORDER_STAGES.length - 1 && (
                  <div
                    className={tw(
                      widgetUi.timelineBar,
                      stageIndex < status && widgetUi.timelineBarDone,
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
