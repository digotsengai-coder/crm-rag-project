from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app import crud
from app.schemas import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
    ErrorDetail
)

router = APIRouter(prefix="/collections", tags=["Firestore CRUD Operations"])


@router.post(
    "/{collection_name}/docs",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新增 Firestore 文件",
    responses={500: {"model": ErrorDetail}}
)
def create_doc(collection_name: str, payload: DocumentCreate):
    """
    在指定的 Collection 中建立新文件。
    - **collection_name**: 集合名稱 (例如 `companies`, `orders`, `users`)
    - **doc_id**: 自訂文件 ID (選填，未傳遞則自動生成)
    - **data**: 文件內容 (JSON 鍵值對)
    """
    try:
        res = crud.create_document(
            collection_name=collection_name,
            data=payload.data,
            doc_id=payload.doc_id
        )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"建立 Firestore 文件失敗: {str(e)}"
        )


@router.get(
    "/{collection_name}/docs",
    response_model=DocumentListResponse,
    summary="查詢 Collection 中的文件列表",
    responses={500: {"model": ErrorDetail}}
)
def list_docs(
    collection_name: str,
    limit: int = Query(100, ge=1, le=1000, description="查詢數量上限 (1-1000)"),
    order_by: Optional[str] = Query(None, description="排序欄位名稱")
):
    """
    列出指定 Collection 的所有文件。
    - **collection_name**: 集合名稱
    - **limit**: 筆數限制
    - **order_by**: 依據指定欄位排序
    """
    try:
        res = crud.list_documents(
            collection_name=collection_name,
            limit=limit,
            order_by=order_by
        )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢 Firestore 文件列表失敗: {str(e)}"
        )


@router.get(
    "/{collection_name}/docs/{doc_id}",
    response_model=DocumentResponse,
    summary="取得單一 Firestore 文件",
    responses={404: {"model": ErrorDetail}, 500: {"model": ErrorDetail}}
)
def get_doc(collection_name: str, doc_id: str):
    """
    依據 ID 取得指定 Collection 的單一文件。
    - **collection_name**: 集合名稱
    - **doc_id**: 文件 ID
    """
    try:
        res = crud.get_document(collection_name=collection_name, doc_id=doc_id)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"在 Collection '{collection_name}' 中找不到文件 ID '{doc_id}'"
            )
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"讀取 Firestore 文件失敗: {str(e)}"
        )


@router.put(
    "/{collection_name}/docs/{doc_id}",
    response_model=DocumentResponse,
    summary="完全覆蓋更新 Firestore 文件",
    responses={404: {"model": ErrorDetail}, 500: {"model": ErrorDetail}}
)
def replace_doc(collection_name: str, doc_id: str, payload: Dict[str, Any]):
    """
    完全覆蓋指定 ID 的文件內容 (Overwrite)。
    - **collection_name**: 集合名稱
    - **doc_id**: 文件 ID
    """
    try:
        res = crud.update_document(
            collection_name=collection_name,
            doc_id=doc_id,
            data=payload,
            merge=False
        )
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"在 Collection '{collection_name}' 中找不到文件 ID '{doc_id}'"
            )
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"覆蓋 Firestore 文件失敗: {str(e)}"
        )


@router.patch(
    "/{collection_name}/docs/{doc_id}",
    response_model=DocumentResponse,
    summary="增量更新 Firestore 文件 (Merge)",
    responses={404: {"model": ErrorDetail}, 500: {"model": ErrorDetail}}
)
def update_doc(collection_name: str, doc_id: str, payload: DocumentUpdate):
    """
    部分增量更新指定 ID 的文件內容 (Merge)。
    - **collection_name**: 集合名稱
    - **doc_id**: 文件 ID
    - **data**: 要更新的部分欄位
    """
    try:
        res = crud.update_document(
            collection_name=collection_name,
            doc_id=doc_id,
            data=payload.data,
            merge=payload.merge
        )
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"在 Collection '{collection_name}' 中找不到文件 ID '{doc_id}'"
            )
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"增量更新 Firestore 文件失敗: {str(e)}"
        )


@router.delete(
    "/{collection_name}/docs/{doc_id}",
    status_code=status.HTTP_200_OK,
    summary="刪除 Firestore 文件",
    responses={404: {"model": ErrorDetail}, 500: {"model": ErrorDetail}}
)
def delete_doc(collection_name: str, doc_id: str):
    """
    刪除指定 ID 的 Firestore 文件。
    - **collection_name**: 集合名稱
    - **doc_id**: 文件 ID
    """
    try:
        success = crud.delete_document(collection_name=collection_name, doc_id=doc_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"在 Collection '{collection_name}' 中找不到要刪除的文件 ID '{doc_id}'"
            )
        return {
            "status": "success",
            "message": f"已成功刪除 Collection '{collection_name}' 中的文件 ID '{doc_id}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除 Firestore 文件失敗: {str(e)}"
        )
