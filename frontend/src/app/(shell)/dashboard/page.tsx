import type { Metadata } from "next";
import {
  AlertCircle,
  CheckCircle2,
  FileCode2,
  FolderOpen,
  Gauge,
} from "lucide-react";
import { UploadCard } from "@/components/upload-card";
import { PipelineView } from "@/components/pipeline-view";
import { LogPanel } from "@/components/log-panel";
import { StatsCard } from "@/components/stats-card";

export const metadata: Metadata = {
  title: "Dashboard",
};

const STATS = [
  {
    label: "Files Processed",
    value: "0",
    sublabel: "Ready to start",
    icon: FileCode2,
    colorClass: "text-blue-500 bg-blue-500/10",
  },
  {
    label: "Classes Migrated",
    value: "0",
    sublabel: "Awaiting upload",
    icon: FolderOpen,
    colorClass: "text-violet-500 bg-violet-500/10",
  },
  {
    label: "Errors Fixed",
    value: "0",
    sublabel: "Self-healing active",
    icon: AlertCircle,
    colorClass: "text-emerald-500 bg-emerald-500/10",
  },
  {
    label: "Status",
    value: "Idle",
    sublabel: "No active migration",
    icon: Gauge,
    colorClass: "text-amber-500 bg-amber-500/10",
  },
] as const;

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Dashboard</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Upload a .NET project and monitor the migration pipeline
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
          All systems operational
        </div>
      </div>

      {/* Stats row */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {STATS.map((s) => (
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

      {/* Upload + Logs — side by side on large screens */}
      <div className="grid gap-4 lg:grid-cols-2">
        <UploadCard />
        <LogPanel />
      </div>

      {/* Pipeline */}
      <PipelineView />
    </div>
  );
}
