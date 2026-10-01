"""
文檔管理核心邏輯：新增/刪除/更新/列出 pgvector（llamaindex 引擎）裡的知識庫文件。

架構：doc_id 完全內部化，只存在這個模組跟資料庫裡，對外一律用「路徑」溝通。
- kb_documents：內容身分，content_hash（SHA256）是唯一依據，判斷「是不是同一份內容」。
- kb_document_labels：路徑/標籤，doc_id 是一般外鍵（可重複）——一份內容可以同時掛在
  多個路徑底下，各自路徑有各自的標籤，互不影響、也不會重複存向量（一對多）。
- pgvector 的向量/chunk 儲存交給 LlamaIndex 的 PGVectorStore 全權處理，這個模組只負責
  「文件身分該怎麼管理」，不碰它的表結構；chunk 的 ref_doc_id 統一用 kb_documents.doc_id
  （流水號字串化），不是路徑本身，所以改路徑（見 upsert_document 的 linked 情境）完全不用
  碰到任何一筆向量。

實作上有兩個容易出錯、已用實際安裝的 llama-index-core==0.11.17 /
llama-index-vector-stores-postgres==0.2.6 原始碼確認過的細節（不是照文件/計畫骨架直接假設）：

1. `TextNode(..., ref_doc_id=source)` 這種建構子寫法會被靜默忽略（TextNode 沒有 ref_doc_id
   欄位，pydantic 不會報錯但值還是 None）。ref_doc_id 要透過
   `node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(node_id=source)` 設定，
   pgvector 的 delete()／VectorStoreIndex.delete_ref_doc() 才能用這個值篩選、刪掉同一份
   文件的所有 chunk（llama_index/vector_stores/postgres/base.py 的 delete() 是用
   `metadata_["doc_id"].astext == ref_doc_id` 做 SQL 篩選，這個 doc_id 就是從
   node.ref_doc_id 存進去的）。
2. `PGVectorStore.from_params(table_name="kb_chunks", ...)` 實際建立的實體資料表名稱是
   `data_kb_chunks`（見 get_data_model() 的 `tablename = "data_%s" % index_name`），
   不是 "kb_chunks" 本身；_count_rows() 這裡要直接對實體表下 SQL，必須對齊這個命名規則。
"""
import hashlib
import re
from typing import Callable, Optional

from llama_index.core import VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import NodeRelationship, RelatedNodeInfo, TextNode
from sqlalchemy import text as sql_text

from app.config import settings
from app.db import get_engine as _get_engine

Parser = Callable[[str, str], list[dict]]


def hash_content(raw_bytes: bytes) -> str:
    """雜湊的是原始上傳檔案 bytes，不是解析／轉檔後的文字——PDF/Word 轉出的純文字沒辦法在
    瀏覽器端重現，client_sha256 只能由前端對原始檔案 bytes 計算，所以身分比對一律以這個為準
    （見 app/main.py 的 _check_client_hash() 呼叫端）。"""
    return hashlib.sha256(raw_bytes).hexdigest()


# 通用 markdown 拆分邏輯：依 H1（文件標題）/H2（小節標題）切段落，每個 H2 小節是一個 chunk。
# 管理頁面上傳的文件一律用這個 parser；產品種子文件因為有固定的規格條列格式，seed_if_empty()
# 改用 product_parser.parse_products 保留逐條拆分的檢索精準度（見該檔案開頭說明）。
_GENERIC_H1_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_GENERIC_H2_SPLIT_PATTERN = re.compile(r"(^##\s+.+$)", re.MULTILINE)


def parse_generic_markdown(raw_text: str, source: str) -> list[dict]:
    """依 H1/H2 切段落。chunk 內部 category 欄位固定給空字串——這是展示用的舊欄位，
    新流程不再用「分類」這個概念，跟文件身分的 tags 是不同語意，不要混用。"""
    h1_match = _GENERIC_H1_PATTERN.search(raw_text)
    doc_title = h1_match.group(1).strip() if h1_match else source

    parts = _GENERIC_H2_SPLIT_PATTERN.split(raw_text)
    chunks = []
    for i in range(1, len(parts), 2):
        section_title = parts[i].lstrip("#").strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if not body:
            continue
        chunks.append({
            "text": f"{doc_title}－{section_title}：\n{body}",
            "source": source,
            "topic": f"{doc_title}：{section_title}",
            "category": "",
            "product_id": "",
        })
    return chunks


