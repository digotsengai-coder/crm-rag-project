"""
測試 /api/admin/documents 系列端點（新增/查詢/更新/刪除/標籤/預檢知識庫文件）。

這幾支 API 依賴 llamaindex 引擎（pgvector 儲存），需要本機真的起一個
pgvector 服務（見 backend/README.md 的 docker run 指令）並在 .env 設定對應的
RAG_PG_* 連線資訊，跑這份測試前請確認 pgvector 已啟動、能連得上，否則會直接失敗
（不像訂單查詢有 fallback 機制可以在沒有外部服務時仍然通過）。

架構：doc_id 完全內部化（kb_documents.doc_id 流水號），對外 API 一律用「路徑」溝通，
「是不是同一份文件」純粹看 SHA256（kb_documents.content_hash UNIQUE）。一份內容可以
同時掛在多個路徑底下（一對多），各自路徑各自標籤，互不影響。

新增/更新是上傳 .md 檔（multipart），不是 JSON body，測試用 httpx 的 files= 參數模擬；
純改標籤/掛到既有內容（linked）不需要帶 file。用獨立、不會跟既有知識庫文件撞名的路徑
（PYTEST_ 開頭）測試完整生命週期，並在測試結束後主動刪除，避免污染共用的 pgvector table。
"""
import hashlib

import pytest
from fastapi.testclient import TestClient

from app.main import app, _chatbot_request_log, _request_log

TEST_PATH = "pytest_test_doc.md"


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _md_file(content: str, filename: str = TEST_PATH):
    return {"file": (filename, content.encode("utf-8"), "text/markdown")}


def _minimal_pdf_bytes(text: str) -> bytes:
    """手刻一份最小可用的單頁 PDF（Helvetica 純文字），足夠讓 pypdf 抽出文字，
    不需要額外套件（例如 reportlab）就能產生測試檔案。"""
    stream = f"BT /F1 18 Tf 10 100 Td ({text}) Tj ET"
    pdf = f"""%PDF-1.4
1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj
2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj
3 0 obj<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 300 144] /Contents 5 0 R >>endobj
4 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj
5 0 obj<< /Length {len(stream)} >>stream
{stream}
endstream
endobj
xref
0 6
0000000000 65535 f
trailer<< /Size 6 /Root 1 0 R >>
startxref
0
%%EOF"""
    return pdf.encode("latin-1")


def _docx_bytes(paragraphs: list[str]) -> bytes:
    import io

    from docx import Document

    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _pdf_file(raw: bytes, filename: str):
    return {"file": (filename, raw, "application/pdf")}


