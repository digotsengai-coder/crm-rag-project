import DeleteOutlined from "@ant-design/icons/DeleteOutlined";
import DownOutlined from "@ant-design/icons/DownOutlined";
import FileOutlined from "@ant-design/icons/FileOutlined";
import FolderOpenOutlined from "@ant-design/icons/FolderOpenOutlined";
import InboxOutlined from "@ant-design/icons/InboxOutlined";
import ReloadOutlined from "@ant-design/icons/ReloadOutlined";
import SearchOutlined from "@ant-design/icons/SearchOutlined";
import UpOutlined from "@ant-design/icons/UpOutlined";
import Alert from "antd/es/alert";
import Button from "antd/es/button";
import Card from "antd/es/card";
import Checkbox from "antd/es/checkbox";
import Collapse from "antd/es/collapse";
import Empty from "antd/es/empty";
import Form from "antd/es/form";
import Input from "antd/es/input";
import InputNumber from "antd/es/input-number";
import message from "antd/es/message";
import Modal from "antd/es/modal";
import Popconfirm from "antd/es/popconfirm";
import Select from "antd/es/select";
import Space from "antd/es/space";
import Switch from "antd/es/switch";
import Table from "antd/es/table";
import Tag from "antd/es/tag";
import Typography from "antd/es/typography";
import Upload from "antd/es/upload";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Navigate, useBeforeUnload, useBlocker } from "react-router-dom";
import AdminPageLayout from "../components/AdminPageLayout";
import CardLoading from "../components/CardLoading";
import ChatbotSettingsTabs from "../components/ChatbotSettingsTabs";
import {
  deleteDocument,
  precheckDocuments,
  sha256Hex,
  upsertDocument,
} from "../api/documents";
import type {
  DocumentInfo,
  PrecheckRequestItem,
  PrecheckStatus,
} from "../types/documents";
import { useAuth } from "../auth/AuthContext";
import ChatWidgetPreview from "../components/ChatWidgetPreview";
import { updateChatbot } from "../api/chatbots";
import { ui } from "../uiStyles";
import { queryKeys } from "../api/queryKeys";
import { queryClient } from "../queryClient";
import {
  useDocumentsQuery,
  useUpdateChatbotMutation,
} from "../hooks/useAdminQueries";
import { useSelectedChatbot } from "../hooks/useSelectedChatbot";
import { tw } from "../utils/tw";

const { Text } = Typography;
const { Dragger } = Upload;

const ACCEPTED_EXTENSIONS = [".md", ".pdf", ".docx"];
// 後端 embedding 是本地 CPU 推論（onnxruntime，見 backend/app/rag/onnx_embedding.py）。
// 曾因 Cloud Run 只有 1 vCPU，並行處理搶同一顆 CPU 導致誤判失敗；已在 cloudbuild.yaml
// 的 backend-deploy 加上 --cpu=2 --concurrency=10 給予足夠運算資源，這裡維持並行處理。
const CONCURRENCY_LIMIT = 4;
const DEFAULT_RAG_TOP_K = 5;
const MAX_RAG_TOP_K = 10;

// lib.dom 的 File 型別不一定含 webkitRelativePath（非標準屬性），用交集型別擴充，
// 避免整份改用 any 而失去其餘欄位的型別檢查。
type FileWithRelativePath = File & { webkitRelativePath?: string };

type RowProgress = "pending" | "processing" | "success" | "error";

interface ProcessRow {
  path: string;
  tags: string[];
  status: PrecheckStatus;
  file: File | null;
  clientSha256: string;
  progress: RowProgress;
}

interface StaleRow {
  path: string;
  checked: boolean;
  progress: RowProgress;
}

function isAcceptedFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