# PDF／Word 轉出的純文字沒有 Markdown 標題結構可循（PDF 更是完全沒有語意標記可言），硬套
# parse_generic_markdown 的 H1/H2 規則在沒有 "##" 段落標題時會直接產出 0 個 chunk。改用
# LlamaIndex 內建的 SentenceSplitter（本專案已經依賴 llama-index-core，見檔案頂端說明）：
# 依句子邊界、以 token 數（而非字元數）切段，相鄰 chunk 間保留 overlap，避免答案剛好跨在
# 切點上時檢索不到完整脈絡。chunk_size/chunk_overlap 選比預設值（1024/200）小的 512/50，
# 對應 RAG 檢索偏好較小、較精準的 chunk。
_PLAIN_TEXT_SPLITTER = SentenceSplitter(chunk_size=512, chunk_overlap=50)


def parse_plain_text(raw_text: str, source: str) -> list[dict]:
    """給沒有 Markdown 結構的純文字使用（PDF／Word 轉出的內容），見上方 _PLAIN_TEXT_SPLITTER 說明。"""
    return [
        {
            "text": text,
            "source": source,
            "topic": f"{source}：第 {i + 1} 段",
            "category": "",
            "product_id": "",
        }
        for i, text in enumerate(_PLAIN_TEXT_SPLITTER.split_text(raw_text))
    ]


def _build_nodes(
    chatbot_id: str, ref_doc_id: str, display_source: str, chunks: list[dict]
) -> list[TextNode]:
    """
    把解析出來的 chunk 包成帶 ref_doc_id 的 TextNode。ref_doc_id 是 kb_documents.doc_id
    （流水號字串化，管理/刪除用的穩定身分），display_source 是給聊天檢索顯示用的路徑
    （建立當下觸發 embed 的那個路徑，多個路徑共用同一份內容時不會動態更新，只是顯示用途）。

    chatbot_id 存進 metadata：llamaindex_engine.retrieve() 用 MetadataFilters 依這個欄位
    過濾，是 RAG chatbot 隔離真正生效的地方（documents_store 這邊的 chatbot_id 只管理
    kb_documents/kb_document_labels 這兩張「身分」表，不代表向量檢索也會自動隔離）。
    """
    nodes = []
    for i, c in enumerate(chunks):
        node = TextNode(
            text=c["text"],
            id_=f"{ref_doc_id}-{i}",
            metadata={
                "chatbot_id": chatbot_id,
                "source": display_source,
                "topic": c["topic"],
                "category": c["category"],
                "product_id": c["product_id"],
            },
        )
        # ref_doc_id 設定方式：TextNode 建構子的 ref_doc_id 參數會被靜默忽略
        # （llama-index-core==0.11.17 沒有這個欄位），必須透過 relationships 設定，
        # 否則 delete_ref_doc() 之後篩不到任何 row。
        node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(node_id=ref_doc_id)
        nodes.append(node)
    return nodes


_schema_ready = False


