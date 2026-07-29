"use client";

import * as React from "react";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  FileCode2,
  FolderOpen,
  Gauge,
  Loader2,
  Play,
  Plus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { UploadCard } from "@/components/upload-card";
import { PipelineView } from "@/components/pipeline-view";
import { LogPanel } from "@/components/log-panel";
import { StatsCard, StatsCardSkeleton } from "@/components/stats-card";
import { MigrationStatusPanel } from "@/components/migration-status";
import {
  useCreateMigration,
  useDownloadMigration,
  useMigration,
  useMigrationStatus,
  useRunMigration,
} from "@/hooks/use-migration";
import { ApiClientError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// ── localStorage key ──────────────────────────────────────────────────────

const LS_KEY = "migration_agent:active_migration_id";

function readStoredId(): string | null {
  try {
    return typeof window !== "undefined"
      ? window.localStorage.getItem(LS_KEY)
      : null;
  } catch {
    return null;
  }
}

function writeStoredId(id: string | null): void {
  try {
    if (typeof window === "undefined") return;
    if (id) {
      window.localStorage.setItem(LS_KEY, id);
    } else {
      window.localStorage.removeItem(LS_KEY);
    }
  } catch {
    /* storage unavailable — silent fail */
  }
}

// ── Create migration modal / inline form ──────────────────────────────────

function CreateMigrationForm({
  onCreated,
}: {
  onCreated: (id: string) => void;
}) {
  const [name, setName] = React.useState("");
  const { mutateAsync, isPending } = useCreateMigration();

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    try {
      const result = await mutateAsync({ project_name: trimmed });
      setName("");
      onCreated(result.migration_id);
      toast.success("Migration created", `Project: ${trimmed}`);
    } catch (err) {
      const msg =
        err instanceof ApiClientError
          ? err.payload.message
          : "Failed to create migration.";
      toast.error("Creation failed", msg);
    }
  }

  return (
    <form onSubmit={handleCreate} className="flex items-center gap-2">
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Project name, e.g. EcommerceApp"
        aria-label="Project name"
        className="flex h-8 flex-1 min-w-0 rounded-lg border border-input bg-background px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/50"
        maxLength={200}
        disabled={isPending}
      />
      <Button
        type="submit"
        size="sm"
        disabled={!name.trim() || isPending}
        className="gap-1.5 shrink-0"
      >
        {isPending ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Plus className="h-3.5 w-3.5" />
        )}
        Create
      </Button>
    </form>
  );
}

// ── Main dashboard ────────────────────────────────────────────────────────