function formatBytes(bytes: number | null): string {
  if (bytes === null) return "-";
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function formatUploadedAt(iso: string | null): string {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

// 去掉前後空白與多餘斜線，非空的話補上結尾斜線，方便直接接資料夾相對路徑。
function normalizeUpperPath(upperPath: string): string {
  const trimmed = upperPath.trim().replace(/^\/+|\/+$/g, "");
  return trimmed ? `${trimmed}/` : "";
}

function getSelectionKey(file: File): string {
  return (file as FileWithRelativePath).webkitRelativePath || file.name;
}

function uniqueTags(tags: string[]): string[] {
  return Array.from(new Set(tags));
}

function getDocumentPathAndTags(
  file: File,
  upperPath: string,
  manualTags: string[],
): { path: string; tags: string[] } {
  const relativePath = (file as FileWithRelativePath).webkitRelativePath;
  if (!relativePath) return { path: file.name, tags: uniqueTags(manualTags) };

  const folderTags = relativePath.split("/").slice(0, -1); // 資料夾各層名稱視為標籤
  const prefix = normalizeUpperPath(upperPath);
  const upperTags = prefix
    ? prefix.slice(0, -1).split("/").filter(Boolean)
    : [];
  return {
    path: `${prefix}${relativePath}`,
    tags: uniqueTags([...upperTags, ...folderTags]),
  };
}

function getScopePrefix(files: File[], upperPath: string): string | null {
  if (files.length === 0) return null;
  const relativePaths = files.map(
    (file) => (file as FileWithRelativePath).webkitRelativePath,
  );
  if (relativePaths.some((path) => !path)) return null;
  const topFolders = new Set(relativePaths.map((path) => path!.split("/")[0]));
  if (topFolders.size !== 1) return null;
  const topFolder = relativePaths[0]!.split("/")[0];
  return `${normalizeUpperPath(upperPath)}${topFolder}/`;
}

const PROGRESS_LABEL: Record<RowProgress, string> = {
  pending: "待處理",
  processing: "處理中...",
  success: "成功",
  error: "失敗",
};

const STATUS_LABEL: Record<PrecheckStatus, string> = {
  new: "新增",
  content_changed: "內容更新",
  tags_only_changed: "僅標籤更新",
  unchanged: "無變更",
  linked: "沿用既有內容",
};

// 有限並行處理，避免一次對後端發出過多請求。
async function runWithConcurrency<T>(
  items: T[],
  limit: number,
  worker: (item: T) => Promise<void>,
): Promise<void> {
  let cursor = 0;
  async function runNext(): Promise<void> {
    const current = cursor;
    cursor += 1;
    if (current >= items.length) return;
    await worker(items[current]);
    await runNext();
  }
  const runnerCount = Math.min(limit, items.length);
  await Promise.all(Array.from({ length: runnerCount }, () => runNext()));
}

function TagChipsInput({
  id,
  tags,
  onChange,
  placeholder,
}: {
  id: string;
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
}) {
  return (
    <Select
      id={id}
      mode="tags"
      value={tags}
      tokenSeparators={[","]}
      open={false}
      className={ui.fullWidth}
      onChange={onChange}
      placeholder={placeholder}
      options={[]}
    />
  );
}

export default function AdminDocumentsPage() {
  const { token } = useAuth();
  const { chatbot, selectedChatbotId } = useSelectedChatbot();
  const updateMutation = useUpdateChatbotMutation(token ?? "");
  const documentsQuery = useDocumentsQuery(token, selectedChatbotId);
  const loadDocuments = () => documentsQuery.refetch();
  const [settingsForm] = Form.useForm<{
    rag_top_k: number;
    rerank_enabled: boolean;
  }>();
  const [savingSettings, setSavingSettings] = useState(false);
  const [messageApi, messageContextHolder] = message.useMessage();
  const [modalApi, modalContextHolder] = Modal.useModal();
  const filesInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const fileDragDepthRef = useRef(0);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const loading = documentsQuery.isLoading;
  const [notice, setNotice] = useState<string | null>(null);

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [skippedCount, setSkippedCount] = useState(0);
  const [manualTags, setManualTags] = useState<string[]>([]);
  const [upperPath, setUpperPath] = useState("");

  const [analyzing, setAnalyzing] = useState(false);
  const [precheckDone, setPrecheckDone] = useState(false);
  const [processRows, setProcessRows] = useState<ProcessRow[]>([]);
  const [staleRows, setStaleRows] = useState<StaleRow[]>([]);
  const [duplicatePaths, setDuplicatePaths] = useState<string[]>([]);
  const [processing, setProcessing] = useState(false);

  const [tagFilters, setTagFilters] = useState<string[]>([]);
  const [searchText, setSearchText] = useState("");
  const [isDraggingFiles, setIsDraggingFiles] = useState(false);
  const hasUnanalyzedFiles = selectedFiles.length > 0 && !precheckDone;
  const navigationBlocker = useBlocker(hasUnanalyzedFiles);

  useEffect(() => {
    setDocuments([]);
  }, [selectedChatbotId]);

  useEffect(() => {
    if (!chatbot) return;
    settingsForm.setFieldsValue({
      rag_top_k: chatbot.rag_top_k ?? DEFAULT_RAG_TOP_K,
      rerank_enabled: chatbot.rerank_enabled ?? false,
    });
  }, [chatbot, settingsForm]);

  async function handleSaveSettings(values: {
    rag_top_k: number;
    rerank_enabled: boolean;
  }) {
    if (!token || !selectedChatbotId) return;
    setSavingSettings(true);
    try {
      await updateMutation.mutateAsync({
        chatbotId: selectedChatbotId,
        params: {
          rag_top_k: values.rag_top_k,
          ...(values.rerank_enabled !== !!chatbot?.rerank_enabled
            ? { rerank_enabled: values.rerank_enabled }
            : {}),
        },
      });
      messageApi.success("已儲存知識設定");
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "儲存失敗");
    } finally {
      setSavingSettings(false);
    }
  }

  useBeforeUnload(
    useCallback(
      (event) => {
        if (!hasUnanalyzedFiles) return;
        event.preventDefault();
        event.returnValue = "";
      },
      [hasUnanalyzedFiles],
    ),
    { capture: true },
  );

  useEffect(() => {
    if (navigationBlocker.state !== "blocked") return;
    modalApi.confirm({
      title: "文件尚未分析",
      content: "目前選取的文件尚未完成分析，確定要離開此頁面嗎？",
      okText: "確定離開",
      cancelText: "繼續分析",
      okButtonProps: { danger: true },
      onOk: () => navigationBlocker.proceed(),
      onCancel: () => navigationBlocker.reset(),
    });
  }, [modalApi, navigationBlocker]);

  // query key 包含 selectedChatbotId；切換公司時不會短暫顯示另一家文件。
  useEffect(() => {
    if (documentsQuery.data) setDocuments(documentsQuery.data);
  }, [documentsQuery.data]);

  useEffect(() => {
    function hasFiles(event: DragEvent): boolean {
      return Array.from(event.dataTransfer?.types ?? []).includes("Files");
    }

    function handleDragEnter(event: DragEvent) {
      if (!hasFiles(event)) return;
      fileDragDepthRef.current += 1;
      setIsDraggingFiles(true);
    }

    function handleDragOver(event: DragEvent) {
      if (!hasFiles(event)) return;
      event.preventDefault();
    }

    function handleDragLeave(event: DragEvent) {
      if (!hasFiles(event)) return;
      fileDragDepthRef.current = Math.max(0, fileDragDepthRef.current - 1);
      if (fileDragDepthRef.current === 0) setIsDraggingFiles(false);
    }

    function resetFileDrag() {
      fileDragDepthRef.current = 0;
      setIsDraggingFiles(false);
    }

    document.addEventListener("dragenter", handleDragEnter);
    document.addEventListener("dragover", handleDragOver);
    document.addEventListener("dragleave", handleDragLeave);
    document.addEventListener("drop", resetFileDrag);
    document.addEventListener("dragend", resetFileDrag);
    window.addEventListener("blur", resetFileDrag);
    return () => {
      document.removeEventListener("dragenter", handleDragEnter);
      document.removeEventListener("dragover", handleDragOver);
      document.removeEventListener("dragleave", handleDragLeave);
      document.removeEventListener("drop", resetFileDrag);
      document.removeEventListener("dragend", resetFileDrag);
      window.removeEventListener("blur", resetFileDrag);
    };
  }, []);

  function resetSelection() {
    setSelectedFiles([]);
    setSkippedCount(0);
    setPrecheckDone(false);
    setProcessRows([]);
    setStaleRows([]);
    setDuplicatePaths([]);
  }

  function invalidatePrecheck() {
    setPrecheckDone(false);
    setProcessRows([]);
    setStaleRows([]);
    setDuplicatePaths([]);
  }

  function addSelectedFiles(files: File[]) {
    const acceptedFiles = files.filter(isAcceptedFile);
    const rejectedCount = files.length - acceptedFiles.length;
    if (rejectedCount > 0) setSkippedCount((count) => count + rejectedCount);
    if (acceptedFiles.length === 0) return;

    setSelectedFiles((currentFiles) => {
      const merged = new Map(
        currentFiles.map((file) => [getSelectionKey(file), file]),
      );
      acceptedFiles.forEach((file) => merged.set(getSelectionKey(file), file));
      return Array.from(merged.values());
    });
    invalidatePrecheck();
  }

  function handleFilesInputChange(event: React.ChangeEvent<HTMLInputElement>) {
    addSelectedFiles(Array.from(event.target.files ?? []));
    event.target.value = "";
  }

  function removeSelectedFile(file: File) {
    const key = getSelectionKey(file);
    setSelectedFiles((currentFiles) =>
      currentFiles.filter((item) => getSelectionKey(item) !== key),
    );
    invalidatePrecheck();
  }

  async function analyzeSelection() {
    if (selectedFiles.length === 0 || !token || !selectedChatbotId) return;
    setAnalyzing(true);
    setNotice(null);
    try {
      const fileEntries = selectedFiles.map((file) => {
        const { path, tags } = getDocumentPathAndTags(
          file,
          upperPath,
          manualTags,
        );
        return { file, path, tags };
      });

      const hashes = await Promise.all(
        fileEntries.map((entry) => sha256Hex(entry.file)),
      );
      const entryByPath = new Map(
        fileEntries.map((entry, index) => [
          entry.path,
          { ...entry, hash: hashes[index] },
        ]),
      );

      const items: PrecheckRequestItem[] = fileEntries.map((entry, index) => ({
        path: entry.path,
        client_sha256: hashes[index],
        tags: entry.tags,
      }));
      const scopePrefix = getScopePrefix(selectedFiles, upperPath);
      const response = await precheckDocuments(
        token,
        selectedChatbotId,
        items,
        scopePrefix,
      );

      const rows: ProcessRow[] = [];
      const duplicates: string[] = [];
      response.items.forEach((item) => {
        if (item.status === "unchanged") {
          duplicates.push(item.path);
          return;
        }
        const entry = entryByPath.get(item.path);
        if (!entry) return;
        rows.push({
          path: item.path,
          tags: entry.tags,
          status: item.status,
          file: entry.file,
          clientSha256: entry.hash,
          progress: "pending",
        });
      });

      setProcessRows(rows);
      setDuplicatePaths(duplicates);
      setStaleRows(
        response.stale_paths.map((path) => ({
          path,
          checked: false,
          progress: "pending",
        })),
      );
      setPrecheckDone(true);
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "分析檔案失敗");
    } finally {
      setAnalyzing(false);
    }
  }

  function updateProcessRow(path: string, patch: Partial<ProcessRow>) {
    setProcessRows((prev) =>
      prev.map((row) => (row.path === path ? { ...row, ...patch } : row)),
    );
  }

  function updateStaleRow(path: string, patch: Partial<StaleRow>) {
    setStaleRows((prev) =>
      prev.map((row) => (row.path === path ? { ...row, ...patch } : row)),
    );
  }

  async function processOneRow(row: ProcessRow) {
    if (!token || !selectedChatbotId) return;
    updateProcessRow(row.path, { progress: "processing" });
    try {
      // new/content_changed 才需要真的帶檔案內容；tags_only_changed/linked 只改標籤紀錄，不用上傳。
      const needsFile =
        row.status === "new" || row.status === "content_changed";
      if (needsFile && !row.file)
        throw new Error("缺少檔案內容，請重新選擇檔案。");
      await upsertDocument(token, selectedChatbotId, {
        path: row.path,
        tags: row.tags,
        clientSha256: row.clientSha256,
        file: needsFile ? row.file! : undefined,
      });
      updateProcessRow(row.path, { progress: "success" });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "處理失敗";
      updateProcessRow(row.path, { progress: "error" });
      messageApi.error(`${row.path}：${errorMessage}`);
    }
  }

  async function processOneDelete(row: StaleRow) {
    if (!token || !selectedChatbotId) return;
    updateStaleRow(row.path, { progress: "processing" });
    try {
      await deleteDocument(token, selectedChatbotId, row.path);
      updateStaleRow(row.path, { progress: "success" });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "刪除失敗";
      updateStaleRow(row.path, { progress: "error" });
      messageApi.error(`${row.path}：${errorMessage}`);
    }
  }

  async function handleStartProcessing() {
    const rowsToProcess = processRows.filter(
      (row) => row.progress !== "success",
    );
    const deletesToRun = staleRows.filter(
      (row) => row.checked && row.progress !== "success",
    );
    if (rowsToProcess.length === 0 && deletesToRun.length === 0) return;

    setProcessing(true);
    setNotice(null);
    try {
      await runWithConcurrency(rowsToProcess, CONCURRENCY_LIMIT, processOneRow);
      await runWithConcurrency(
        deletesToRun,
        CONCURRENCY_LIMIT,
        processOneDelete,
      );
      setNotice("批次處理完成，已重新整理文件列表。");
      await loadDocuments();
    } finally {
      setProcessing(false);
    }
  }

  const allTags = useMemo(
    () => Array.from(new Set(documents.flatMap((doc) => doc.tags))).sort(),
    [documents],
  );

  const filteredDocuments = useMemo(() => {
    const keyword = searchText.trim().toLowerCase();
    return documents.filter((doc) => {
      const matchesKeyword =
        keyword === "" || doc.path.toLowerCase().includes(keyword);
      const matchesTags =
        tagFilters.length === 0 ||
        tagFilters.some((tag) => doc.tags.includes(tag));
      return matchesKeyword && matchesTags;
    });
  }, [documents, searchText, tagFilters]);

  async function handleDelete(path: string) {
    if (!token || !selectedChatbotId) return;
    setNotice(null);
    try {
      await deleteDocument(token, selectedChatbotId, path);
      queryClient.setQueryData<DocumentInfo[]>(
        queryKeys.documents.byChatbot(selectedChatbotId),
        (current) => current?.filter((doc) => doc.path !== path),
      );
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "刪除文件失敗");
    }
  }

  if (!selectedChatbotId) return <Navigate to="/chatbots" replace />;

  return (
    <AdminPageLayout
      title="知識管理"
      description="管理聊天機器人檢索使用的 Markdown 文件與分類標籤。"
      beforeHeader={
        <>
          {messageContextHolder}
          {modalContextHolder}
          {/* 讓管理者可以直接在這頁測試「目前選定公司」的聊天機器人回答，不用切去 corp-frontend。 */}
          <ChatWidgetPreview chatbotId={selectedChatbotId} />
          {isDraggingFiles ? (
            <div className={ui.ragDragOverlay} aria-hidden="true" />
          ) : null}
        </>
      }
      // headerExtra={
      //   <Tag className={ui.headingTag} color="blue">
      //     {documents.length} 份文件
      //   </Tag>
      // }
    >
      <ChatbotSettingsTabs />
      <Card className={ui.settingsCard} title="檢索設定">
        <Form
          form={settingsForm}
          layout="vertical"
          onFinish={handleSaveSettings}
        >
          <Form.Item
            name="rag_top_k"
            label="檢索片段數（k）"
            extra={`每次回答從知識庫挑選的內容數量（1～${MAX_RAG_TOP_K}）。`}
            rules={[{ required: true, message: "請輸入片段數" }]}
          >
            <InputNumber min={1} max={MAX_RAG_TOP_K} precision={0} />
          </Form.Item>
          <Form.Item
            name="rerank_enabled"
            label="重排序（rerank）"
            valuePropName="checked"
            extra={
              chatbot?.rerank_available
                ? "使用重排序模型挑選最相關片段。"
                : "這個環境目前不支援重排序。"
            }
          >
            <Switch
              disabled={!chatbot?.rerank_available && !chatbot?.rerank_enabled}
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={savingSettings}>
            儲存知識設定
          </Button>
        </Form>
      </Card>
      {notice ? (
        <Alert
          type="success"
          showIcon
          message={notice}
          closable
          onClose={() => setNotice(null)}
        />
      ) : null}

      <Collapse
        className={ui.ragUploadCollapse}
        defaultActiveKey={["upload"]}
        expandIconPosition="end"
        expandIcon={({ isActive }) =>
          isActive ? <UpOutlined /> : <DownOutlined />
        }
        items={[
          {
            key: "upload",
            label: "新增或更新文件",
            children: (
              <>
                <Dragger
                  className={tw(
                    ui.ragDragger,
                    isDraggingFiles && ui.ragDragging,
                  )}
                  directory
                  multiple
                  openFileDialogOnClick
                  showUploadList={false}
                  beforeUpload={(file) => {
                    addSelectedFiles([file]);
                    return false;
                  }}
                >
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined />
                  </p>
                  <p className="ant-upload-text">
                    拖曳 Markdown／PDF／Word 檔案或整個資料夾至此
                  </p>
                  <p className="ant-upload-hint">
                    支援單一檔案、多檔案與資料夾；只會加入 .md、.pdf、.docx
                    檔案，不會立即上傳。
                  </p>
                  <Space className={ui.ragPickerActions} wrap>
                    <Button
                      icon={<FileOutlined />}
                      onClick={(event) => {
                        event.stopPropagation();
                        filesInputRef.current?.click();
                      }}
                    >
                      選擇檔案
                    </Button>
                    <Button
                      icon={<FolderOpenOutlined />}
                      onClick={(event) => {
                        event.stopPropagation();
                        folderInputRef.current?.click();
                      }}
                    >
                      選擇資料夾
                    </Button>
                  </Space>
                </Dragger>

                <input
                  ref={filesInputRef}
                  className={ui.visuallyHidden}
                  type="file"
                  accept={ACCEPTED_EXTENSIONS.join(",")}
                  multiple
                  onChange={handleFilesInputChange}
                />
                <input
                  ref={folderInputRef}
                  className={ui.visuallyHidden}
                  type="file"
                  multiple
                  onChange={handleFilesInputChange}
                  {...({ webkitdirectory: "true" } as Record<string, string>)}
                />

                <div className={ui.ragUploadOptions}>
                  <div className={ui.ragField}>
                    <Text type="secondary">散落檔案標籤</Text>
                    <TagChipsInput
                      id="rag-manual-tags"
                      tags={manualTags}
                      onChange={(tags) => {
                        setManualTags(tags);
                        invalidatePrecheck();
                      }}
                      placeholder="輸入標籤後按 Enter"
                    />
                  </div>
                  <div className={ui.ragField}>
                    <Text type="secondary">資料夾上層路徑（選填）</Text>
                    <Input
                      value={upperPath}
                      onChange={(event) => {
                        setUpperPath(event.target.value);
                        invalidatePrecheck();
                      }}
                      placeholder="例如 policy/knowledge"
                    />
                  </div>
                </div>

                {selectedFiles.length > 0 ? (
                  <div className={ui.ragSelectedFiles} aria-label="已選取檔案">
                    {selectedFiles.map((file) => (
                      <div
                        className={ui.ragSelectedFile}
                        key={getSelectionKey(file)}
                      >
                        <FileOutlined />
                        <div>
                          <Text>{getSelectionKey(file)}</Text>
                          <Text type="secondary">{formatBytes(file.size)}</Text>
                        </div>
                        <Button
                          type="text"
                          danger
                          icon={<DeleteOutlined />}
                          aria-label={`移除 ${getSelectionKey(file)}`}
                          onClick={() => removeSelectedFile(file)}
                        />
                      </div>
                    ))}
                  </div>
                ) : null}

                <div className={ui.ragSelectionSummary}>
                  <Text type="secondary">
                    {selectedFiles.length > 0
                      ? `已選取 ${selectedFiles.length} 個檔案`
                      : "尚未選取檔案"}
                    {skippedCount > 0
                      ? `，已略過 ${skippedCount} 個不支援的檔案`
                      : ""}
                  </Text>
                  <Button
                    type="primary"
                    loading={analyzing}
                    disabled={selectedFiles.length === 0}
                    onClick={analyzeSelection}
                  >
                    上傳檔案
                  </Button>
                </div>

                {precheckDone ? (
                  <div className={ui.ragReview}>
                    {duplicatePaths.length > 0 ? (
                      <div className={ui.ragReviewSection}>
                        <Alert
                          type="warning"
                          showIcon
                          message={`發現 ${duplicatePaths.length} 份重複文件`}
                          description={
                            <ul className={ui.ragDuplicateList}>
                              {duplicatePaths.map((path) => (
                                <li key={path}>
                                  <strong>{path}</strong>{" "}
                                  檔案已重複，內容與標籤皆無變更。
                                </li>
                              ))}
                            </ul>
                          }
                        />
                      </div>
                    ) : null}

                    {staleRows.length > 0 ? (
                      <div className={ui.ragReviewSection}>
                        <div className={ui.ragSubheading}>
                          <div>
                            <h3>待刪除的舊文件</h3>
                            <p>
                              此範圍內未包含於本次選取的文件，請確認後勾選。
                            </p>
                          </div>
                        </div>
                        <div className={ui.ragStaleList}>
                          {staleRows.map((row) => (
                            <div className={ui.ragStaleRow} key={row.path}>
                              <Checkbox
                                checked={row.checked}
                                onChange={(event) =>
                                  updateStaleRow(row.path, {
                                    checked: event.target.checked,
                                  })
                                }
                              >
                                {row.path}
                              </Checkbox>
                              <Tag
                                color={
                                  row.progress === "error"
                                    ? "error"
                                    : row.progress === "success"
                                      ? "success"
                                      : row.progress === "processing"
                                        ? "processing"
                                        : "default"
                                }
                              >
                                {PROGRESS_LABEL[row.progress]}
                              </Tag>
                              {row.progress === "error" ? (
                                <Button
                                  size="small"
                                  onClick={() => processOneDelete(row)}
                                >
                                  重試
                                </Button>
                              ) : null}
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {processRows.length > 0 ? (
                      <div className={ui.ragReviewSection}>
                        <div className={ui.ragSubheading}>
                          <div>
                            <h3>要處理的文件</h3>
                            <p>預檢會略過內容與標籤皆未變更的文件。</p>
                          </div>
                        </div>
                        <Table<ProcessRow>
                          rowKey="path"
                          size="small"
                          pagination={false}
                          dataSource={processRows}
                          scroll={{ x: 760 }}
                          columns={[
                            {
                              title: "路徑",
                              dataIndex: "path",
                              key: "path",
                              ellipsis: true,
                            },
                            {
                              title: "標籤",
                              dataIndex: "tags",
                              key: "tags",
                              render: (tags: string[]) => (
                                <Space size={[4, 4]} wrap>
                                  {uniqueTags(tags).map((tag) => (
                                    <Tag key={tag}>{tag}</Tag>
                                  ))}
                                </Space>
                              ),
                            },
                            {
                              title: "動作",
                              dataIndex: "status",
                              key: "status",
                              width: 110,
                              render: (status: PrecheckStatus) =>
                                STATUS_LABEL[status],
                            },
                            {
                              title: "狀態",
                              dataIndex: "progress",
                              key: "progress",
                              width: 150,
                              render: (progress: RowProgress) => (
                                <Tag
                                  color={
                                    progress === "error"
                                      ? "error"
                                      : progress === "success"
                                        ? "success"
                                        : progress === "processing"
                                          ? "processing"
                                          : "default"
                                  }
                                >
                                  {PROGRESS_LABEL[progress]}
                                </Tag>
                              ),
                            },
                            {
                              title: "操作",
                              key: "action",
                              width: 80,
                              render: (_, row) =>
                                row.progress === "error" ? (
                                  <Button
                                    size="small"
                                    onClick={() => processOneRow(row)}
                                  >
                                    重試
                                  </Button>
                                ) : null,
                            },
                          ]}
                        />
                      </div>
                    ) : null}

                    <Space>
                      <Button
                        type="primary"
                        loading={processing}
                        onClick={handleStartProcessing}
                      >
                        開始處理
                      </Button>
                      <Button
                        icon={<ReloadOutlined />}
                        disabled={processing}
                        onClick={resetSelection}
                      >
                        清空選取
                      </Button>
                    </Space>
                  </div>
                ) : null}
              </>
            ),
          },
        ]}
      />

      <Card
        className={ui.ragDocumentsCard}
        title="文件列表"
        extra={
          <Text type="secondary">
            顯示 {filteredDocuments.length} / {documents.length}
          </Text>
        }
      >
        <div className={ui.ragTableTools}>
          <Input
            allowClear
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            placeholder="搜尋文件路徑"
          />
          <Select
            mode="multiple"
            allowClear
            value={tagFilters}
            onChange={setTagFilters}
            options={allTags.map((tag) => ({ label: tag, value: tag }))}
            placeholder="依標籤篩選"
            maxTagCount="responsive"
          />
          <Button
            icon={<ReloadOutlined />}
            loading={loading}
            onClick={loadDocuments}
          >
            重新整理
          </Button>
        </div>

        {loading ? (
          <CardLoading label="文件列表讀取中" />
        ) : (
          <Table<DocumentInfo>
            rowKey="path"
            dataSource={filteredDocuments}
            pagination={{
              pageSize: 10,
              showSizeChanger: false,
              showTotal: (total) => `共 ${total} 份文件`,
            }}
            locale={{
              emptyText: (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="目前沒有符合條件的文件"
                />
              ),
            }}
            scroll={{ x: 920 }}
            columns={[
              {
                title: "路徑",
                dataIndex: "path",
                key: "path",
                ellipsis: true,
              },
              {
                title: "標籤",
                dataIndex: "tags",
                key: "tags",
                render: (tags: string[]) => (
                  <Space size={[4, 4]} wrap>
                    {uniqueTags(tags).map((tag) => (
                      <Tag key={tag}>{tag}</Tag>
                    ))}
                  </Space>
                ),
              },
              {
                title: "Chunks",
                dataIndex: "chunk_count",
                key: "chunk_count",
                width: 90,
                align: "right",
              },
              {
                title: "檔案大小",
                dataIndex: "file_size_bytes",
                key: "file_size_bytes",
                width: 110,
                render: formatBytes,
              },
              {
                title: "最後更新時間",
                dataIndex: "uploaded_at",
                key: "uploaded_at",
                width: 190,
                render: formatUploadedAt,
              },
              {
                title: "操作",
                key: "action",
                width: 86,
                fixed: "right",
                render: (_, doc) => (
                  <Popconfirm
                    title="刪除文件"
                    description={`確定要刪除「${doc.path}」嗎？此操作無法復原。`}
                    okText="刪除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                    onConfirm={() => handleDelete(doc.path)}
                  >
                    <Button type="text" danger icon={<DeleteOutlined />}>
                      刪除
                    </Button>
                  </Popconfirm>
                ),
              },
            ]}
          />
        )}
      </Card>
    </AdminPageLayout>
  );
}