def _ensure_schema() -> None:
    """
    確保 kb_documents／kb_document_labels 這兩張身分/標籤表存在。冪等、每個 process
    只會真的執行一次 DDL（用模組層級旗標快取），之後呼叫都是無成本的早退。

    chatbot_id 隔離（Phase 1）：兩張表都加上 chatbot_id，唯一性從「全域唯一」改成
    「同一 chatbot_id 底下唯一」（UNIQUE(chatbot_id, content_hash) / UNIQUE(chatbot_id, path)），
    讓不同公司可以各自有同路徑、同內容的文件而互不干擾。舊的（無公司歸屬）RAG 資料直接砍掉
    重建，不用遷移（見實作計畫），所以這裡用 CREATE TABLE IF NOT EXISTS 搭配新 schema，
    不寫 ALTER TABLE 相容舊表。
    """
    global _schema_ready
    if _schema_ready:
        return
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(sql_text(
            """
            CREATE TABLE IF NOT EXISTS kb_documents (
                doc_id          BIGSERIAL PRIMARY KEY,
                chatbot_id      UUID NOT NULL,
                content_hash    CHAR(64) NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                chunk_count     INTEGER NOT NULL DEFAULT 0,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (chatbot_id, content_hash)
            )
            """
        ))
        conn.execute(sql_text(
            """
            CREATE TABLE IF NOT EXISTS kb_document_labels (
                id         BIGSERIAL PRIMARY KEY,
                doc_id     BIGINT NOT NULL REFERENCES kb_documents(doc_id) ON DELETE CASCADE,
                chatbot_id UUID NOT NULL,
                path       TEXT NOT NULL,
                tags       TEXT[] NOT NULL DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (chatbot_id, path)
            )
            """
        ))
        conn.execute(sql_text(
            "CREATE INDEX IF NOT EXISTS kb_document_labels_doc_id_idx ON kb_document_labels (doc_id)"
        ))
        conn.execute(sql_text(
            "CREATE INDEX IF NOT EXISTS kb_documents_chatbot_id_idx ON kb_documents (chatbot_id)"
        ))
        conn.execute(sql_text(
            "CREATE INDEX IF NOT EXISTS kb_document_labels_chatbot_id_idx ON kb_document_labels (chatbot_id)"
        ))
        # 舊資料庫的 labels 表沒有 updated_at；以既有建立時間回填後再設為必填，
        # 讓 migration 與新 schema 都能安全使用同一個排序欄位。
        conn.execute(sql_text(
            "ALTER TABLE kb_document_labels ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ"
        ))
        conn.execute(sql_text(
            "UPDATE kb_document_labels SET updated_at = created_at WHERE updated_at IS NULL"
        ))
        conn.execute(sql_text(
            "ALTER TABLE kb_document_labels ALTER COLUMN updated_at SET DEFAULT now()"
        ))
        conn.execute(sql_text(
            "ALTER TABLE kb_document_labels ALTER COLUMN updated_at SET NOT NULL"
        ))
        conn.execute(sql_text(
            "CREATE INDEX IF NOT EXISTS kb_document_labels_chatbot_updated_at_idx "
            "ON kb_document_labels (chatbot_id, updated_at DESC)"
        ))
    _schema_ready = True


def get_label(chatbot_id: str, path: str) -> Optional[dict]:
    """查這個公司底下、這個路徑目前指向哪份內容（doc_id/tags/content_hash/chunk_count），查不到回 None。"""
    _ensure_schema()
    sql = sql_text(
        """
        SELECT l.doc_id, l.tags, d.content_hash, d.chunk_count
        FROM kb_document_labels l JOIN kb_documents d ON d.doc_id = l.doc_id
        WHERE l.chatbot_id = :chatbot_id AND l.path = :path
        """
    )
    engine = _get_engine()
    with engine.connect() as conn:
        row = conn.execute(sql, {"chatbot_id": chatbot_id, "path": path}).fetchone()
    if row is None:
        return None
    return {
        "doc_id": row.doc_id,
        "tags": list(row.tags) if row.tags is not None else [],
        "content_hash": row.content_hash,
        "chunk_count": row.chunk_count,
    }


def find_document_by_hash(chatbot_id: str, content_hash: str) -> Optional[dict]:
    """查這個公司底下、這個內容雜湊有沒有既有的 kb_documents 紀錄（不管掛在哪個路徑底下），查不到回 None。"""
    _ensure_schema()
    sql = sql_text(
        "SELECT doc_id, chunk_count FROM kb_documents WHERE chatbot_id = :chatbot_id AND content_hash = :h"
    )
    engine = _get_engine()
    with engine.connect() as conn:
        row = conn.execute(sql, {"chatbot_id": chatbot_id, "h": content_hash}).fetchone()
    if row is None:
        return None
    return {"doc_id": row.doc_id, "chunk_count": row.chunk_count}


