from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app import crud
from app.config import settings
from app.firebase_client import get_db
from app.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    ErrorDetail
)

router = APIRouter(prefix="/Product", tags=["Firebase Product Operations"])

COLLECTION_PRODUCTS = "Product"


import logging

logger = logging.getLogger("corp-backend.products")

def _enrich_product_data(doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    補全 ImageUrl 欄位：若無指定 ImageUrl，自動依據 {PRODUCT_IMAGE_BASE_URL}/{ProductID}_M.jpg 組合網址。
    """
    enriched = dict(data)
    if "ProductID" in enriched and enriched["ProductID"] is not None:
        enriched["ProductID"] = str(enriched["ProductID"])
    else:
        enriched["ProductID"] = doc_id

    if not enriched.get("ImageUrl"):
        product_id = enriched.get("ProductID") or doc_id
        enriched["ImageUrl"] = f"{settings.PRODUCT_IMAGE_BASE_URL}/{product_id}_M.jpg"
    return enriched

@router.get(
    "/count",
    response_model=Dict[str, int],
    summary="取得產品總數",
    responses={500: {"model": ErrorDetail}}
)
def get_product_count():
    try:
        db = get_db()
        results = db.collection(COLLECTION_PRODUCTS).count().get()
        total_count = results[0][0].value
        return {"count": total_count}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取得產品總數失敗: {str(e)}"
        )
    
@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="取得單一產品資料",
    responses={404: {"model": ErrorDetail}, 500: {"model": ErrorDetail}}
)
def get_product(product_id: str):
    """
    依據產品 ID (`product_id` 或 `ProductID`) 查詢單一產品資料。
    - **product_id**: 產品識別碼 (例如: `2001`, `P001`)
    """
    try:
        # 1. 優先嘗試依據 Document ID 取得
        doc = crud.get_document(collection_name=COLLECTION_PRODUCTS, doc_id=product_id)
        if doc:
            enriched_data = _enrich_product_data(doc.id, doc.data)
            return ProductResponse(id=doc.id, **enriched_data)

        # 2. 若未依 Document ID 找到，嘗試依據 ProductID 欄位查詢 (支援字串與數字比較)
        db = get_db()
        docs = (
            db.collection(COLLECTION_PRODUCTS)
            .where("ProductID", "==", product_id)
            .limit(1)
            .stream()
        )

        for d in docs:
            raw_data = d.to_dict() or {}
            sanitized_data = crud._sanitize_firestore_data(raw_data)
            enriched_data = _enrich_product_data(d.id, sanitized_data)
            return ProductResponse(id=d.id, **enriched_data)

        # 3. 嘗試以數字型別查詢 ProductID
        if product_id.isdigit():
            docs_num = (
                db.collection(COLLECTION_PRODUCTS)
                .where("ProductID", "==", int(product_id))
                .limit(1)
                .stream()
            )
            for d in docs_num:
                raw_data = d.to_dict() or {}
                sanitized_data = crud._sanitize_firestore_data(raw_data)
                enriched_data = _enrich_product_data(d.id, sanitized_data)
                return ProductResponse(id=d.id, **enriched_data)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"找不到 ProductID 或 DocID 為 '{product_id}' 的產品"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"讀取產品資料失敗: {str(e)}"
        )


@router.get(
    "",
    response_model=ProductListResponse,
    summary="分頁查詢產品列表",
    responses={500: {"model": ErrorDetail}}
)
@router.get(
    "/",
    response_model=ProductListResponse,
    include_in_schema=False
)
def list_products(
    pidx: int = Query(1, ge=1, description="頁碼 (從 1 開始)"),
    pno: int = Query(10, ge=1, le=500, description="每頁筆數 (1-500)")
):
    """
    分頁取得產品列表。
    - **pidx**: 第幾頁 (預設 1)
    - **pno**: 每頁幾筆 (預設 10)
    """
    try:
        offset = (pidx - 1) * pno
        raw_res = crud.list_documents(
            collection_name=COLLECTION_PRODUCTS,
            limit=pno,
            offset=offset
        )

        products_list = []
        for doc in raw_res.documents:
            try:
                enriched = _enrich_product_data(doc.id, doc.data)
                products_list.append(ProductResponse(id=doc.id, **enriched))
            except Exception as parse_err:
                logger.warning(f"解析 Product Document ID '{doc.id}' 時發生警告: {parse_err}")

        return ProductListResponse(
            pidx=pidx,
            pno=pno,
            count=len(products_list),
            products=products_list
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分頁查詢產品列表失敗: {str(e)}"
        )


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新增產品資料",
    responses={500: {"model": ErrorDetail}}
)
@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False
)
def create_product(payload: ProductCreate):
    """
    新增一筆產品資料至 Firebase Firestore `Product` 集合中。
    """
    try:
        doc_id = payload.ProductID
        product_dict = payload.model_dump()

        res = crud.create_document(
            collection_name=COLLECTION_PRODUCTS,
            data=product_dict,
            doc_id=doc_id
        )

        enriched_data = _enrich_product_data(res.id, res.data)
        return ProductResponse(id=res.id, **enriched_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"新增產品資料失敗: {str(e)}"
        )


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="更新產品資料",
    responses={404: {"model": ErrorDetail}, 500: {"model": ErrorDetail}}
)
def update_product(product_id: str, payload: ProductUpdate):
    """
    部分增量更新既有產品資料。
    """
    try:
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未傳遞任何需要更新的欄位"
            )

        res = crud.update_document(
            collection_name=COLLECTION_PRODUCTS,
            doc_id=product_id,
            data=update_data,
            merge=True
        )

        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到 ID 為 '{product_id}' 的產品"
            )

        enriched_data = _enrich_product_data(res.id, res.data)
        return ProductResponse(id=res.id, **enriched_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新產品資料失敗: {str(e)}"
        )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_200_OK,
    summary="刪除產品資料",
    responses={404: {"model": ErrorDetail}, 500: {"model": ErrorDetail}}
)
def delete_product(product_id: str):
    """
    刪除指定 ID 的產品資料。
    """
    try:
        success = crud.delete_document(collection_name=COLLECTION_PRODUCTS, doc_id=product_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到要刪除的產品 ID '{product_id}'"
            )
        return {
            "status": "success",
            "message": f"已成功刪除產品 ID '{product_id}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除產品資料失敗: {str(e)}"
        )
