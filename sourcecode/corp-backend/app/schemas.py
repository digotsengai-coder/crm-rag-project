from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 泛用 Firestore Document Schemas
# ---------------------------------------------------------------------------

class DocumentCreate(BaseModel):
    """
    建立文件請求資料結構。
    doc_id 為選填，未提供時 Firestore 將自動生成 UUID/DocID。
    """
    doc_id: Optional[str] = Field(None, description="自訂文件 ID (選填，未傳遞時自動生成)")
    data: Dict[str, Any] = Field(..., description="要儲存至 Firestore 文件的 JSON 鍵值對資料")


class DocumentUpdate(BaseModel):
    """
    更新文件請求資料結構。
    """
    data: Dict[str, Any] = Field(..., description="要更新至 Firestore 文件的欄位資料")
    merge: bool = Field(True, description="True 為增量更新 (Merge)，False 為完全覆蓋 (Overwrite)")


class DocumentResponse(BaseModel):
    """
    單一文件回應結構。
    """
    id: str = Field(..., description="Firestore 文件 ID")
    collection: str = Field(..., description="所屬 Collection 名稱")
    data: Dict[str, Any] = Field(..., description="文件內容")


class DocumentListResponse(BaseModel):
    """
    文件清單回應結構。
    """
    collection: str = Field(..., description="Collection 名稱")
    count: int = Field(..., description="取得文件數量")
    documents: List[DocumentResponse] = Field(default_factory=list, description="文件列表")


# ---------------------------------------------------------------------------
# 專屬 Firebase 訂單 (Order) Schemas
# ---------------------------------------------------------------------------

class OrderCreate(BaseModel):
    """
    新增 Firebase 訂單資料結構。
    """
    OrderID: Optional[Union[int, str]] = Field(None, description="訂單編號")
    CustomerID: Optional[Union[int, str]] = Field(0, description="顧客編號")
    OrderDate: Optional[str] = Field("", description="訂單日期")
    ProductID: Optional[Union[int, str]] = Field(0, description="產品編號")
    Quantity: Optional[Union[int, float]] = Field(1, description="購買數量")
    Discount: Optional[Union[int, float]] = Field(0.0, description="折扣金額/比例")
    PaymentMethod: Optional[str] = Field("", description="付款方式")
    Status: Optional[str] = Field("Completed", description="訂單狀態")
    Age: Optional[Union[int, str]] = Field(None, description="顧客年齡")
    City: Optional[str] = Field("", description="居住城市")
    SignupDate: Optional[str] = Field("", description="註冊日期")
    CustomerSegment: Optional[str] = Field("", description="顧客分群")
    ProductName: Optional[str] = Field("", description="產品名稱")
    Category: Optional[str] = Field("", description="產品分類")
    UnitPrice: Optional[Union[int, float]] = Field(0.0, description="單價")
    Sales: Optional[Union[int, float]] = Field(0.0, description="銷售金額")
    OrderValue: Optional[Union[int, float]] = Field(0.0, description="訂單總價值")
    NewOrderID: Optional[str] = Field(None, description="新訂單識別碼 (選填，若未填寫則自動帶入生成的 doc_id)")
    PhoneNumber: Optional[str] = Field("", description="電話號碼")


class OrderUpdate(BaseModel):
    """
    更新 Firebase 訂單資料結構 (所有欄位皆可選)。
    """
    OrderID: Optional[Union[int, str]] = None
    CustomerID: Optional[Union[int, str]] = None
    OrderDate: Optional[str] = None
    ProductID: Optional[Union[int, str]] = None
    Quantity: Optional[Union[int, float]] = None
    Discount: Optional[Union[int, float]] = None
    PaymentMethod: Optional[str] = None
    Status: Optional[str] = None
    Age: Optional[Union[int, str]] = None
    City: Optional[str] = None
    SignupDate: Optional[str] = None
    CustomerSegment: Optional[str] = None
    ProductName: Optional[str] = None
    Category: Optional[str] = None
    UnitPrice: Optional[Union[int, float]] = None
    Sales: Optional[Union[int, float]] = None
    OrderValue: Optional[Union[int, float]] = None
    NewOrderID: Optional[str] = None
    PhoneNumber: Optional[str] = None


class OrderResponse(OrderCreate):
    """
    訂單單筆回應結構，繼承 OrderCreate 並包含 Firestore 文件 ID。
    """
    id: str = Field(..., description="Firestore 文件 ID")


class OrderListResponse(BaseModel):
    """
    訂單列表回應結構。
    """
    count: int = Field(..., description="取得訂單總筆數")
    orders: List[OrderResponse] = Field(default_factory=list, description="訂單列表")


# ---------------------------------------------------------------------------
# 專屬 Firebase 產品 (Product) Schemas
# ---------------------------------------------------------------------------

class ProductCreate(BaseModel):
    """
    新增 Firebase 產品資料結構 (支援字串與數字型別轉換)。
    """
    ProductID: Union[str, int] = Field(..., description="產品 ID")
    ProductNameZH: Optional[str] = Field("", description="中文品名")
    ProductNameEN: Optional[str] = Field("", description="英文品名")
    Category: Optional[str] = Field("", description="分類")
    CategoryGeneral: Optional[str] = Field("", description="分類")
    Description: Optional[str] = Field("", description="產品詳細說明")
    DescriptionShort: Optional[str] = Field("", description="產品簡短說明 (25字內)")
    CreateDate: Optional[str] = Field("", description="建立日期")
    InStock: Optional[Union[str, int, bool]] = Field("1", description="庫存狀況")
    OriginalPrice: Optional[Union[int, float]] = Field(0.0, description="原價")
    RealPrice: Optional[Union[int, float]] = Field(0.0, description="實際售價")
    ImageUrl: Optional[str] = Field(None, description="產品圖片網址")


class ProductUpdate(BaseModel):
    """
    更新 Firebase 產品資料結構 (所有欄位皆可選)。
    """
    ProductID: Optional[Union[str, int]] = None
    ProductNameZH: Optional[str] = None
    ProductNameEN: Optional[str] = None
    Category: Optional[str] = None
    CategoryGeneral: Optional[str] = None
    Description: Optional[str] = None
    DescriptionShort: Optional[str] = None
    CreateDate: Optional[str] = None
    InStock: Optional[Union[str, int, bool]] = None
    OriginalPrice: Optional[Union[int, float]] = None
    RealPrice: Optional[Union[int, float]] = None
    ImageUrl: Optional[str] = None


class ProductResponse(ProductCreate):
    """
    產品單筆回應結構。
    """
    id: str = Field(..., description="Firestore 文件 ID")


class ProductListResponse(BaseModel):
    """
    產品列表回應結構 (支援分頁)。
    """
    pidx: int = Field(..., description="當前頁碼 (1-based)")
    pno: int = Field(..., description="每頁筆數")
    count: int = Field(..., description="本頁回傳筆數")
    products: List[ProductResponse] = Field(default_factory=list, description="產品列表")


# ---------------------------------------------------------------------------
# 系統與健康檢查 Schemas
# ---------------------------------------------------------------------------

class HealthStatus(BaseModel):
    """
    健康檢查回應結構。
    """
    status: str = Field(..., description="服務狀態 ('healthy' 或 'degraded')")
    app_name: str = Field(..., description="應用程式名稱")
    firebase_connected: bool = Field(..., description="Firebase Firestore 連線狀態")
    details: Optional[str] = Field(None, description="詳細狀態或警告說明")


class ErrorDetail(BaseModel):
    """
    錯誤詳細資訊結構。
    """
    detail: str = Field(..., description="錯誤訊息說明")
