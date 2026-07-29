"use client";

import * as React from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Download,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useMigrations } from "@/hooks/use-migration";
import { downloadMigration } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import type { MigrationSummary, MigrationStage } from "@/types/migration";

// ── Stage badge config ────────────────────────────────────────────────────

const STAGE_BADGE: Record<
  MigrationStage,
  { label: string; className: string }
> = {
  uploaded:  { label: "Uploaded",   className: "bg-blue-500/15 text-blue-600 dark:text-blue-400" },
  parsed:    { label: "Parsed",     className: "bg-violet-500/15 text-violet-600 dark:text-violet-400" },
  analyzed:  { label: "Analyzed",   className: "bg-purple-500/15 text-purple-600 dark:text-purple-400" },
  embedded:  { label: "Embedded",   className: "bg-indigo-500/15 text-indigo-600 dark:text-indigo-400" },
  retrieved: { label: "Retrieved",  className: "bg-cyan-500/15 text-cyan-600 dark:text-cyan-400" },
  migrated:  { label: "Migrated",   className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400" },
  compiled:  { label: "Compiled",   className: "bg-teal-500/15 text-teal-600 dark:text-teal-400" },
  saved:     { label: "Completed",  className: "bg-green-500/15 text-green-600 dark:text-green-400" },
  failed:    { label: "Failed",     className: "bg-destructive/15 text-destructive" },
};

// ── Row component ─────────────────────────────────────────────────────────

function HistoryRow({ migration }: { migration: MigrationSummary }) {
  const stage = migration.current_stage as MigrationStage;
  const cfg = STAGE_BADGE[stage] ?? STAGE_BADGE.uploaded;
  const isComplete = migration.is_complete;
  const isFailed = migration.is_failed;

  function handleDownload() {
    downloadMigration(migration.migration_id);
    toast.success("Download started", `Downloading ${migration.project_name} project ZIP.`);
  }

  return (
    <div className="flex items-center gap-4 px-5 py-4 hover:bg-muted/30 transition-colors">
      {/* Icon */}
      <div className="shrink-0 flex h-9 w-9 items-center justify-center rounded-full bg-muted">
        {isComplete ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        ) : isFailed ? (
          <AlertCircle className="h-4 w-4 text-destructive" />
        ) : (
          <Loader2 className="h-4 w-4 text-muted-foreground animate-spin" />
        )}
      </div>

      {/* Project name + ID */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold truncate">{migration.project_name}</p>
        <p className="text-xs text-muted-foreground font-mono mt-0.5 truncate">
          {migration.migration_id}
        </p>
      </div>

      {/* Date */}
      <div className="hidden sm:flex items-center gap-1.5 text-xs text-muted-foreground shrink-0">
        <Clock className="h-3.5 w-3.5" />
        <span>{formatDate(migration.created_at)}</span>
      </div>

      {/* Files */}
      <div className="hidden md:block text-xs text-muted-foreground shrink-0 w-16 text-right">
        {migration.file_count} file{migration.file_count !== 1 ? "s" : ""}
      </div>

      {/* Status badge */}
      <Badge className={`text-xs font-medium shrink-0 ${cfg.className}`}>
        {cfg.label}
      </Badge>

      {/* Download button */}
      <Button
        size="sm"
        variant="outline"
        onClick={handleDownload}
        disabled={!isComplete}
        className="gap-1.5 shrink-0"
        aria-label={`Download ${migration.project_name}`}
        id={`download-${migration.migration_id}`}
        title={isComplete ? "Download generated Java project" : "Migration must complete before downloading"}
      >
        <Download className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">Download</span>
      </Button>
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function HistoryPage() {
  const { data, isLoading, isError, refetch, isFetching } = useMigrations();

  const migrations = data?.migrations ?? [];
  const total = data?.total ?? 0;

  // Auto-refresh every 5 s if any migration is still running
  const hasRunning = migrations.some(
    (m) => !m.is_complete && !m.is_failed,
  );

  React.useEffect(() => {
    if (!hasRunning) return;
    const timer = setInterval(() => refetch(), 5000);
    return () => clearInterval(timer);
  }, [hasRunning, refetch]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight">History</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Past migrations, audit logs, and downloadable outputs
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          className="gap-2"
          aria-label="Refresh history"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="rounded-xl border border-border bg-card divide-y divide-border/50 overflow-hidden">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-5 py-4 animate-pulse">
              <div className="h-9 w-9 rounded-full bg-muted shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="h-3.5 w-40 rounded bg-muted" />
                <div className="h-2.5 w-64 rounded bg-muted" />
              </div>
              <div className="h-5 w-20 rounded-full bg-muted shrink-0" />
              <div className="h-7 w-24 rounded-md bg-muted shrink-0" />
            </div>
          ))}
        </div>
      )}

      {/* Error state */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-destructive/30 bg-destructive/5 py-14 text-center gap-3">
          <AlertCircle className="h-8 w-8 text-destructive/60" />
          <p className="text-sm font-medium text-destructive">Failed to load migration history</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Try again
          </Button>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && total === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card py-20 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted mb-4">
            <Clock className="h-6 w-6 text-muted-foreground" />
          </div>
          <h2 className="text-base font-semibold">No history yet</h2>
          <p className="mt-1.5 text-sm text-muted-foreground max-w-xs">
            Completed migrations will appear here with full logs, timings, and downloadable outputs.
          </p>
          <Badge variant="secondary" className="mt-4 text-xs">
            History available after first migration
          </Badge>
        </div>
      )}

      {/* Migration list */}
      {!isLoading && !isError && migrations.length > 0 && (
        <>
          {/* Summary row */}
          <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
            <span>
              {total} migration{total !== 1 ? "s" : ""}
              {hasRunning && (
                <span className="ml-2 inline-flex items-center gap-1 text-amber-500">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  {migrations.filter((m) => !m.is_complete && !m.is_failed).length} running
                </span>
              )}
            </span>
            <span>
              {migrations.filter((m) => m.is_complete).length} completed •{" "}
              {migrations.filter((m) => m.is_failed).length} failed
            </span>
          </div>

          {/* Table */}
          <div className="rounded-xl border border-border bg-card divide-y divide-border/50 overflow-hidden">
            {/* Header */}
            <div className="hidden sm:flex items-center gap-4 px-5 py-2.5 bg-muted/50 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              <div className="h-9 w-9 shrink-0" />
              <div className="flex-1">Project</div>
              <div className="hidden sm:block w-28 shrink-0">Date</div>
              <div className="hidden md:block w-16 text-right shrink-0">Files</div>
              <div className="w-20 shrink-0">Status</div>
              <div className="w-24 shrink-0 text-right">Download</div>
            </div>

            {migrations.map((m) => (
              <HistoryRow key={m.migration_id} migration={m} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
