export interface AdminOrder {
  id: string;
  OrderID: number;
  CustomerID: number;
  OrderDate: string;
  ProductID: number;
  Quantity: number;
  Discount: number;
  PaymentMethod: string;
  Status: string;
  Age: number;
  City: string;
  SignupDate: string;
  CustomerSegment: string;
  ProductName: string;
  Category: string;
  UnitPrice: number;
  Sales: number;
  OrderValue: number;
  NewOrderID: string | null;
  PhoneNumber: string;
}

export interface AdminOrderListResponse {
  count: number;
  orders: AdminOrder[];
}
