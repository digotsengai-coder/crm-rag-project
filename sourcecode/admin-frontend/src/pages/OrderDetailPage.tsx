import ArrowLeftOutlined from "@ant-design/icons/ArrowLeftOutlined";
import Alert from "antd/es/alert";
import Button from "antd/es/button";
import Descriptions from "antd/es/descriptions";
import Result from "antd/es/result";
import Skeleton from "antd/es/skeleton";
import { useNavigate, useParams } from "react-router-dom";
import { OrderApiError } from "../api/orders";
import AdminPageLayout from "../components/AdminPageLayout";
import StatusTag from "../components/StatusTag";
import type { AdminOrder } from "../types/order";
import { ui } from "../uiStyles";
import { tw } from "../utils/tw";
import { useOrderQuery } from "../hooks/useAdminQueries";

const moneyFormatter = new Intl.NumberFormat("zh-TW", {
  style: "currency",
  currency: "TWD",
  maximumFractionDigits: 0,
});

export default function OrderDetailPage() {
  const navigate = useNavigate();
  const { orderId = "" } = useParams();
  const orderQuery = useOrderQuery(orderId);
  const order = orderQuery.data ?? null;
  const error = orderQuery.error
    ? {
        message: orderQuery.error.message,
        status:
          orderQuery.error instanceof OrderApiError
            ? orderQuery.error.status
            : undefined,
      }
    : null;

  const backButton = (
    <Button
      type="text"
      icon={<ArrowLeftOutlined />}
      onClick={() => navigate("/orders")}
    >
      返回訂單列表
    </Button>
  );

  if (error?.status === 404)
    return (
      <AdminPageLayout
        title="訂單詳情"
        description={orderId}
        headerLeading={backButton}
        variant="detail"
      >
        <Result
          status="404"
          title="找不到訂單"
          subTitle={error.message}
          extra={
            <Button type="primary" onClick={() => navigate("/orders")}>
              返回訂單列表
            </Button>
          }
        />
      </AdminPageLayout>
    );

  return (
    <AdminPageLayout
      title="訂單詳情"
      description={order?.NewOrderID || orderId}
      headerLeading={backButton}
      headerExtra={order && <StatusTag status={order.Status} />}
      variant="detail"
    >
      <section className={tw(ui.surface, ui.detailSurface)}>
        {error ? (
          <Alert type="error" showIcon message={error.message} />
        ) : !order ? (
          <Skeleton active paragraph={{ rows: 8 }} />
        ) : (
          <>
            <h2>訂單資訊</h2>
            <Descriptions bordered column={{ xs: 1, sm: 2, lg: 3 }}>
              <Descriptions.Item label="訂單編號">
                {order.NewOrderID || order.id}
              </Descriptions.Item>
              <Descriptions.Item label="原始編號">
                {order.OrderID}
              </Descriptions.Item>
              <Descriptions.Item label="訂單日期">
                {order.OrderDate}
              </Descriptions.Item>
              <Descriptions.Item label="付款方式">
                {order.PaymentMethod}
              </Descriptions.Item>
              <Descriptions.Item label="折扣">
                {order.Discount}
              </Descriptions.Item>
              <Descriptions.Item label="訂單金額">
                {moneyFormatter.format(order.OrderValue)}
              </Descriptions.Item>
            </Descriptions>
            <h2>商品資訊</h2>
            <Descriptions bordered column={{ xs: 1, sm: 2, lg: 3 }}>
              <Descriptions.Item label="商品編號">
                {order.ProductID}
              </Descriptions.Item>
              <Descriptions.Item label="商品名稱">
                {order.ProductName}
              </Descriptions.Item>
              <Descriptions.Item label="分類">
                {order.Category}
              </Descriptions.Item>
              <Descriptions.Item label="數量">
                {order.Quantity}
              </Descriptions.Item>
              <Descriptions.Item label="單價">
                {moneyFormatter.format(order.UnitPrice)}
              </Descriptions.Item>
              <Descriptions.Item label="銷售金額">
                {moneyFormatter.format(order.Sales)}
              </Descriptions.Item>
            </Descriptions>
            <h2>顧客資訊</h2>
            <Descriptions bordered column={{ xs: 1, sm: 2, lg: 3 }}>
              <Descriptions.Item label="顧客編號">
                {order.CustomerID}
              </Descriptions.Item>
              <Descriptions.Item label="電話">
                {order.PhoneNumber}
              </Descriptions.Item>
              <Descriptions.Item label="城市">{order.City}</Descriptions.Item>
              <Descriptions.Item label="顧客分群">
                {order.CustomerSegment}
              </Descriptions.Item>
              <Descriptions.Item label="年齡">{order.Age}</Descriptions.Item>
              <Descriptions.Item label="加入日期">
                {order.SignupDate}
              </Descriptions.Item>
            </Descriptions>
          </>
        )}
      </section>
    </AdminPageLayout>
  );
}
