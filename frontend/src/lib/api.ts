/**
 * Typed API client for Code Migration Agent backend.
 * All methods use Axios with proper error handling and response typing.
 */

import axios, { AxiosError, type AxiosInstance } from "axios";
import type {
  ApiError,
  CreateMigrationRequest,
  CreateMigrationResponse,
  ListFilesResponse,
  ListMigrationsResponse,
  Migration,
  MigrationStatus,
  RunWorkflowResponse,
  UploadResponse,
} from "@/types/migration";

// ── Axios instance ────────────────────────────────────────────────────────

function getApiBaseUrl(): string {
  if (
    process.env.NEXT_PUBLIC_API_URL &&
    !process.env.NEXT_PUBLIC_API_URL.includes("localhost")
  ) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    return `${protocol}//${hostname}:8000`;
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

const httpClient: AxiosInstance = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

httpClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    config.baseURL = getApiBaseUrl();
  }
  return config;
});

// ── Error normalisation ───────────────────────────────────────────────────

export class ApiClientError extends Error {
  readonly status: number;
  readonly payload: ApiError;

  constructor(status: number, payload: ApiError) {
    super(payload.message ?? "API request failed");
    this.status = status;
    this.payload = payload;
    this.name = "ApiClientError";
  }
}

function handleAxiosError(err: unknown): never {
  if (err instanceof AxiosError) {
    const status = err.response?.status ?? 0;
    const data = err.response?.data as ApiError | undefined;
    throw new ApiClientError(status, {
      error: data?.error ?? "NetworkError",
      message:
        data?.message ?? err.message ?? "An unexpected network error occurred.",
      details: data?.details,
      migration_id: data?.migration_id,
    });
  }
  throw err;
}

// ── Migrations ────────────────────────────────────────────────────────────

export async function createMigration(
  body: CreateMigrationRequest,
): Promise<CreateMigrationResponse> {
  try {
    const { data } = await httpClient.post<CreateMigrationResponse>(
      "/api/migrations",
      body,
    );
    return data;
  } catch (err) {
    handleAxiosError(err);
  }
}

export async function listMigrations(): Promise<ListMigrationsResponse> {
  try {
    const { data } = await httpClient.get<ListMigrationsResponse>(
      "/api/migrations",
    );
    return data;
  } catch (err) {
    handleAxiosError(err);
  }
}

export async function getMigration(migrationId: string): Promise<Migration> {
  try {
    const { data } = await httpClient.get<Migration>(
      `/api/migrations/${migrationId}`,
    );
    return data;
  } catch (err) {
    handleAxiosError(err);
  }
}

export async function deleteMigration(migrationId: string): Promise<void> {
  try {
    await httpClient.delete(`/api/migrations/${migrationId}`);
  } catch (err) {
    handleAxiosError(err);
  }
}

// ── File upload ───────────────────────────────────────────────────────────

export async function uploadFiles(
  migrationId: string,
  files: File[],
  onProgress?: (pct: number) => void,
): Promise<UploadResponse> {
  try {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));

    const { data } = await httpClient.post<UploadResponse>(
      `/api/migrations/${migrationId}/upload`,
      form,
      {
        // DO NOT set Content-Type manually here.
        // Axios auto-sets 'multipart/form-data; boundary=...' when it detects FormData.
        // Setting it manually omits the boundary, causing the server to reject with 422.
        headers: { "Content-Type": undefined },
        onUploadProgress: (evt) => {
          if (evt.total && onProgress) {
            onProgress(Math.round((evt.loaded / evt.total) * 100));
          }
        },
      },
    );
    return data;
  } catch (err) {
    handleAxiosError(err);
  }
}

export async function listProjectFiles(
  migrationId: string,
): Promise<ListFilesResponse> {
  try {
    const { data } = await httpClient.get<ListFilesResponse>(
      `/api/migrations/${migrationId}/files`,
    );
    return data;
  } catch (err) {
    handleAxiosError(err);
  }
}

export async function deleteProjectFiles(
  migrationId: string,
): Promise<void> {
  try {
    await httpClient.delete(`/api/migrations/${migrationId}/files`);
  } catch (err) {
    handleAxiosError(err);
  }
}

// ── Workflow ──────────────────────────────────────────────────────────────

export async function runMigration(
  migrationId: string,
): Promise<RunWorkflowResponse> {
  try {
    const { data } = await httpClient.post<RunWorkflowResponse>(
      `/api/migrations/${migrationId}/run`,
    );
    return data;
  } catch (err) {
    handleAxiosError(err);
  }
}

export async function getMigrationStatus(
  migrationId: string,
): Promise<MigrationStatus> {
  try {
    const { data } = await httpClient.get<MigrationStatus>(
      `/api/migrations/${migrationId}/status`,
    );
    return data;
  } catch (err) {
    handleAxiosError(err);
  }
}

// ── Download ──────────────────────────────────────────────────────────────

/**
 * Trigger a browser download of all generated Java files for a migration.
 * Opens the backend download URL directly so the browser handles the
 * file-save dialog natively (backend returns a ZIP with Content-Disposition).
 */
export function downloadMigration(migrationId: string): void {
  const url = `${getApiBaseUrl()}/api/migrations/${migrationId}/download`;
  const a = document.createElement("a");
  a.href = url;
  a.download = ""; // let Content-Disposition filename take precedence
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// ── Health ────────────────────────────────────────────────────────────────

export async function getHealthStatus(): Promise<{
  status: string;
  version: string;
  environment: string;
}> {
  try {
    const { data } = await httpClient.get("/health");
    return data;
  } catch (err) {
    handleAxiosError(err);
  }
}
