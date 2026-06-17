"use client";

import * as React from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  FileCode2,
  FolderOpen,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { Migration, MigrationStage, MigrationStatus } from "@/types/migration";

// ── Stage config ──────────────────────────────────────────────────────────

const STAGE_CONFIG: Record<
  MigrationStage,
  { label: string; colorClass: string; badgeClass: string }
> = {
  uploaded:  { label: "Uploaded",   colorClass: "text-blue-500",    badgeClass: "bg-blue-500/15 text-blue-600 dark:text-blue-400" },
  parsed:    { label: "Parsed",     colorClass: "text-violet-500",  badgeClass: "bg-violet-500/15 text-violet-600 dark:text-violet-400" },
  analyzed:  { label: "Analyzed",   colorClass: "text-purple-500",  badgeClass: "bg-purple-500/15 text-purple-600 dark:text-purple-400" },
  embedded:  { label: "Embedded",   colorClass: "text-indigo-500",  badgeClass: "bg-indigo-500/15 text-indigo-600 dark:text-indigo-400" },
  retrieved: { label: "Retrieved",  colorClass: "text-cyan-500",    badgeClass: "bg-cyan-500/15 text-cyan-600 dark:text-cyan-400" },
  migrated:  { label: "Migrated",   colorClass: "text-emerald-500", badgeClass: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400" },
  compiled:  { label: "Compiled",   colorClass: "text-teal-500",    badgeClass: "bg-teal-500/15 text-teal-600 dark:text-teal-400" },
  saved:     { label: "Completed",  colorClass: "text-green-500",   badgeClass: "bg-green-500/15 text-green-600 dark:text-green-400" },
  failed:    { label: "Failed",     colorClass: "text-destructive", badgeClass: "bg-destructive/15 text-destructive" },
};

// ── Progress bar ──────────────────────────────────────────────────────────

function ProgressBar({ pct, failed }: { pct: number; failed: boolean }) {
  return (
    <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
      <div
        className={cn(
          "h-full rounded-full transition-all duration-500",
          failed ? "bg-destructive" : "bg-primary",
        )}
        style={{ width: `${pct}%` }}
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Migration progress: ${pct}%`}
      />
    </div>
  );
}

// ── Props ─────────────────────────────────────────────────────────────────

interface MigrationStatusPanelProps {
  migration: Migration | null | undefined;
  status: MigrationStatus | null | undefined;
  isLoading?: boolean;
  onRefresh?: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────

export function MigrationStatusPanel({
  migration,
  status,
  isLoading,
  onRefresh,
}: MigrationStatusPanelProps) {
  if (isLoading) return <MigrationStatusSkeleton />;

  if (!migration) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-card p-6 text-center space-y-2">
        <AlertCircle className="mx-auto h-8 w-8 text-muted-foreground/40" />
        <p className="text-sm font-medium text-muted-foreground">
          No migration selected
        </p>
        <p className="text-xs text-muted-foreground/60">
          Create a migration and upload files to get started
        </p>
      </div>
    );
  }

  const stage = migration.current_stage;
  const cfg = STAGE_CONFIG[stage];
  const pct = status?.progress_pct ?? 0;
  const isFailed = migration.current_stage === "failed";
  const isComplete = migration.current_stage === "saved";

  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-4">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-1">
            Migration Status
          </p>
          <h3 className="text-sm font-semibold truncate">{migration.project_name}</h3>
          <p className="text-xs text-muted-foreground font-mono truncate mt-0.5">
            {migration.migration_id.slice(0, 8)}…
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge className={cn("text-xs font-medium", cfg.badgeClass)}>
            {isFailed && <AlertCircle className="h-3 w-3 mr-1" />}
            {isComplete && <CheckCircle2 className="h-3 w-3 mr-1" />}
            {!isFailed && !isComplete && (
              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
            )}
            {cfg.label}
          </Badge>
          {onRefresh && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={onRefresh}
              aria-label="Refresh status"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* Progress */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Progress</span>
          <span className="tabular-nums font-medium">{pct}%</span>
        </div>
        <ProgressBar pct={pct} failed={isFailed} />
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-2">
        <StatCell
          icon={<FileCode2 className="h-3.5 w-3.5 text-blue-500" />}
          label="Files Uploaded"
          value={String(migration.uploaded_files.length)}
        />
        <StatCell
          icon={<FolderOpen className="h-3.5 w-3.5 text-violet-500" />}
          label="Files Generated"
          value={String(migration.generated_java_files.length)}
        />
        <StatCell
          icon={<Clock className="h-3.5 w-3.5 text-muted-foreground" />}
          label="Created"
          value={formatTime(migration.created_at)}
        />
        <StatCell
          icon={<RefreshCw className="h-3.5 w-3.5 text-muted-foreground" />}
          label="Updated"
          value={formatTime(migration.updated_at)}
        />
      </div>

      {/* Completed stages */}
      {migration.completed_stages.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs text-muted-foreground font-medium">
            Completed stages
          </p>
          <div className="flex flex-wrap gap-1">
            {migration.completed_stages.map((s) => (
              <Badge
                key={s}
                className="text-[10px] px-1.5 py-0 h-5 bg-muted text-muted-foreground"
              >
                <CheckCircle2 className="h-2.5 w-2.5 mr-1 text-emerald-500" />
                {STAGE_CONFIG[s]?.label ?? s}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Errors */}
      {migration.errors.length > 0 && (
        <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 space-y-1">
          <p className="text-xs font-medium text-destructive flex items-center gap-1">
            <AlertCircle className="h-3 w-3" /> Errors
          </p>
          {migration.errors.slice(-3).map((err, i) => (
            <p key={i} className="text-xs text-destructive/80 font-mono break-all">
              {err}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Helper sub-components ─────────────────────────────────────────────────

function StatCell({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg bg-muted/40 px-3 py-2 space-y-0.5">
      <div className="flex items-center gap-1.5">
        {icon}
        <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">
          {label}
        </p>
      </div>
      <p className="text-sm font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "—";
  }
}

export function MigrationStatusSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-4">
      <div className="flex items-start justify-between">
        <div className="space-y-1.5">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-24" />
        </div>
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <Skeleton className="h-1.5 w-full rounded-full" />
      <div className="grid grid-cols-2 gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-14 rounded-lg" />
        ))}
      </div>
    </div>
  );
}
