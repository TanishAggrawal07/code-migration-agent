import type { Metadata } from "next";
import { Clock, Filter, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export const metadata: Metadata = {
  title: "History",
};

export default function HistoryPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">History</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Past migrations, audit logs, and outputs
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-2">
            <Search className="h-3.5 w-3.5" />
            Search
          </Button>
          <Button variant="outline" size="sm" className="gap-2">
            <Filter className="h-3.5 w-3.5" />
            Filter
          </Button>
        </div>
      </div>

      {/* Timeline — empty state */}
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

      {/* Skeleton timeline rows */}
      <div className="rounded-xl border border-border bg-card divide-y divide-border/50 overflow-hidden opacity-30">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-start gap-4 px-4 py-4 animate-pulse">
            <div className="mt-0.5 h-8 w-8 rounded-full bg-muted shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="h-3.5 w-40 rounded bg-muted" />
              <div className="h-2.5 w-64 rounded bg-muted" />
            </div>
            <div className="h-5 w-14 rounded-full bg-muted shrink-0" />
          </div>
        ))}
      </div>
    </div>
  );
}