def _relabel_and_collect_orphan(
    chatbot_id: str, path: str, doc_id: int, tags: list[str], old_doc_id: Optional[int]
) -> Optional[int]:
    """
    把路徑指向 doc_id（不存在就新增、存在就整筆覆蓋），跟「舊 doc_id 是否變成孤兒」這兩件事
    都是純 SQL、彼此之間不需要插入任何外部呼叫，包在同一個 transaction 裡一次做完。

    回傳「真的沒人指了、需要清掉向量的 doc_id」；沒有孤兒（or old_doc_id 就是 None／沒變）
    回傳 None。向量刪除本身是外部呼叫（LlamaIndex 自己的連線，不在這個 transaction 裡），
    沒辦法一起原子化，所以拆成兩段：這裡只負責在 SQL 層面「判斷」，真的要刪向量交給呼叫端
    另外呼叫 _finalize_orphan_deletion()。
    """
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(
            sql_text(
                """
                INSERT INTO kb_document_labels (doc_id, chatbot_id, path, tags)
                VALUES (:doc_id, :chatbot_id, :path, :tags)
                ON CONFLICT (chatbot_id, path) DO UPDATE
                SET doc_id = EXCLUDED.doc_id, tags = EXCLUDED.tags, updated_at = now()
                """
            ),
            {"doc_id": doc_id, "chatbot_id": chatbot_id, "path": path, "tags": tags},
        )
        if old_doc_id is None or old_doc_id == doc_id:
            return None
        remaining = conn.execute(
            sql_text("SELECT count(*) FROM kb_document_labels WHERE doc_id = :id"), {"id": old_doc_id}
        ).scalar_one()
        return old_doc_id if remaining == 0 else None


def _finalize_orphan_deletion(doc_id: int, index: VectorStoreIndex) -> None:
    """
    真的刪掉一個已經沒人指的 doc_id：先刪向量（外部呼叫），成功後才刪 kb_documents 那筆。
    順序很重要——如果反過來先刪 kb_documents 紀錄，向量刪除又失敗，會留下檢索得到、
    但任何路徑/標籤都查不到來源的「幽靈向量」；現在這個順序最壞情況只是留下一筆沒有
    對應向量、也不會被任何 API 顯示出來的孤兒 kb_documents 紀錄，之後可以再補一支背景
    清理工具處理，不影響現有功能正確性。
    """
    index.delete_ref_doc(str(doc_id), delete_from_docstore=True)
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(sql_text("DELETE FROM kb_documents WHERE doc_id = :id"), {"id": doc_id})


def _create_document_with_embedding(
    chatbot_id: str,
    path: str,
    raw_text: str,
    content_hash: str,
    file_size_bytes: int,
    index: VectorStoreIndex,
    parser: Parser = parse_generic_markdown,
) -> dict:
    """真的解析＋embed 一份新內容：新增 kb_documents 一筆，插入對應的向量，回傳新 doc_id 與 chunk 數。

    content_hash／file_size_bytes 直接信任呼叫端（app/main.py 的 PUT /api/admin/documents/{path}）
    已經核對過的原始檔案 client_sha256／bytes 長度，不在這裡從 raw_text 重算——raw_text 對 PDF/Word
    來說是轉檔後的擷取文字，跟原始檔案 bytes 是兩回事，「內容身分」必須以使用者實際上傳的檔案為準。
    """
    engine = _get_engine()
    with engine.begin() as conn:
        doc_id = conn.execute(
            sql_text(
                """
                INSERT INTO kb_documents (chatbot_id, content_hash, file_size_bytes, chunk_count)
                VALUES (:chatbot_id, :h, :s, 0) RETURNING doc_id
                """
            ),
            {"chatbot_id": chatbot_id, "h": content_hash, "s": file_size_bytes},
        ).scalar_one()

    chunks = parser(raw_text, path)
    nodes = _build_nodes(chatbot_id, str(doc_id), path, chunks)
    if nodes:
        index.insert_nodes(nodes)

    with engine.begin() as conn:
        conn.execute(
            sql_text("UPDATE kb_documents SET chunk_count = :c WHERE doc_id = :id"),
            {"c": len(nodes), "id": doc_id},
        )
    return {"doc_id": doc_id, "chunk_count": len(nodes)}


