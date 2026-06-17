"use client";

import * as React from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  createMigration,
  deleteMigration,
  getMigration,
  getMigrationStatus,
  listMigrations,
  runMigration,
  uploadFiles,
} from "@/lib/api";
import { queryKeys } from "@/lib/query-client";
import type {
  CreateMigrationRequest,
  MigrationStage,
} from "@/types/migration";

// ── List ──────────────────────────────────────────────────────────────────

export function useMigrations() {
  return useQuery({
    queryKey: queryKeys.migrations.list(),
    queryFn: listMigrations,
  });
}

// ── Single migration detail ───────────────────────────────────────────────

export function useMigration(migrationId: string | null) {
  return useQuery({
    queryKey: queryKeys.migrations.detail(migrationId ?? ""),
    queryFn: () => getMigration(migrationId!),
    enabled: !!migrationId,
  });
}

// ── Pipeline status — with live polling ───────────────────────────────────

const TERMINAL_STAGES: MigrationStage[] = ["saved", "failed"];

export function useMigrationStatus(
  migrationId: string | null,
  pollIntervalMs = 3000,
) {
  const query = useQuery({
    queryKey: queryKeys.migrations.status(migrationId ?? ""),
    queryFn: () => getMigrationStatus(migrationId!),
    enabled: !!migrationId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return pollIntervalMs;
      // Stop polling once the pipeline reaches a terminal state
      if (TERMINAL_STAGES.includes(data.current_stage)) return false;
      return pollIntervalMs;
    },
  });
  return query;
}

// ── Create ────────────────────────────────────────────────────────────────

export function useCreateMigration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateMigrationRequest) => createMigration(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.migrations.list() });
    },
  });
}

// ── Delete ────────────────────────────────────────────────────────────────

export function useDeleteMigration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (migrationId: string) => deleteMigration(migrationId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.migrations.list() });
    },
  });
}

// ── Upload ────────────────────────────────────────────────────────────────

export function useUploadFiles(migrationId: string | null) {
  const qc = useQueryClient();
  const [uploadProgress, setUploadProgress] = React.useState(0);

  const mutation = useMutation({
    mutationFn: (files: File[]) => {
      if (!migrationId) throw new Error("No migration selected");
      setUploadProgress(0);
      return uploadFiles(migrationId, files, setUploadProgress);
    },
    onSuccess: () => {
      if (migrationId) {
        qc.invalidateQueries({
          queryKey: queryKeys.migrations.detail(migrationId),
        });
        qc.invalidateQueries({
          queryKey: queryKeys.migrations.files(migrationId),
        });
      }
      setUploadProgress(0);
    },
    onError: () => setUploadProgress(0),
  });

  return { ...mutation, uploadProgress };
}

// ── Run workflow ──────────────────────────────────────────────────────────

export function useRunMigration(migrationId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => {
      if (!migrationId) throw new Error("No migration selected");
      return runMigration(migrationId);
    },
    onSuccess: () => {
      if (migrationId) {
        // Immediately re-fetch detail + status
        qc.invalidateQueries({
          queryKey: queryKeys.migrations.detail(migrationId),
        });
        qc.invalidateQueries({
          queryKey: queryKeys.migrations.status(migrationId),
        });
      }
    },
  });
}