def _docx_file(raw: bytes, filename: str):
    return {
        "file": (
            filename,
            raw,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _request_log.clear()
    _chatbot_request_log.clear()
    yield
    _request_log.clear()
    _chatbot_request_log.clear()


@pytest.fixture
def client(platform_token, test_chatbot):
    """
    這份測試檔案的所有請求都需要 chatbot_id 查詢參數 + Authorization header
    （/api/admin/documents* 加了 require_chatbot_access，見 app/main.py）。用 httpx.Client
    的預設 headers／params 機制，讓每一筆請求自動帶上，測試本體的呼叫寫法不用逐一修改。
    """
    with TestClient(app) as c:
        c.headers["Authorization"] = f"Bearer {platform_token}"
        c.params = {"chatbot_id": test_chatbot["id"]}
        yield c
        # 測試後清乾淨，避免留下測試資料污染共用的 pgvector table
        c.delete(f"/api/admin/documents/{TEST_PATH}")


def _upsert(client, path, tags, content, filename=None):
    return client.put(
        f"/api/admin/documents/{path}",
        data={"tags": tags, "client_sha256": _sha256(content)},
        files=_md_file(content, filename=filename or path.rsplit("/", 1)[-1]),
    )


def test_create_list_update_tags_delete_document_lifecycle(client):
    content_v1 = "# Pytest 測試文件\n\n## 測試小節\n這是 pytest 建立的測試內容。\n"

    # 1. 新增（PUT upsert，path 是路徑本身，帶 file + client_sha256）
    create_resp = _upsert(client, TEST_PATH, ["policy", "faq"], content_v1)
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["path"] == TEST_PATH
    assert set(created["tags"]) == {"policy", "faq"}
    assert created["chunk_count"] == 1
    assert created["content_changed"] is True
    assert created["content_hash"] == _sha256(content_v1)

    # 2. 非 .md 檔要回 400
    bad_ext_resp = client.put(
        "/api/admin/documents/other.md",
        data={"tags": [], "client_sha256": _sha256("x")},
        files={"file": ("not_markdown.txt", b"x", "text/plain")},
    )
    assert bad_ext_resp.status_code == 400

    # 2b. client_sha256 跟伺服器重算的雜湊不一致要回 400（硬性檢查，不能只靠前端自己比對）
    bad_hash_resp = client.put(
        "/api/admin/documents/mismatch.md",
        data={"tags": [], "client_sha256": "0" * 64},
        files=_md_file(content_v1, filename="mismatch.md"),
    )
    assert bad_hash_resp.status_code == 400

    # 3. 列表看得到剛新增的文件，且有記錄上傳時間/檔案大小/標籤
    list_resp = client.get("/api/admin/documents")
    assert list_resp.status_code == 200
    docs = {d["path"]: d for d in list_resp.json()["documents"]}
    assert TEST_PATH in docs
    assert docs[TEST_PATH]["uploaded_at"] is not None
    assert docs[TEST_PATH]["file_size_bytes"] > 0
    assert set(docs[TEST_PATH]["tags"]) == {"policy", "faq"}

    # 4. 上傳一模一樣的內容：應該偵測到沒變更，跳過重新 embed
    noop_resp = _upsert(client, TEST_PATH, ["policy", "faq"], content_v1)
    assert noop_resp.status_code == 200
    assert noop_resp.json()["content_changed"] is False

    # 5. 更新內容（tags 一併帶入，不用沿用既有標籤）
    content_v2 = "# Pytest 測試文件\n\n## 測試小節\n更新後的內容。\n"
    update_resp = _upsert(client, TEST_PATH, ["policy"], content_v2)
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["path"] == TEST_PATH
    assert updated["tags"] == ["policy"]
    assert updated["chunk_count"] == 1
    assert updated["content_changed"] is True

    # 5b. 更新時 client_sha256 不符也要回 400
    bad_update_resp = client.put(
        f"/api/admin/documents/{TEST_PATH}",
        data={"tags": ["policy"], "client_sha256": "0" * 64},
        files=_md_file(content_v2),
    )
    assert bad_update_resp.status_code == 400

    # 6. 只改標籤：不帶 file，只帶 tags + 目前內容的 client_sha256
    patch_resp = client.put(
        f"/api/admin/documents/{TEST_PATH}",
        data={"tags": ["policy", "updated"], "client_sha256": _sha256(content_v2)},
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    assert patched["tags"] == ["policy", "updated"]
    assert patched["content_changed"] is False

    # 7. 刪除
    delete_resp = client.delete(f"/api/admin/documents/{TEST_PATH}")
    assert delete_resp.status_code == 200
    assert delete_resp.json() == {"status": "deleted", "path": TEST_PATH}

    # 8. 刪除後列表查不到
    list_resp_after = client.get("/api/admin/documents")
    paths_after = [d["path"] for d in list_resp_after.json()["documents"]]
    assert TEST_PATH not in paths_after


def test_upsert_without_file_and_without_existing_content_returns_400(client):
    """路徑不存在、雜湊也沒命中任何既有內容時，沒帶 file 應該回 400（沒辦法生出內容）。"""
    resp = client.put(
        "/api/admin/documents/pytest_needs_file.md",
        data={"tags": [], "client_sha256": _sha256("從沒出現過的內容")},
    )
    assert resp.status_code == 400


def test_delete_nonexistent_document_returns_404(client):
    resp = client.delete("/api/admin/documents/does_not_exist.md")
    assert resp.status_code == 404


def test_delete_nested_path(client):
    """path 是相對路徑（含斜線）時，路徑參數要能吃得下去（{path:path}）。"""
    nested_path = "policy/faq/pytest_nested.md"
    content = "# Pytest 巢狀文件\n\n## 小節\n內容。\n"
    create_resp = _upsert(client, nested_path, [], content, filename="pytest_nested.md")
    assert create_resp.status_code == 200
    assert create_resp.json()["path"] == nested_path

    delete_resp = client.delete(f"/api/admin/documents/{nested_path}")
    assert delete_resp.status_code == 200
    assert delete_resp.json() == {"status": "deleted", "path": nested_path}


def test_upsert_pdf_file_extracts_and_chunks_text(client):
    """.pdf 上傳應該能被解析成至少一個 chunk（見 app/main.py 的 _extract_pdf_text、
    app/rag/documents_store.py 的 parse_plain_text——PDF 沒有 Markdown 標題結構，
    依字數切段）。雜湊比對的是原始 PDF bytes，不是抽出來的文字。"""
    path = "pytest_pdf_upload.pdf"
    raw = _minimal_pdf_bytes("Pytest PDF chunking test content")
    try:
        resp = client.put(
            f"/api/admin/documents/{path}",
            data={"tags": ["pdf"], "client_sha256": _sha256_bytes(raw)},
            files=_pdf_file(raw, path),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["chunk_count"] > 0
        assert body["content_changed"] is True
    finally:
        client.delete(f"/api/admin/documents/{path}")


def test_upsert_docx_file_extracts_and_chunks_text(client):
    """.docx 上傳應該能被解析成至少一個 chunk，流程與 .pdf 相同。"""
    path = "pytest_docx_upload.docx"
    raw = _docx_bytes(["測試標題", "這是 pytest 建立的 Word 測試內容。"])
    try:
        resp = client.put(
            f"/api/admin/documents/{path}",
            data={"tags": ["docx"], "client_sha256": _sha256_bytes(raw)},
            files=_docx_file(raw, path),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["chunk_count"] > 0
        assert body["content_changed"] is True
    finally:
        client.delete(f"/api/admin/documents/{path}")


def test_upsert_rejects_unsupported_extension(client):
    """非 .md／.pdf／.docx 的副檔名一律回 400。"""
    path = "pytest_unsupported.txt"
    raw = b"plain text"
    resp = client.put(
        f"/api/admin/documents/{path}",
        data={"tags": [], "client_sha256": _sha256_bytes(raw)},
        files={"file": (path, raw, "text/plain")},
    )
    assert resp.status_code == 400


def test_linked_status_shares_content_without_reembed(client):
    """
    同一份內容掛在兩個不同路徑：第二個路徑判定為 linked，不重新 embed；刪除其中一個路徑，
    另一個路徑的內容不受影響（一對多，doc_id 沒人指了才真的刪向量）。
    """
    content = "# 文件\n\n## 小節\n這份內容會同時掛在兩個路徑底下。\n"
    path_a = "pytest_linked_a.md"
    path_b = "policy/pytest_linked_b.md"

    create_resp = _upsert(client, path_a, ["a"], content, filename="pytest_linked_a.md")
    assert create_resp.status_code == 200
    original = create_resp.json()

    try:
        # precheck：path_b 沒有紀錄，但 hash 命中 path_a 既有的內容 -> linked
        precheck_resp = client.post(
            "/api/admin/documents/precheck",
            json={"items": [{"path": path_b, "client_sha256": _sha256(content), "tags": ["b"]}]},
        )
        assert precheck_resp.status_code == 200
        assert precheck_resp.json()["items"][0]["status"] == "linked"

        # 掛上第二個路徑：不帶 file
        link_resp = client.put(
            f"/api/admin/documents/{path_b}",
            data={"tags": ["b"], "client_sha256": _sha256(content)},
        )
        assert link_resp.status_code == 200
        linked = link_resp.json()
        assert linked["path"] == path_b
        assert linked["tags"] == ["b"]
        assert linked["content_changed"] is False
        assert linked["chunk_count"] == original["chunk_count"]

        # 兩個路徑都查得到，標籤各自獨立
        list_resp = client.get("/api/admin/documents")
        docs = {d["path"]: d for d in list_resp.json()["documents"]}
        assert path_a in docs and path_b in docs
        assert docs[path_a]["tags"] == ["a"]
        assert docs[path_b]["tags"] == ["b"]

        # 刪掉 path_a，path_b（同內容）應該不受影響
        del_resp = client.delete(f"/api/admin/documents/{path_a}")
        assert del_resp.status_code == 200
        list_resp2 = client.get("/api/admin/documents")
        docs2 = {d["path"]: d for d in list_resp2.json()["documents"]}
        assert path_a not in docs2
        assert path_b in docs2
        assert docs2[path_b]["chunk_count"] == original["chunk_count"]
    finally:
        client.delete(f"/api/admin/documents/{path_a}")
        client.delete(f"/api/admin/documents/{path_b}")


def test_content_changed_to_existing_content_relinks_and_gc_old(client):
    """
    路徑原本指向內容 A，這次上傳的內容其實跟另一個既有路徑的內容 B 完全一樣：
    應該判定 linked（不是 content_changed），且原本的內容 A 沒人指了要被清掉。
    """
    content_a = "# 文件 A\n\n## 小節\n內容 A。\n"
    content_b = "# 文件 B\n\n## 小節\n內容 B。\n"
    path_x = "pytest_relink_x.md"
    path_y = "pytest_relink_y.md"

    resp_x = _upsert(client, path_x, [], content_a, filename="pytest_relink_x.md")
    assert resp_x.status_code == 200
    resp_y = _upsert(client, path_y, [], content_b, filename="pytest_relink_y.md")
    assert resp_y.status_code == 200
    y_chunk_count = resp_y.json()["chunk_count"]

    try:
        # 把 path_x 的內容換成跟 path_y 一樣：應該判定 linked，不重新 embed
        relink_resp = client.put(
            f"/api/admin/documents/{path_x}",
            data={"tags": ["x"], "client_sha256": _sha256(content_b)},
        )
        assert relink_resp.status_code == 200
        relinked = relink_resp.json()
        assert relinked["content_changed"] is False
        assert relinked["chunk_count"] == y_chunk_count

        # path_x 現在的內容雜湊應該等於 content_b
        list_resp = client.get("/api/admin/documents")
        docs = {d["path"]: d for d in list_resp.json()["documents"]}
        assert docs[path_x]["content_hash"] == _sha256(content_b)
    finally:
        client.delete(f"/api/admin/documents/{path_x}")
        client.delete(f"/api/admin/documents/{path_y}")


class TestPrecheck:
    """POST /api/admin/documents/precheck 五種狀態分類 + scope_prefix 算 stale_paths。"""

    PREFIX = "pytest_precheck/"

    def _path(self, name: str) -> str:
        return f"{self.PREFIX}{name}"

    def _create(self, client, name: str, content: str, tags=None):
        path = self._path(name)
        resp = _upsert(client, path, tags or [], content, filename=name)
        assert resp.status_code == 200
        return path

    def test_precheck_status_classification_and_stale_paths(self, client):
        content_unchanged = "# 文件\n\n## 小節\n不變內容。\n"
        content_old = "# 文件\n\n## 小節\n舊內容。\n"
        content_new_version = "# 文件\n\n## 小節\n新內容。\n"

        unchanged_path = self._create(client, "unchanged.md", content_unchanged, tags=["a"])
        changed_path = self._create(client, "changed.md", content_old, tags=["a"])
        tags_only_path = self._create(client, "tags_only.md", content_unchanged, tags=["a"])
        stale_path = self._create(client, "stale.md", content_unchanged, tags=["a"])

        try:
            precheck_resp = client.post(
                "/api/admin/documents/precheck",
                json={
                    "scope_prefix": self.PREFIX,
                    "items": [
                        {"path": self._path("brand_new.md"), "client_sha256": _sha256("brand new"), "tags": []},
                        {"path": unchanged_path, "client_sha256": _sha256(content_unchanged), "tags": ["a"]},
                        {"path": changed_path, "client_sha256": _sha256(content_new_version), "tags": ["a"]},
                        {"path": tags_only_path, "client_sha256": _sha256(content_unchanged), "tags": ["b"]},
                    ],
                },
            )
            assert precheck_resp.status_code == 200
            body = precheck_resp.json()
            results = {item["path"]: item["status"] for item in body["items"]}
            assert results[self._path("brand_new.md")] == "new"
            assert results[unchanged_path] == "unchanged"
            assert results[changed_path] == "content_changed"
            assert results[tags_only_path] == "tags_only_changed"

            # stale.md 沒有出現在這次 items 裡，應該被列進 stale_paths
            assert body["stale_paths"] == [stale_path]
        finally:
            for path in [unchanged_path, changed_path, tags_only_path, stale_path]:
                client.delete(f"/api/admin/documents/{path}")

    def test_precheck_linked_status_old_path_still_counts_as_stale(self, client):
        """一對多模型下，linked 不會把舊路徑搬走——舊路徑是獨立仍然有效的紀錄，這次批次
        沒包含到它的話，理應跟其他未涵蓋到的路徑一樣被列進 stale_paths（待你決定要不要刪）。"""
        content = "# 文件\n\n## 小節\n內容。\n"
        old_path = self._create(client, "old_path.md", content, tags=["a"])
        new_path = self._path("new_path.md")

        try:
            precheck_resp = client.post(
                "/api/admin/documents/precheck",
                json={
                    "scope_prefix": self.PREFIX,
                    "items": [{"path": new_path, "client_sha256": _sha256(content), "tags": ["a"]}],
                },
            )
            assert precheck_resp.status_code == 200
            body = precheck_resp.json()
            item = body["items"][0]
            assert item["status"] == "linked"
            assert old_path in body["stale_paths"]
        finally:
            client.delete(f"/api/admin/documents/{old_path}")
            client.delete(f"/api/admin/documents/{new_path}")

    def test_precheck_without_scope_prefix_returns_empty_stale_list(self, client):
        content = "# 文件\n\n## 小節\n內容。\n"
        path = self._path("no_scope.md")
        try:
            resp = client.post(
                "/api/admin/documents/precheck",
                json={"items": [{"path": path, "client_sha256": _sha256(content), "tags": []}]},
            )
            assert resp.status_code == 200
            assert resp.json()["stale_paths"] == []
        finally:
            client.delete(f"/api/admin/documents/{path}")


class TestChatbotIsolation:
    """
    多租戶 chatbot_id 隔離：同名 path／同雜湊在不同 chatbot_id 下互不干擾，各自視為獨立的
    new；一家公司的文件列表看不到另一家公司的文件；purge_chatbot 之後這家公司的文件與
    （靠 chatbot_id metadata 過濾的）檢索都要清空。
    """

    def test_same_path_and_hash_are_independent_across_chatbots(self, client, platform_token):
        from app import accounts_store

        other_chatbot = accounts_store.create_chatbot("Pytest 隔離測試 - 另一家公司", None)
        path = "pytest_isolation_shared_path.md"
        content = "# 隔離測試\n\n## 小節\n兩家公司各自上傳同樣的路徑跟內容。\n"
        headers = {"Authorization": f"Bearer {platform_token}"}
        try:
            # 公司 A（client fixture 預設的 test_chatbot）新增這個路徑
            resp_a = client.put(
                f"/api/admin/documents/{path}",
                data={"tags": ["a"], "client_sha256": _sha256(content)},
                files=_md_file(content, filename=path),
            )
            assert resp_a.status_code == 200

            # 公司 B 上傳一模一樣的路徑＋內容：因為 chatbot_id 不同，應該視為全新的 new
            # （不是 linked、也不會被視為已存在），content_changed 為 True。
            resp_b = client.put(
                f"/api/admin/documents/{path}",
                params={"chatbot_id": other_chatbot["id"]},
                data={"tags": ["b"], "client_sha256": _sha256(content)},
                files=_md_file(content, filename=path),
            )
            assert resp_b.status_code == 200
            assert resp_b.json()["content_changed"] is True

            # 公司 A 的列表看不到公司 B 的標籤，反之亦然（各自只看到自己那份，tags 不同）
            list_a = client.get("/api/admin/documents").json()["documents"]
            list_b = client.get(
                "/api/admin/documents", params={"chatbot_id": other_chatbot["id"]}
            ).json()["documents"]
            docs_a = {d["path"]: d for d in list_a}
            docs_b = {d["path"]: d for d in list_b}
            assert docs_a[path]["tags"] == ["a"]
            assert docs_b[path]["tags"] == ["b"]
        finally:
            client.delete(f"/api/admin/documents/{path}")
            client.delete(f"/api/admin/documents/{path}", params={"chatbot_id": other_chatbot["id"]})
            accounts_store.delete_chatbot(other_chatbot["id"])

    def test_purge_chatbot_clears_documents_and_vectors(self, client, platform_token):
        from app import accounts_store
        from app.rag.documents_store import list_documents as _list_documents, purge_chatbot
        from app.rag.engine import get_retriever

        purge_chatbot_target = accounts_store.create_chatbot("Pytest 待刪除公司", None)
        path = "pytest_purge_target.md"
        content = "# 待刪除\n\n## 小節\n這份文件所屬的公司會被整個刪除。\n"

        upload_resp = client.put(
            f"/api/admin/documents/{path}",
            params={"chatbot_id": purge_chatbot_target["id"]},
            data={"tags": [], "client_sha256": _sha256(content)},
            files=_md_file(content, filename=path),
        )
        assert upload_resp.status_code == 200
        assert upload_resp.json()["chunk_count"] > 0

        # 刪除前：list_documents(chatbot_id) 應該看得到這筆
        assert len(_list_documents(purge_chatbot_target["id"])) == 1

        purge_chatbot(purge_chatbot_target["id"], get_retriever().index)
        accounts_store.delete_chatbot(purge_chatbot_target["id"])

        # 刪除後：文件記錄清空
        assert _list_documents(purge_chatbot_target["id"]) == []