def upsert_document(
    chatbot_id: str,
    path: str,
    tags: list[str],
    client_sha256: str,
    raw_text: Optional[str],
    index: VectorStoreIndex,
    parser: Parser = parse_generic_markdown,
    file_size_bytes: Optional[int] = None,
) -> dict:
    """
    知識庫文件管理的唯一寫入入口：不需要呼叫端提供任何 doc_id，純粹依「公司 + 路徑」跟
    「公司 + 內容雜湊」交叉查詢決定要做什麼事。回傳 {"status", "chunk_count", "content_changed"}。

    所有判斷都限定在同一個 chatbot_id 範圍內——不同公司即使路徑、內容完全一樣，也各自視為
    獨立的 new，不會互相命中對方的雜湊或路徑（多租戶隔離）。

    - 這個路徑本來就指向這個雜湊：標籤沒變 -> unchanged；標籤變了 -> tags_only_changed（不重新 embed）。
    - 這個雜湊命中「別的」既有內容（不管這個路徑本來有沒有紀錄）：linked，只改標籤紀錄指向該內容，
      不重新 embed；如果這個路徑原本指向別的 doc_id，且那個 doc_id 之後沒有任何路徑指著了，順手清掉。
    - 兩者都沒中：真的需要 raw_text 才能新增/更新內容（呼叫端要保證這種情況一定有帶檔案）。
    """
    _ensure_schema()
    label = get_label(chatbot_id, path)

    if label is not None and label["content_hash"] == client_sha256:
        if set(label["tags"]) == set(tags):
            return {"status": "unchanged", "chunk_count": label["chunk_count"], "content_changed": False}
        _relabel_and_collect_orphan(chatbot_id, path, label["doc_id"], tags, old_doc_id=None)
        return {"status": "tags_only_changed", "chunk_count": label["chunk_count"], "content_changed": False}

    old_doc_id = label["doc_id"] if label is not None else None

    matched = find_document_by_hash(chatbot_id, client_sha256)
    if matched is not None:
        orphan = _relabel_and_collect_orphan(chatbot_id, path, matched["doc_id"], tags, old_doc_id)
        if orphan is not None:
            _finalize_orphan_deletion(orphan, index)
        return {"status": "linked", "chunk_count": matched["chunk_count"], "content_changed": False}

    if raw_text is None:
        raise ValueError("需要上傳檔案內容才能新增或更新這份文件。")

    created = _create_document_with_embedding(
        chatbot_id, path, raw_text, client_sha256, file_size_bytes, index, parser=parser
    )
    orphan = _relabel_and_collect_orphan(chatbot_id, path, created["doc_id"], tags, old_doc_id)
    if orphan is not None:
        _finalize_orphan_deletion(orphan, index)
    status = "content_changed" if label is not None else "new"
    return {"status": status, "chunk_count": created["chunk_count"], "content_changed": True}


def list_documents(chatbot_id: str) -> list[dict]:
    """列出這個公司底下所有路徑（一份內容掛兩個路徑就是兩列，各自標籤）。"""
    _ensure_schema()
    sql = sql_text(
        """
        SELECT l.path, l.tags, d.chunk_count, d.file_size_bytes, l.updated_at, d.content_hash
        FROM kb_document_labels l JOIN kb_documents d ON d.doc_id = l.doc_id
        WHERE l.chatbot_id = :chatbot_id
        ORDER BY l.updated_at DESC, l.path ASC
        """
    )
    engine = _get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sql, {"chatbot_id": chatbot_id}).fetchall()
    return [
        {
            "path": row.path,
            "tags": list(row.tags) if row.tags is not None else [],
            "chunk_count": row.chunk_count,
            "file_size_bytes": row.file_size_bytes,
            "uploaded_at": row.updated_at.isoformat() if row.updated_at is not None else None,
            "content_hash": row.content_hash,
        }
        for row in rows
    ]


def list_paths_by_prefix(chatbot_id: str, prefix: str) -> list[str]:
    """列出這個公司底下以 prefix 開頭的所有路徑，用於「資料夾全量覆蓋上傳」比對這次沒包含到的舊路徑。"""
    _ensure_schema()
    sql = sql_text(
        "SELECT path FROM kb_document_labels WHERE chatbot_id = :chatbot_id AND path LIKE :pattern"
    )
    engine = _get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sql, {"chatbot_id": chatbot_id, "pattern": prefix + "%"}).fetchall()
    return [row.path for row in rows]


