import type { AdminOrder, AdminOrderListResponse } from "../types/order";

const ORDER_API_URL =
  import.meta.env.VITE_ADMIN_API_URL || "http://localhost:8001";

export class OrderApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "OrderApiError";
  }
}

async function requestOrderApi<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`${ORDER_API_URL}${path}`, { signal });

  if (!response.ok) {
    throw new OrderApiError(
      response.status === 404
        ? "找不到指定的訂單。"
        : "訂單服務暫時無法使用，請稍後再試。",
      response.status,
    );
  }

  return response.json() as Promise<T>;
}

export function getOrders(
  signal?: AbortSignal,
): Promise<AdminOrderListResponse> {
  return requestOrderApi<AdminOrderListResponse>(
    "/api/v1/Order?limit=100&order_by=OrderDate",
    signal,
  );
}

export function getOrder(
  orderId: string,
  signal?: AbortSignal,
): Promise<AdminOrder> {
  return requestOrderApi<AdminOrder>(
    `/api/v1/Order/${encodeURIComponent(orderId)}`,
    signal,
  );
}
