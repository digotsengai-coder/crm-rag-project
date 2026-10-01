from datetime import datetime, date
import logging
from typing import Any, Dict, List, Optional

from app.firebase_client import get_db
from app.schemas import DocumentResponse, DocumentListResponse

logger = logging.getLogger("corp-backend.crud")


def _sanitize_firestore_data(data: Any) -> Any:
    """
    遞迴處理 Firestore 回傳的資料，將 datetime / Timestamp 物件轉換為 ISO 格式字串，
    確保 JSON 序列化正常。
    """
    if isinstance(data, dict):
        return {k: _sanitize_firestore_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_sanitize_firestore_data(item) for item in data]
    elif isinstance(data, (datetime, date)):
        return data.isoformat()
    return data


def create_document(collection_name: str, data: Dict[str, Any], doc_id: Optional[str] = None) -> DocumentResponse:
    """
    在指定 Collection 建立新文件。
    :param collection_name: Firestore Collection 名稱
    :param data: 文件 JSON 資料
    :param doc_id: 可選的自訂 Document ID
    :return: DocumentResponse
    """
    db = get_db()
    collection_ref = db.collection(collection_name)

    if doc_id:
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(data)
    else:
        update_time, doc_ref = collection_ref.add(data)
        doc_id = doc_ref.id

    sanitized_data = _sanitize_firestore_data(data)
    logger.info(f"已在 Collection '{collection_name}' 建立文件 ID '{doc_id}'")
    return DocumentResponse(
        id=doc_id,
        collection=collection_name,
        data=sanitized_data
    )


def get_document(collection_name: str, doc_id: str) -> Optional[DocumentResponse]:
    """
    取得指定 Collection 與 Document ID 的單一文件。
    :param collection_name: Firestore Collection 名稱
    :param doc_id: Document ID
    :return: DocumentResponse 或 None (若不存在)
    """
    db = get_db()
    doc_ref = db.collection(collection_name).document(doc_id)
    doc_snapshot = doc_ref.get()

    if not doc_snapshot.exists:
        return None

    raw_data = doc_snapshot.to_dict() or {}
    sanitized_data = _sanitize_firestore_data(raw_data)

    return DocumentResponse(
        id=doc_snapshot.id,
        collection=collection_name,
        data=sanitized_data
    )


def list_documents(
    collection_name: str,
    limit: int = 100,
    offset: int = 0,
    order_by: Optional[str] = None
) -> DocumentListResponse:
    """
    查詢指定 Collection 中的文件清單。
    :param collection_name: Firestore Collection 名稱
    :param limit: 回傳上限數量 (預設 100)
    :param offset: 跳過筆數 (預設 0)
    :param order_by: 排序欄位名稱 (選填)
    :return: DocumentListResponse
    """
    db = get_db()
    query = db.collection(collection_name)

    if order_by:
        query = query.order_by(order_by)

    if offset > 0:
        query = query.offset(offset)

    query = query.limit(limit)
    docs = query.stream()

    document_list: List[DocumentResponse] = []
    for doc in docs:
        raw_data = doc.to_dict() or {}
        sanitized_data = _sanitize_firestore_data(raw_data)
        document_list.append(
            DocumentResponse(
                id=doc.id,
                collection=collection_name,
                data=sanitized_data
            )
        )

    return DocumentListResponse(
        collection=collection_name,
        count=len(document_list),
        documents=document_list
    )


def update_document(
    collection_name: str,
    doc_id: str,
    data: Dict[str, Any],
    merge: bool = True
) -> Optional[DocumentResponse]:
    """
    更新指定 Collection 與 Document ID 的文件內容。
    :param collection_name: Firestore Collection 名稱
    :param doc_id: Document ID
    :param data: 要更新的欄位資料
    :param merge: True 為增量更新 (Merge)，False 為完全覆蓋
    :return: DocumentResponse 或 None (若不存在)
    """
    db = get_db()
    doc_ref = db.collection(collection_name).document(doc_id)

    if not doc_ref.get().exists:
        return None

    if merge:
        doc_ref.set(data, merge=True)
    else:
        doc_ref.set(data)

    updated_snapshot = doc_ref.get()
    raw_data = updated_snapshot.to_dict() or {}
    sanitized_data = _sanitize_firestore_data(raw_data)

    logger.info(f"已更新 Collection '{collection_name}' 文件 ID '{doc_id}' (merge={merge})")
    return DocumentResponse(
        id=doc_id,
        collection=collection_name,
        data=sanitized_data
    )


def delete_document(collection_name: str, doc_id: str) -> bool:
    """
    刪除指定 Collection 中的文件。
    :param collection_name: Firestore Collection 名稱
    :param doc_id: Document ID
    :return: bool 是否成功刪除 (存在並刪除)
    """
    db = get_db()
    doc_ref = db.collection(collection_name).document(doc_id)
    doc_snapshot = doc_ref.get()

    if not doc_snapshot.exists:
        return False

    doc_ref.delete()
    logger.info(f"已刪除 Collection '{collection_name}' 文件 ID '{doc_id}'")
    return True
