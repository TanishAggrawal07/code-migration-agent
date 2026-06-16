import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatsCardProps {
  label: string;
  value: string | number;
  sublabel?: string;
  icon: LucideIcon;
  trend?: "up" | "down" | "neutral";
  colorClass?: string;
}

export function StatsCard({
  label,
  value,
  sublabel,
  icon: Icon,
  colorClass = "text-primary bg-primary/10",
}: StatsCardProps) {
  return (
    <div className="group rounded-xl border border-border bg-card p-5 hover:shadow-sm hover:border-border/80 transition-all">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-sm text-muted-foreground font-medium truncate">{label}</p>
          <p className="mt-1.5 text-2xl font-bold tabular-nums tracking-tight">
            {value}
          </p>
          {sublabel && (
            <p className="mt-1 text-xs text-muted-foreground truncate">{sublabel}</p>
          )}
        </div>
        <div
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
            colorClass,
          )}
        >
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

// Skeleton version for loading state
export function StatsCardSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-card p-5 animate-pulse">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-muted rounded w-24" />
          <div className="h-7 bg-muted rounded w-12 mt-1.5" />
          <div className="h-3 bg-muted rounded w-20 mt-1" />
        </div>
        <div className="h-10 w-10 bg-muted rounded-lg" />
      </div>
    </div>
  );
}