def delete_document_by_path(chatbot_id: str, path: str, index: VectorStoreIndex) -> bool:
    """刪除這個公司底下這個路徑的標籤紀錄；該內容沒有其他路徑指著了才真的刪掉向量與內容紀錄。"""
    _ensure_schema()
    engine = _get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            sql_text(
                "DELETE FROM kb_document_labels WHERE chatbot_id = :chatbot_id AND path = :path "
                "RETURNING doc_id"
            ),
            {"chatbot_id": chatbot_id, "path": path},
        ).fetchone()
        if row is None:
            return False
        remaining = conn.execute(
            sql_text("SELECT count(*) FROM kb_document_labels WHERE doc_id = :id"), {"id": row.doc_id}
        ).scalar_one()
    if remaining == 0:
        _finalize_orphan_deletion(row.doc_id, index)
    return True


def purge_chatbot(chatbot_id: str, index: VectorStoreIndex) -> None:
    """
    硬刪除一家公司的所有 RAG 資料：kb_document_labels/kb_documents 的列，以及 pgvector
    物理表裡屬於這家公司的向量 chunk。供公司刪除（DELETE /api/admin/chatbots/{id}）呼叫。

    向量部分直接對 PGVectorStore 的實體表（data_<RAG_PG_TABLE>，見檔案頂端說明）下 SQL，
    用 metadata_ JSONB 欄位的 chatbot_id 篩選——不透過 index.delete_ref_doc() 逐筆刪
    （那個方法要先知道每個 doc_id，公司刪除是整批清空，直接對表下 SQL 更直接也更不容易漏刪）。
    """
    _ensure_schema()
    engine = _get_engine()
    table = _table_full_name()
    try:
        # 向量物理表是 lazy 建立的（第一次 insert_nodes 才會觸發建表，見 seed_if_empty()
        # 的說明），全新資料庫可能還沒有任何文件、表根本不存在，這種情況視同沒有向量要清，
        # 不用另外擋成錯誤，跟 _count_rows() 的處理方式一致。
        with engine.begin() as conn:
            conn.execute(
                sql_text(f"DELETE FROM {table} WHERE metadata_->>'chatbot_id' = :chatbot_id"),
                {"chatbot_id": chatbot_id},
            )
    except Exception:
        pass
    with engine.begin() as conn:
        conn.execute(
            sql_text("DELETE FROM kb_document_labels WHERE chatbot_id = :chatbot_id"),
            {"chatbot_id": chatbot_id},
        )
        conn.execute(
            sql_text("DELETE FROM kb_documents WHERE chatbot_id = :chatbot_id"),
            {"chatbot_id": chatbot_id},
        )


def _table_full_name() -> str:
    # 見檔案頂端說明：實體資料表名稱是 "data_<table_name>"，schema_name 固定用 public
    # （PGVectorStore.from_params 預設 schema_name="public"，本專案沒有另外指定）。
    return f"public.data_{settings.RAG_PG_TABLE.lower()}"


def _count_rows() -> int:
    table = _table_full_name()
    engine = _get_engine()
    with engine.connect() as conn:
        return conn.execute(sql_text(f"SELECT count(*) FROM {table}")).scalar_one()


def seed_if_empty(index: VectorStoreIndex) -> None:
    """
    Phase 1 多租戶隔離後的已知限制：這個函式原本會在 pgvector table 全空時（例如全新資料庫）
    自動把 app/data/*.md 的示範知識庫內容灌進去；但現在 kb_documents.chatbot_id 是必填
    （見 _ensure_schema() 的說明），啟動階段並不存在任何「預設公司」可以歸屬這批示範資料
    （公司要透過 POST /api/admin/chatbots 由平台帳號手動建立），繼續硬塞一個假的 chatbot_id
    會混淆真正的租戶資料，所以 Phase 1 先把自動灌入示範資料整個停用，改成純粹的 no-op。
    後續如果要恢復「新公司預先帶入示範知識庫」的體驗，應該在建立公司當下明確呼叫、帶入
    該公司的 chatbot_id，而不是在啟動階段猜一個全域對象。
    """
    return
