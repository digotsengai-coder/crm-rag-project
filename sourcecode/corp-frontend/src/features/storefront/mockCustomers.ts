export interface MockCustomer {
  CustomerID: number;
  Age: number;
  City: string;
  SignupDate: string;
  PhoneNumber: string;
}

// 僅用於前端結帳展示，避免混用真實顧客資料。
export const MOCK_CUSTOMERS = [
  {
    CustomerID: 900001,
    Age: 28,
    City: "Taipei",
    SignupDate: "2022-01-14",
    PhoneNumber: "0900-000-001",
  },
  {
    CustomerID: 900002,
    Age: 35,
    City: "New Taipei",
    SignupDate: "2022-03-22",
    PhoneNumber: "0900-000-002",
  },
  {
    CustomerID: 900003,
    Age: 42,
    City: "Taoyuan",
    SignupDate: "2022-06-09",
    PhoneNumber: "0900-000-003",
  },
  {
    CustomerID: 900004,
    Age: 31,
    City: "Taichung",
    SignupDate: "2022-08-17",
    PhoneNumber: "0900-000-004",
  },
  {
    CustomerID: 900005,
    Age: 26,
    City: "Tainan",
    SignupDate: "2022-11-03",
    PhoneNumber: "0900-000-005",
  },
  {
    CustomerID: 900006,
    Age: 47,
    City: "Kaohsiung",
    SignupDate: "2023-01-19",
    PhoneNumber: "0900-000-006",
  },
  {
    CustomerID: 900007,
    Age: 24,
    City: "Hsinchu",
    SignupDate: "2023-02-27",
    PhoneNumber: "0900-000-007",
  },
  {
    CustomerID: 900008,
    Age: 53,
    City: "Keelung",
    SignupDate: "2023-04-11",
    PhoneNumber: "0900-000-008",
  },
  {
    CustomerID: 900009,
    Age: 38,
    City: "Chiayi",
    SignupDate: "2023-05-30",
    PhoneNumber: "0900-000-009",
  },
  {
    CustomerID: 900010,
    Age: 29,
    City: "Miaoli",
    SignupDate: "2023-07-08",
    PhoneNumber: "0900-000-010",
  },
  {
    CustomerID: 900011,
    Age: 45,
    City: "Changhua",
    SignupDate: "2023-09-16",
    PhoneNumber: "0900-000-011",
  },
  {
    CustomerID: 900012,
    Age: 33,
    City: "Nantou",
    SignupDate: "2023-10-24",
    PhoneNumber: "0900-000-012",
  },
  {
    CustomerID: 900013,
    Age: 57,
    City: "Yunlin",
    SignupDate: "2024-01-12",
    PhoneNumber: "0900-000-013",
  },
  {
    CustomerID: 900014,
    Age: 22,
    City: "Pingtung",
    SignupDate: "2024-03-05",
    PhoneNumber: "0900-000-014",
  },
  {
    CustomerID: 900015,
    Age: 40,
    City: "Yilan",
    SignupDate: "2024-04-29",
    PhoneNumber: "0900-000-015",
  },
  {
    CustomerID: 900016,
    Age: 36,
    City: "Hualien",
    SignupDate: "2024-06-18",
    PhoneNumber: "0900-000-016",
  },
  {
    CustomerID: 900017,
    Age: 49,
    City: "Taitung",
    SignupDate: "2024-08-07",
    PhoneNumber: "0900-000-017",
  },
  {
    CustomerID: 900018,
    Age: 27,
    City: "Penghu",
    SignupDate: "2024-09-21",
    PhoneNumber: "0900-000-018",
  },
  {
    CustomerID: 900019,
    Age: 61,
    City: "Kinmen",
    SignupDate: "2025-02-14",
    PhoneNumber: "0900-000-019",
  },
  {
    CustomerID: 900020,
    Age: 44,
    City: "Lienchiang",
    SignupDate: "2025-05-26",
    PhoneNumber: "0900-000-020",
  },
] as const satisfies readonly MockCustomer[];
