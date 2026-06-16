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

type StepStatus = "idle" | "running" | "done" | "error";

interface PipelineStep {
  label: string;
  sublabel: string;
  icon: React.ElementType;
  status: StepStatus;
  color: string;
}

const STEPS: PipelineStep[] = [
  {
    label: ".NET Project",
    sublabel: "Input source",
    icon: Code2,
    status: "idle",
    color: "text-blue-500 bg-blue-500/10 border-blue-500/20",
  },
  {
    label: "Parser",
    sublabel: "Tree-sitter AST",
    icon: ScanSearch,
    status: "idle",
    color: "text-violet-500 bg-violet-500/10 border-violet-500/20",
  },
  {
    label: "Analyzer",
    sublabel: "Semantic analysis",
    icon: BrainCircuit,
    status: "idle",
    color: "text-purple-500 bg-purple-500/10 border-purple-500/20",
  },
  {
    label: "Embeddings",
    sublabel: "Sentence transformers",
    icon: Binary,
    status: "idle",
    color: "text-indigo-500 bg-indigo-500/10 border-indigo-500/20",
  },
  {
    label: "RAG",
    sublabel: "ChromaDB retrieval",
    icon: DatabaseZap,
    status: "idle",
    color: "text-cyan-500 bg-cyan-500/10 border-cyan-500/20",
  },
  {
    label: "Migration",
    sublabel: "Gemini 2.5 Flash",
    icon: BookOpen,
    status: "idle",
    color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
  },
  {
    label: "Compile",
    sublabel: "Java compiler",
    icon: CheckCircle2,
    status: "idle",
    color: "text-teal-500 bg-teal-500/10 border-teal-500/20",
  },
  {
    label: "Java Project",
    sublabel: "Output artifact",
    icon: Coffee,
    status: "idle",
    color: "text-orange-500 bg-orange-500/10 border-orange-500/20",
  },
];

const STATUS_BADGE: Record<
  StepStatus,
  { label: string; className: string }
> = {
  idle: {
    label: "Idle",
    className: "bg-muted text-muted-foreground border-transparent",
  },
  running: {
    label: "Running",
    className: "bg-blue-500/15 text-blue-500 border-transparent animate-pulse",
  },
  done: {
    label: "Done",
    className:
      "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-transparent",
  },
  error: {
    label: "Error",
    className: "bg-destructive/15 text-destructive border-transparent",
  },
};

export function PipelineView() {
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
          8 stages
        </Badge>
      </div>

      {/* Desktop: horizontal flow */}
      <div className="hidden xl:flex items-stretch gap-1.5">
        {STEPS.map((step, idx) => (
          <div key={step.label} className="flex items-center gap-1.5 flex-1 min-w-0">
            <CompactStepCard step={step} />
            {idx < STEPS.length - 1 && (
              <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground/30" />
            )}
          </div>
        ))}
      </div>

      {/* Tablet: 2-column grid */}
      <div className="hidden sm:grid xl:hidden grid-cols-2 gap-2">
        {STEPS.map((step, idx) => (
          <div key={step.label}>
            <FullStepCard step={step} />
            {idx % 2 === 0 && idx === STEPS.length - 2 && (
              <div className="flex justify-center py-1">
                <ArrowDown className="h-3.5 w-3.5 text-muted-foreground/40" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Mobile: vertical */}
      <div className="sm:hidden space-y-2">
        {STEPS.map((step, idx) => (
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

/* ── Sub-components ─────────────────────────────────────────────────────── */

function CompactStepCard({ step }: { step: PipelineStep }) {
  const Icon = step.icon;
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-1.5 rounded-lg border px-2 py-3 w-full",
        "hover:shadow-sm transition-all cursor-default text-center",
        step.color,
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="text-[11px] font-medium leading-tight">{step.label}</span>
    </div>
  );
}

function FullStepCard({ step }: { step: PipelineStep }) {
  const Icon = step.icon;
  const { label: statusLabel, className: statusClass } = STATUS_BADGE[step.status];

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-lg border p-3",
        "hover:shadow-sm cursor-default transition-all",
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
