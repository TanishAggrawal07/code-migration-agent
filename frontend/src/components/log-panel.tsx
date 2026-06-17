"use client";

import * as React from "react";
import { RefreshCw, Terminal, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import type { LogLevel } from "@/types/migration";

// Keep LogEntry available for the props type
import type { LogEntry } from "@/types/migration";

// ── Styles ────────────────────────────────────────────────────────────────

const LEVEL_STYLES: Record<LogLevel, string> = {
  INFO:    "text-blue-400",
  SUCCESS: "text-emerald-400",
  WARNING: "text-yellow-400",
  ERROR:   "text-red-400",
  DEBUG:   "text-slate-500",
};

const LEVEL_WIDTH: Record<LogLevel, string> = {
  INFO:    "w-[52px]",
  SUCCESS: "w-[68px]",
  WARNING: "w-[68px]",
  ERROR:   "w-[52px]",
  DEBUG:   "w-[52px]",
};

// ── Props ─────────────────────────────────────────────────────────────────

interface LogPanelProps {
  /** Real log entries from the backend. When null/undefined shows placeholder. */
  logs?: LogEntry[] | null;
  /** Called when the user clicks the refresh button */
  onRefresh?: () => void;
  /** Show a pulsing "live" indicator */
  isLive?: boolean;
}

// ── Helpers ───────────────────────────────────────────────────────────────

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

// ── Component ─────────────────────────────────────────────────────────────

export function LogPanel({ logs, onRefresh, isLive = false }: LogPanelProps) {
  const [clearedAt, setClearedAt] = React.useState<number | null>(null);
  const bottomRef = React.useRef<HTMLDivElement>(null);

  // Display logs: real logs from props (filtered by clear), or empty
  const displayLogs = React.useMemo(() => {
    if (!logs || logs.length === 0) return [];
    if (clearedAt === null) return logs;
    // Show only entries added after the user cleared
    return logs.filter(
      (l) => new Date(l.timestamp).getTime() > clearedAt,
    );
  }, [logs, clearedAt]);

  // Auto-scroll when new entries arrive
  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [displayLogs.length]);

  const clearLogs = () => setClearedAt(Date.now());

  const levelCounts = React.useMemo(
    () => ({
      errors: displayLogs.filter(
        (l) => l.level === "ERROR",
      ).length,
      warns: displayLogs.filter(
        (l) => l.level === "WARNING",
      ).length,
    }),
    [displayLogs],
  );

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border bg-muted/30 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Live Logs</span>

          {isLive && (
            <span className="flex items-center gap-1 text-xs text-emerald-500">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live
            </span>
          )}

          <Badge
            variant="secondary"
            className="h-5 px-1.5 text-xs tabular-nums"
          >
            {displayLogs.length}
          </Badge>

          {levelCounts.errors > 0 && (
            <Badge className="h-5 px-1.5 text-xs bg-red-500/15 text-red-500">
              {levelCounts.errors} err
            </Badge>
          )}
          {levelCounts.warns > 0 && (
            <Badge className="h-5 px-1.5 text-xs bg-yellow-500/15 text-yellow-600 dark:text-yellow-400">
              {levelCounts.warns} warn
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-1">
          {onRefresh && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 rounded-md"
              onClick={onRefresh}
              aria-label="Refresh logs"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 rounded-md"
            onClick={clearLogs}
            aria-label="Clear logs"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Terminal body */}
      <ScrollArea className="h-56">
        <div
          className="log-terminal bg-[#0d1117] dark:bg-[#0a0d14] px-4 py-3 min-h-56"
          aria-live="polite"
          aria-label="Log output"
        >
          {displayLogs.length === 0 ? (
            <p className="text-muted-foreground/40 text-xs">
              No logs yet — run the migration workflow to see output.
            </p>
          ) : (
            <div className="space-y-0.5">
              {displayLogs.map((log, idx) => {
                const level = log.level as LogLevel;
                return (
                  <div
                    key={idx}
                    className="flex items-start gap-2 leading-relaxed"
                  >
                    <span className="text-slate-600 select-none shrink-0 tabular-nums text-[11px] pt-px">
                      {formatTimestamp(log.timestamp)}
                    </span>
                    <span
                      className={cn(
                        "shrink-0 font-semibold text-[11px] pt-px",
                        LEVEL_STYLES[level] ?? "text-slate-400",
                        LEVEL_WIDTH[level] ?? "w-[52px]",
                      )}
                    >
                      [{level}]
                    </span>
                    <span className="text-slate-300 text-[11px] break-words min-w-0">
                      {log.message}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>
    </div>
  );
}
