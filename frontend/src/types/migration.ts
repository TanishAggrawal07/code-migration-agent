/**
 * TypeScript types for the Code Migration Agent API.
 * These mirror the Pydantic models in the backend exactly.
 */

// ── Enums ─────────────────────────────────────────────────────────────────

export type MigrationStage =
  | "uploaded"
  | "parsed"
  | "analyzed"
  | "embedded"
  | "retrieved"
  | "migrated"
  | "compiled"
  | "saved"
  | "failed";

export type LogLevel = "DEBUG" | "INFO" | "SUCCESS" | "WARNING" | "ERROR";

// ── Sub-models ────────────────────────────────────────────────────────────

export interface LogEntry {
  level: LogLevel;
  message: string;
  stage: MigrationStage | null;
  timestamp: string;          // ISO-8601
  agent: string | null;
}

export interface ParsedFile {
  filename: string;
  path: string;
  classes: string[];
  methods: string[];
  lines: number;
  parsed: boolean;
}

export interface GeneratedFile {
  filename: string;
  path: string;
  source_file: string;
  compile_success: boolean;
  content_preview: string;
}

// ── Primary migration state ───────────────────────────────────────────────

export interface Migration {
  migration_id: string;
  project_name: string;

  // File tracking
  uploaded_files: string[];
  project_root: string;
  last_upload_time: string | null;  // ISO-8601

  // Pipeline stages
  parsed_files: ParsedFile[];
  chunks: string[];
  embeddings_created: boolean;
  embedding_count: number;
  retrieved_context: string[];
  generated_java_files: GeneratedFile[];

  // Compile
  compile_status: "pending" | "success" | "failed" | "skipped";
  compile_errors: string[];

  // Error / log tracking
  errors: string[];
  logs: LogEntry[];

  // Progress
  current_stage: MigrationStage;
  completed_stages: MigrationStage[];

  // Metadata
  created_at: string;   // ISO-8601
  updated_at: string;   // ISO-8601

  // Extra context (arbitrary)
  context: Record<string, unknown>;
}

// ── Pipeline status response ──────────────────────────────────────────────

export interface MigrationStatus {
  migration_id: string;
  current_stage: MigrationStage;
  completed: MigrationStage[];
  remaining: MigrationStage[];
  progress_pct: number;        // 0–100
  is_failed: boolean;
  is_complete: boolean;
  file_count: number;
  generated_count: number;
  log_count: number;
}

// ── API request/response shapes ───────────────────────────────────────────

export interface CreateMigrationRequest {
  project_name: string;
  uploaded_files?: string[];
}

export interface CreateMigrationResponse {
  migration_id: string;
  project_name: string;
  status: string;
  message: string;
}

export interface UploadResponse {
  migration_id: string;
  project_name: string;
  uploaded_count: number;
  uploaded_files: string[];
  project_root: string;
  message: string;
}

export interface RunWorkflowResponse {
  migration_id: string;
  stage: MigrationStage;
  is_complete: boolean;
  is_failed: boolean;
  message: string;
}

export interface ListFilesResponse {
  migration_id: string;
  file_count: number;
  files: string[];
}

export interface MigrationSummary {
  migration_id: string;
  project_name: string;
  current_stage: MigrationStage;
  is_failed: boolean;
  is_complete: boolean;
  file_count: number;
  project_root: string;
  last_upload_time: string | null;
  created_at: string;
  updated_at: string;
}

export interface ListMigrationsResponse {
  total: number;
  migrations: MigrationSummary[];
}

// ── Error ─────────────────────────────────────────────────────────────────

export interface ApiError {
  error: string;
  message: string;
  details?: unknown;
  migration_id?: string;
}
