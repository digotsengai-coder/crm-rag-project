import CheckCircleOutlined from "@ant-design/icons/CheckCircleOutlined";
import DatabaseOutlined from "@ant-design/icons/DatabaseOutlined";
import MessageOutlined from "@ant-design/icons/MessageOutlined";
import WarningOutlined from "@ant-design/icons/WarningOutlined";
import Alert from "antd/es/alert";
import Button from "antd/es/button";
import Empty from "antd/es/empty";
import { Link } from "react-router-dom";
import AdminPageLayout from "../components/AdminPageLayout";
import OrderTable from "../components/OrderTable";
import { useOrders } from "../hooks/useOrders";
import { ui } from "../uiStyles";
import { tw } from "../utils/tw";

export default function DashboardPage() {
  const { orders, isLoading, error, reload } = useOrders();
  const orderMetrics = orders.reduce(
    (metrics, order) => {
      const status = order.Status.toLowerCase();
      if (status === "completed" || status === "delivered")
        metrics.completed += 1;
      if (status === "pending" || status === "processing") metrics.pending += 1;
      return metrics;
    },
    { completed: 0, pending: 0 },
  );

  return (
    <AdminPageLayout
      title="儀表板"
      description="掌握服務狀況，快速處理訂單，提供更好的客戶體驗。"
      headerExtra={
        <time>
          {new Intl.DateTimeFormat("zh-TW", {
            year: "numeric",
            month: "long",
            day: "numeric",
            weekday: "short",
          }).format(new Date())}
        </time>
      }
    >
      <section className={ui.metricGrid} aria-label="營運摘要">
        <article className={ui.metricCard}>
          <span className={tw(ui.metricIcon, ui.metricTeal)}>
            <MessageOutlined />
          </span>
          <div>
            <span>今日對話</span>
            <strong>待串接</strong>
            <small>對話分析功能規劃中</small>
          </div>
        </article>
        <article className={ui.metricCard}>
          <span className={tw(ui.metricIcon, ui.metricBlue)}>
            <CheckCircleOutlined />
          </span>
          <div>
            <span>已完成訂單</span>
            <strong>{isLoading ? "—" : orderMetrics.completed}</strong>
            <small>依目前載入資料計算</small>
          </div>
        </article>
        <article className={ui.metricCard}>
          <span className={tw(ui.metricIcon, ui.metricIndigo)}>
            <DatabaseOutlined />
          </span>
          <div>
            <span>知識庫文件</span>
            <strong>待串接</strong>
            <small>RAG 管理功能規劃中</small>
          </div>
        </article>
        <article className={ui.metricCard}>
          <span className={tw(ui.metricIcon, ui.metricOrange)}>
            <WarningOutlined />
          </span>
          <div>
            <span>待處理訂單</span>
            <strong>{isLoading ? "—" : orderMetrics.pending}</strong>
            <small>待確認與處理中</small>
          </div>
        </article>
      </section>

      <section className={tw(ui.surface, ui.insightPlaceholder)}>
        <div className={ui.sectionHeading}>
          <div>
            <h2>商品與 RAG 洞察</h2>
            <p>整合商品銷售與知識庫使用數據，發掘客戶需求與服務機會。</p>
          </div>
          <span className={ui.periodChip}>最近 30 天</span>
        </div>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <>
              <strong>圖表功能規劃中</strong>
              <span>資料介面完成後，將呈現商品與 RAG 分析。</span>
            </>
          }
        />
      </section>

      <section className={tw(ui.surface, ui.recentOrders)}>
        <div className={ui.sectionHeading}>
          <div>
            <h2>最近訂單</h2>
            <p>即時掌握訂單處理進度，快速回應客戶需求。</p>
          </div>
          <Link to="/orders">前往訂單管理 →</Link>
        </div>
        {error ? (
          <Alert
            type="error"
            showIcon
            message={error}
            action={
              <Button size="small" onClick={reload}>
                重新載入
              </Button>
            }
          />
        ) : (
          <OrderTable orders={orders} loading={isLoading} compact />
        )}
      </section>
    </AdminPageLayout>
  );
}
