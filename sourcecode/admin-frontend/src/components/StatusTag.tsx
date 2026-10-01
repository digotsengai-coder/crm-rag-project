import Tag from "antd/es/tag";

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  completed: { color: "success", label: "已完成" },
  delivered: { color: "success", label: "已送達" },
  processing: { color: "processing", label: "處理中" },
  pending: { color: "warning", label: "待確認" },
  cancelled: { color: "error", label: "已取消" },
  returned: { color: "default", label: "已退貨" },
};

export default function StatusTag({ status }: { status: string }) {
  const normalized = status.trim().toLowerCase();
  const display = STATUS_MAP[normalized] ?? {
    color: "default",
    label: status || "未知",
  };
  return <Tag color={display.color}>{display.label}</Tag>;
}
