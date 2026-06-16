"use client";

import * as React from "react";
import { Terminal, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";

type LogLevel = "INFO" | "SUCCESS" | "WARN" | "ERROR" | "DEBUG";

interface LogEntry {
  id: number;
  level: LogLevel;
  message: string;
  timestamp: string;
}

const LEVEL_STYLES: Record<LogLevel, string> = {
  INFO:    "text-blue-400",
  SUCCESS: "text-emerald-400",
  WARN:    "text-yellow-400",
  ERROR:   "text-red-400",
  DEBUG:   "text-muted-foreground",
};

const INITIAL_LOGS: LogEntry[] = [
  { id: 1,  level: "INFO",    message: "Code Migration Agent initialized",        timestamp: "09:00:00" },
  { id: 2,  level: "INFO",    message: "Loading configuration from .env",         timestamp: "09:00:00" },
  { id: 3,  level: "SUCCESS", message: "FastAPI backend connected",                timestamp: "09:00:01" },
  { id: 4,  level: "INFO",    message: "ChromaDB vector store loaded",            timestamp: "09:00:01" },
  { id: 5,  level: "SUCCESS", message: "Sentence transformer model ready",        timestamp: "09:00:02" },
  { id: 6,  level: "INFO",    message: "LangGraph agent pipeline configured",     timestamp: "09:00:02" },
  { id: 7,  level: "SUCCESS", message: "Gemini 2.5 Flash API reachable",          timestamp: "09:00:03" },
  { id: 8,  level: "INFO",    message: "Tree-sitter parser loaded",               timestamp: "09:00:03" },
  { id: 9,  level: "SUCCESS", message: "All systems ready — awaiting upload",     timestamp: "09:00:04" },
  { id: 10, level: "INFO",    message: "Status: IDLE · Drop a .NET project to start", timestamp: "09:00:04" },
];

export function LogPanel() {
  const [logs, setLogs] = React.useState<LogEntry[]>(INITIAL_LOGS);
  const bottomRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const clearLogs = () => setLogs([]);

  const levelCounts = React.useMemo(
    () => ({
      errors: logs.filter((l) => l.level === "ERROR").length,
      warns:  logs.filter((l) => l.level === "WARN").length,
    }),
    [logs],
  );

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border bg-muted/30 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Live Logs</span>
          <Badge variant="secondary" className="h-5 px-1.5 text-xs tabular-nums">
            {logs.length}
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

      {/* Terminal body */}
      <ScrollArea className="h-52">
        <div
          className="log-terminal bg-[#0d1117] dark:bg-[#0a0d14] px-4 py-3 space-y-0.5 min-h-52"
          aria-live="polite"
          aria-label="Log output"
        >
          {logs.length === 0 ? (
            <p className="text-muted-foreground/50 text-xs">No logs yet.</p>
          ) : (
            logs.map((log) => (
              <div key={log.id} className="flex items-start gap-2 group">
                <span className="text-muted-foreground/40 select-none shrink-0">
                  {log.timestamp}
                </span>
                <span
                  className={cn(
                    "shrink-0 font-semibold w-[52px]",
                    LEVEL_STYLES[log.level],
                  )}
                >
                  [{log.level}]
                </span>
                <span className="text-slate-300 dark:text-slate-300 break-all">
                  {log.message}
                </span>
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>
    </div>
  );
}
