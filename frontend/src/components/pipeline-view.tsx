"use client";

import {
  ArrowDown,
  ArrowRight,
  Binary,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  Code2,
  Coffee,
  DatabaseZap,
  ScanSearch,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { MigrationStage } from "@/types/migration";

// ── Step config ───────────────────────────────────────────────────────────

type StepStatus = "idle" | "running" | "done" | "error";

interface PipelineStep {
  label: string;
  sublabel: string;
  icon: React.ElementType;
  stage: MigrationStage;
  color: string;
}

const STEPS: PipelineStep[] = [
  { label: ".NET Project", sublabel: "Input source",         icon: Code2,        stage: "uploaded",  color: "text-blue-500 bg-blue-500/10 border-blue-500/20" },
  { label: "Parser",       sublabel: "Tree-sitter AST",      icon: ScanSearch,   stage: "parsed",    color: "text-violet-500 bg-violet-500/10 border-violet-500/20" },
  { label: "Analyzer",     sublabel: "Semantic analysis",    icon: BrainCircuit, stage: "analyzed",  color: "text-purple-500 bg-purple-500/10 border-purple-500/20" },
  { label: "Embeddings",   sublabel: "Sentence transformers",icon: Binary,       stage: "embedded",  color: "text-indigo-500 bg-indigo-500/10 border-indigo-500/20" },
  { label: "RAG",          sublabel: "ChromaDB retrieval",   icon: DatabaseZap,  stage: "retrieved", color: "text-cyan-500 bg-cyan-500/10 border-cyan-500/20" },
  { label: "Migration",    sublabel: "Gemini 2.5 Flash",     icon: BookOpen,     stage: "migrated",  color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20" },
  { label: "Compile",      sublabel: "Java compiler",        icon: CheckCircle2, stage: "compiled",  color: "text-teal-500 bg-teal-500/10 border-teal-500/20" },
  { label: "Java Project", sublabel: "Output artifact",      icon: Coffee,       stage: "saved",     color: "text-orange-500 bg-orange-500/10 border-orange-500/20" },
];

const STATUS_BADGE: Record<StepStatus, { label: string; className: string }> = {
  idle:    { label: "Idle",    className: "bg-muted text-muted-foreground border-transparent" },
  running: { label: "Running", className: "bg-blue-500/15 text-blue-500 border-transparent animate-pulse" },
  done:    { label: "Done",    className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-transparent" },
  error:   { label: "Error",   className: "bg-destructive/15 text-destructive border-transparent" },
};

// ── Status derivation ─────────────────────────────────────────────────────

function deriveStepStatus(
  step: PipelineStep,
  currentStage: MigrationStage | undefined,
  completedStages: MigrationStage[],
  isFailed: boolean,
): StepStatus {
  if (!currentStage) return "idle";
  if (completedStages.includes(step.stage)) return "done";
  if (step.stage === "saved" && currentStage === "saved") return "done";
  if (step.stage === currentStage) {
    return isFailed ? "error" : "running";
  }
  return "idle";
}

// ── Props ─────────────────────────────────────────────────────────────────

interface PipelineViewProps {
  currentStage?: MigrationStage;
  completedStages?: MigrationStage[];
  isFailed?: boolean;
}

// ── Component ─────────────────────────────────────────────────────────────

export function PipelineView({
  currentStage,
  completedStages = [],
  isFailed = false,
}: PipelineViewProps) {
  const stepsWithStatus = STEPS.map((step) => ({
    ...step,
    status: deriveStepStatus(step, currentStage, completedStages, isFailed),
  }));

  const doneCount = stepsWithStatus.filter((s) => s.status === "done").length;

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      {/* Header */}
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">Migration Pipeline</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            End-to-end .NET → Java transformation
          </p>
        </div>
        <Badge variant="secondary" className="text-xs">
          {doneCount}/{STEPS.length} stages
        </Badge>
      </div>

      {/* Desktop: horizontal */}
      <div className="hidden xl:flex items-stretch gap-1.5">
        {stepsWithStatus.map((step, idx) => (
          <div key={step.label} className="flex items-center gap-1.5 flex-1 min-w-0">
            <CompactStepCard step={step} />
            {idx < STEPS.length - 1 && (
              <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground/30" />
            )}
          </div>
        ))}
      </div>

      {/* Tablet: 2-column */}
      <div className="hidden sm:grid xl:hidden grid-cols-2 gap-2">
        {stepsWithStatus.map((step) => (
          <FullStepCard key={step.label} step={step} />
        ))}
      </div>

      {/* Mobile: vertical */}
      <div className="sm:hidden space-y-2">
        {stepsWithStatus.map((step, idx) => (
          <div key={step.label}>
            <FullStepCard step={step} />
            {idx < STEPS.length - 1 && (
              <div className="flex justify-center py-1">
                <ArrowDown className="h-3.5 w-3.5 text-muted-foreground/40" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────

function CompactStepCard({
  step,
}: {
  step: PipelineStep & { status: StepStatus };
}) {
  const Icon = step.icon;
  const statusCfg = STATUS_BADGE[step.status];

  return (
    <div
      className={cn(
        "flex flex-col items-center gap-1 rounded-lg border px-2 py-2.5 w-full",
        "transition-all cursor-default text-center",
        step.status === "done" && "opacity-100",
        step.status === "idle" && "opacity-50",
        step.color,
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="text-[10px] font-medium leading-tight">{step.label}</span>
      <Badge className={cn("text-[9px] h-4 px-1", statusCfg.className)}>
        {statusCfg.label}
      </Badge>
    </div>
  );
}

function FullStepCard({
  step,
}: {
  step: PipelineStep & { status: StepStatus };
}) {
  const Icon = step.icon;
  const { label: statusLabel, className: statusClass } = STATUS_BADGE[step.status];

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-lg border p-3 transition-all cursor-default",
        step.status === "idle" ? "opacity-50" : "opacity-100",
        step.color,
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border",
          step.color,
        )}
      >
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{step.label}</p>
        <p className="text-xs text-muted-foreground truncate">{step.sublabel}</p>
      </div>
      <Badge className={cn("text-xs shrink-0", statusClass)}>
        {statusLabel}
      </Badge>
    </div>
  );
}
