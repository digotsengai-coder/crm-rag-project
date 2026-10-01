import EyeOutlined from "@ant-design/icons/EyeOutlined";
import SearchOutlined from "@ant-design/icons/SearchOutlined";
import Button from "antd/es/button";
import Input from "antd/es/input";
import Space from "antd/es/space";
import Table from "antd/es/table";
import Typography from "antd/es/typography";
import type { ColumnsType } from "antd/es/table";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { AdminOrder } from "../types/order";
import StatusTag from "./StatusTag";
import { ui } from "../uiStyles";

const moneyFormatter = new Intl.NumberFormat("zh-TW", {
  style: "currency",
  currency: "TWD",
  maximumFractionDigits: 0,
});

export default function OrderTable({
  orders,
  loading,
  compact = false,
}: {
  orders: AdminOrder[];
  loading: boolean;
  compact?: boolean;
}) {
  const navigate = useNavigate();
  const [keyword, setKeyword] = useState("");
  const filteredOrders = useMemo(() => {
    const query = keyword.trim().toLowerCase();
    if (!query) return orders;
    return orders.filter((order) =>
      [
        order.id,
        order.NewOrderID,
        order.OrderID,
        order.CustomerID,
        order.ProductName,
      ].some((value) =>
        String(value ?? "")
          .toLowerCase()
          .includes(query),
      ),
    );
  }, [keyword, orders]);

  const columns: ColumnsType<AdminOrder> = [
    {
      title: "訂單編號",
      key: "orderCode",
      width: 170,
      render: (_, order) => (
        <Typography.Link onClick={() => navigate(`/orders/${order.id}`)}>
          {order.NewOrderID || order.id}
        </Typography.Link>
      ),
    },
    {
      title: "訂單日期",
      dataIndex: "OrderDate",
      width: 130,
      sorter: (a, b) => a.OrderDate.localeCompare(b.OrderDate),
    },
    { title: "客戶編號", dataIndex: "CustomerID", width: 120 },
    { title: "商品名稱", dataIndex: "ProductName", ellipsis: true },
    {
      title: "金額",
      dataIndex: "OrderValue",
      width: 120,
      align: "right",
      sorter: (a, b) => a.OrderValue - b.OrderValue,
      render: (value: number) => moneyFormatter.format(value),
    },
    {
      title: "狀態",
      dataIndex: "Status",
      width: 100,
      filters: [...new Set(orders.map((order) => order.Status))].map(
        (value) => ({ text: value, value }),
      ),
      onFilter: (value, order) => order.Status === value,
      render: (status: string) => <StatusTag status={status} />,
    },
    {
      title: "操作",
      key: "action",
      width: 88,
      render: (_, order) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/orders/${order.id}`)}
        >
          查看
        </Button>
      ),
    },
  ];

  return (
    <div className={ui.orderTable}>
      {!compact && (
        <div className={ui.tableTools}>
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="搜尋訂單、客戶或商品"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
          />
          <Space>
            <span className={ui.resultCount}>
              共 {filteredOrders.length} 筆
            </span>
          </Space>
        </div>
      )}
      <Table
        rowKey="id"
        columns={columns}
        dataSource={compact ? filteredOrders.slice(0, 10) : filteredOrders}
        loading={loading}
        pagination={
          compact
            ? false
            : {
                pageSize: 10,
                showSizeChanger: false,
                position: ["bottomRight"],
              }
        }
        scroll={{ x: 900 }}
        onRow={(order) => ({
          onDoubleClick: () => navigate(`/orders/${order.id}`),
        })}
      />
    </div>
  );
}
