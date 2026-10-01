import random
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app import crud
from app.schemas import (
    OrderCreate,
    OrderUpdate,
    OrderResponse,
    OrderListResponse,
    ErrorDetail
)

router = APIRouter(prefix="/Order", tags=["Firebase Orders Operations"])

COLLECTION_ORDERS = "Order"


import logging

logger = logging.getLogger("corp-backend.orders")


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新增 Firebase 訂單資料",
    responses={500: {"model": ErrorDetail}}
)
@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False
)
def create_order(payload: OrderCreate):
    """
    寫入一筆新的訂單至 Firebase Firestore `Order` 集合中。
    - **doc_id** 生成規則：10 位 Unix Timestamp 秒數 + 3 位隨機數字 (共 13 位數字)。
    """
    try:
        # 生成 10 位數 Unix 時間戳記與 3 位數隨機號碼 (例如: 1757409477832)
        timestamp_part = int(time.time())
        random_part = random.randint(100, 999)
        doc_id = f"ORD-{timestamp_part}{random_part}"

        order_dict = payload.model_dump()
        if not order_dict.get("NewOrderID"):
            order_dict["NewOrderID"] = doc_id

        res = crud.create_document(
            collection_name=COLLECTION_ORDERS,
            data=order_dict,
            doc_id=doc_id
        )

        return OrderResponse(id=res.id, **res.data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"寫入 Firebase 訂單失敗: {str(e)}"
        )


@router.get(
    "",
    response_model=OrderListResponse,
    summary="取得 Firebase 訂單列表",
    responses={500: {"model": ErrorDetail}}
)
@router.get(
    "/",
    response_model=OrderListResponse,
    include_in_schema=False
)
def list_orders(
    limit: int = Query(100, ge=1, le=1000, description="查詢筆數限制 (1-1000)"),
    order_by: Optional[str] = Query(None, description="排序欄位 (例如: OrderDate 或 OrderID)")
):
    """
    查詢 Firestore `Order` 集合中的訂單列表。
    """
    try:
        raw_res = crud.list_documents(
            collection_name=COLLECTION_ORDERS,
            limit=limit,
            order_by=order_by
        )

        orders_list = []
        for doc in raw_res.documents:
            try:
                data = dict(doc.data)
                if not data.get("NewOrderID"):
                    data["NewOrderID"] = doc.id
                orders_list.append(OrderResponse(id=doc.id, **data))
            except Exception as parse_err:
                logger.warning(f"解析 Order Document ID '{doc.id}' 時發生警告: {parse_err}")

        return OrderListResponse(
            count=len(orders_list),
            orders=orders_list
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢 Firebase 訂單列表失敗: {str(e)}"
        )


@router.get(
    "/search",
    response_model=OrderResponse,
    summary="根據訂單編號與電話查詢訂單，缺一不可",
    responses={404: {"model": ErrorDetail}, 500: {"model": ErrorDetail}}
)
def get_order_by_orderid_and_phone(
    oid: str = Query(description="訂單編號"),
    pno: str = Query(description="電話號碼")
):
    try:
        doc = crud.get_document(collection_name=COLLECTION_ORDERS, doc_id=oid)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"查無訂單"
            )
        if doc.data.get("PhoneNumber") != pno:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"查無訂單"
            )
        return OrderResponse(id=doc.id, **doc.data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"讀取 Firebase 訂單失敗: {str(e)}"
        )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="查詢單筆 Firebase 訂單",
    responses={404: {"model": ErrorDetail}, 500: {"model": ErrorDetail}}
)
def get_order(order_id: str):
    """
    依據 ID (NewOrderID 或 OrderID) 取得單筆 Firebase 訂單。
    """
    try:
        doc = crud.get_document(collection_name=COLLECTION_ORDERS, doc_id=order_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到 ID 為 '{order_id}' 的 Firebase 訂單"
            )
        return OrderResponse(id=doc.id, **doc.data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"讀取 Firebase 訂單失敗: {str(e)}"
        )


@router.patch(
    "/{order_id}",
    response_model=OrderResponse,
    summary="更新單筆 Firebase 訂單",
    responses={404: {"model": ErrorDetail}, 500: {"model": ErrorDetail}}
)
def update_order(order_id: str, payload: OrderUpdate):
    """
    更新既有 Firebase 訂單的部分欄位。
    """
    try:
        # 過濾未傳遞 (None) 的欄位
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未傳遞任何需要更新的欄位"
            )

        res = crud.update_document(
            collection_name=COLLECTION_ORDERS,
            doc_id=order_id,
            data=update_data,
            merge=True
        )

        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到 ID 為 '{order_id}' 的 Firebase 訂單"
            )

        return OrderResponse(id=res.id, **res.data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新 Firebase 訂單失敗: {str(e)}"
        )


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_200_OK,
    summary="刪除 Firebase 訂單",
    responses={404: {"model": ErrorDetail}, 500: {"model": ErrorDetail}}
)
def delete_order(order_id: str):
    """
    刪除指定 ID 的 Firebase 訂單。
    """
    try:
        success = crud.delete_document(collection_name=COLLECTION_ORDERS, doc_id=order_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到要刪除的 Firebase 訂單 ID '{order_id}'"
            )
        return {
            "status": "success",
            "message": f"已成功刪除 Firebase 訂單 ID '{order_id}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除 Firebase 訂單失敗: {str(e)}"
        )