export default function DashboardPage() {
  // ── Active migration ID ──────────────────────────────────────────────────
  //
  // HYDRATION SAFETY: Initialize to null on both server and client so the
  // first render always matches. Then, in a useEffect (client-only), restore
  // the stored ID from localStorage. This eliminates the SSR/client mismatch
  // that causes React hydration warnings.
  const [activeMigrationId, setActiveMigrationIdRaw] = React.useState<
    string | null
  >(null);

  // After the component mounts on the client, restore any stored migration ID.
  React.useEffect(() => {
    const stored = readStoredId();
    if (stored) {
      setActiveMigrationIdRaw(stored);
    }
  }, []);

  // Keep localStorage in sync with component state
  const setActiveMigrationId = React.useCallback(
    (id: string | null) => {
      setActiveMigrationIdRaw(id);
      writeStoredId(id);
    },
    [],
  );

  // ── Data queries (these automatically start polling when ID is present) ──
  const {
    data: migration,
    isLoading: migrationLoading,
    refetch: refetchMigration,
    isError: migrationError,
  } = useMigration(activeMigrationId);

  const {
    data: status,
    refetch: refetchStatus,
  } = useMigrationStatus(activeMigrationId);

  // ── Download ─────────────────────────────────────────────────────────────
  const { download, canDownload } = useDownloadMigration(activeMigrationId);

  // ── Run workflow mutation ────────────────────────────────────────────────
  const { mutateAsync: runWorkflow, isPending: isRunning } =
    useRunMigration(activeMigrationId);

  // If the stored ID no longer exists on the backend (e.g. backend restarted),
  // clear it so the "Create migration" form shows up instead of an error loop.
  React.useEffect(() => {
    if (activeMigrationId && migrationError) {
      writeStoredId(null);
      setActiveMigrationIdRaw(null);
    }
  }, [activeMigrationId, migrationError]);

  // ── Derived values ───────────────────────────────────────────────────────

  const isTerminal =
    migration?.current_stage === "saved" ||
    migration?.current_stage === "failed";

  const canRun =
    !!activeMigrationId &&
    !isRunning &&
    !migrationLoading &&
    (migration?.uploaded_files.length ?? 0) > 0 &&
    !isTerminal;

  // Stats derived from real migration data
  const stats = React.useMemo(
    () => [
      {
        label: "Files Uploaded",
        value: String(migration?.uploaded_files.length ?? 0),
        sublabel: migration ? `${migration.project_name}` : "No migration",
        icon: FileCode2,
        colorClass: "text-blue-500 bg-blue-500/10",
      },
      {
        label: "Files Generated",
        value: String(migration?.generated_java_files.length ?? 0),
        sublabel: "Java output files",
        icon: FolderOpen,
        colorClass: "text-violet-500 bg-violet-500/10",
      },
      {
        label: "Pipeline Stage",
        value: migration?.current_stage ?? "idle",
        sublabel: status
          ? `${status.progress_pct}% complete`
          : "Awaiting run",
        icon: AlertCircle,
        colorClass: "text-emerald-500 bg-emerald-500/10",
      },
      {
        label: "Status",
        value: migration
          ? isTerminal
            ? migration.current_stage === "saved"
              ? "Complete"
              : "Failed"
            : isRunning
              ? "Running"
              : "Ready"
          : "Idle",
        sublabel: migration
          ? `ID: ${migration.migration_id.slice(0, 8)}…`
          : "No active migration",
        icon: Gauge,
        colorClass: "text-amber-500 bg-amber-500/10",
      },
    ],
    [migration, status, isRunning, isTerminal],
  );

  // ── Handlers ─────────────────────────────────────────────────────────────

  async function handleRunWorkflow() {
    try {
      const result = await runWorkflow();
      await Promise.all([refetchMigration(), refetchStatus()]);
      if (result.is_complete) {
        toast.success("Migration complete!", "All 8 pipeline stages finished.");
      } else if (result.is_failed) {
        toast.error("Migration failed", `Stopped at: ${result.stage}`);
      }
    } catch (err) {
      const msg =
        err instanceof ApiClientError
          ? err.payload.message
          : "Failed to run workflow.";
      toast.error("Workflow error", msg);
    }
  }

  function handleRefresh() {
    refetchMigration();
    refetchStatus();
  }

  function handleDownload() {
    download();
    toast.success("Download started", "Your Java project ZIP is downloading.");
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Dashboard</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Create a migration, upload your .NET project, and run the pipeline
          </p>
        </div>
        {migration && !isTerminal ? (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            Migration active
          </div>
        ) : migration && isTerminal ? (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {migration.current_stage === "saved" ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            ) : (
              <AlertCircle className="h-3.5 w-3.5 text-destructive" />
            )}
            {migration.current_stage === "saved" ? "Completed" : "Failed"}
          </div>
        ) : null}
      </div>

      {/* Create Migration Form */}
      {!activeMigrationId && (
        <div className="rounded-xl border border-dashed border-primary/30 bg-primary/5 p-5">
          <p className="text-sm font-medium mb-3">
            Start by creating a new migration:
          </p>
          <CreateMigrationForm onCreated={setActiveMigrationId} />
        </div>
      )}

      {/* Active migration ID bar */}
      {activeMigrationId && (
        <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-muted/30 px-4 py-2.5">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-xs text-muted-foreground shrink-0">
              Active migration:
            </span>
            <code className="text-xs font-mono text-foreground truncate">
              {activeMigrationId}
            </code>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {/* Download button — shown only when migration is complete with output */}
            {canDownload && (
              <Button
                size="sm"
                variant="default"
                onClick={handleDownload}
                className="gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white"
                aria-label="Download generated Java project"
                id="download-migration-btn"
              >
                <Download className="h-3.5 w-3.5" />
                {(migration?.generated_java_files.length ?? 0) === 1
                  ? "Download Java File"
                  : "Download Generated Project"}
              </Button>
            )}

            {/* Run workflow button */}
            <Button
              size="sm"
              disabled={!canRun}
              onClick={handleRunWorkflow}
              className="gap-1.5"
              aria-label="Run migration workflow"
            >
              {isRunning ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Running…
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5" />
                  Run Migration
                </>
              )}
            </Button>

            {/* Start new migration */}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setActiveMigrationId(null)}
              className="gap-1.5"
            >
              <Plus className="h-3.5 w-3.5" />
              New
            </Button>
          </div>
        </div>
      )}

      {/* Stats row */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {migrationLoading
          ? Array.from({ length: 4 }).map((_, i) => (
              <StatsCardSkeleton key={i} />
            ))
          : stats.map((s) => (
              <StatsCard
                key={s.label}
                label={s.label}
                value={s.value}
                sublabel={s.sublabel}
                icon={s.icon}
                colorClass={s.colorClass}
              />
            ))}
      </div>

      {/* Status panel + Upload — side by side on lg+ */}
      <div className="grid gap-4 lg:grid-cols-2">
        <MigrationStatusPanel
          migration={migration}
          status={status}
          isLoading={migrationLoading && !!activeMigrationId}
          onRefresh={handleRefresh}
        />
        <UploadCard
          migrationId={activeMigrationId}
          onUploaded={() => refetchMigration()}
        />
      </div>

      {/* Logs */}
      <LogPanel
        logs={migration?.logs}
        onRefresh={handleRefresh}
        isLive={isRunning || (!!activeMigrationId && !isTerminal && !!migration)}
      />

      {/* Pipeline visualisation */}
      <PipelineView
        currentStage={migration?.current_stage}
        completedStages={migration?.completed_stages ?? []}
        isFailed={migration?.current_stage === "failed"}
      />
    </div>
  );
}
