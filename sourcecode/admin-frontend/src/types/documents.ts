export interface DocumentInfo {
  path: string;
  tags: string[];
  chunk_count: number;
  content_changed: boolean | null;
  uploaded_at: string | null;
  file_size_bytes: number | null;
  content_hash?: string | null;
}

export type PrecheckStatus =
  "new" | "unchanged" | "content_changed" | "tags_only_changed" | "linked";

export interface PrecheckRequestItem {
  path: string;
  client_sha256: string;
  tags: string[];
}

export interface PrecheckResultItem {
  path: string;
  status: PrecheckStatus;
}

export interface PrecheckResponse {
  items: PrecheckResultItem[];
  stale_paths: string[];
}
