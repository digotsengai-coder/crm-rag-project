import type {
  CartItem,
  CheckoutCustomer,
  CheckoutOrder,
  CheckoutResponse,
} from "./types";

const ORDER_API_BASE_URL =
  import.meta.env.VITE_API_CORP_URL || "http://localhost:8001";

export class OrderSubmissionError extends Error {}

function formatLocalDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function buildCheckoutOrders(
  customer: CheckoutCustomer,
  cartItems: CartItem[],
  orderDate = formatLocalDate(new Date()),
): CheckoutOrder[] {
  return cartItems.map(({ product, quantity }) => {
    const unitPrice = product.realPrice ?? 0;
    const orderValue = Number((unitPrice * quantity).toFixed(2));
    return {
      CustomerID: customer.CustomerID,
      OrderDate: orderDate,
      ProductID: product.productID,
      Quantity: quantity,
      Discount: 0,
      PaymentMethod: customer.PaymentMethod,
      Status: "Completed",
      Age: customer.Age,
      City: customer.City.trim(),
      SignupDate: customer.SignupDate,
      CustomerSegment: customer.CustomerSegment,
      ProductName: product.productNameEN,
      Category: product.category,
      UnitPrice: unitPrice,
      Sales: orderValue,
      OrderValue: orderValue,
      PhoneNumber: customer.PhoneNumber.trim(),
    };
  });
}

export async function submitCheckout(
  customer: CheckoutCustomer,
  cartItems: CartItem[],
): Promise<CheckoutResponse[]> {
  const orders = buildCheckoutOrders(customer, cartItems);
  return Promise.all(
    orders.map(async (order) => {
      const response = await fetch(
        `${ORDER_API_BASE_URL}/api/v1/collections/Order/docs`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ data: order }),
        },
      );

      if (!response.ok) {
        throw new OrderSubmissionError(
          `訂單送出失敗（${response.status}）。請確認訂單服務後重試。`,
        );
      }

      return response.json() as Promise<CheckoutResponse>;
    }),
  );
}
