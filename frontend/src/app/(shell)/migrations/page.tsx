import type { Metadata } from "next";
import Link from "next/link";
import { ArrowUpRight, Clock, FileCode2, Plus, Workflow } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Migrations",
};

export default function MigrationsPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Migrations</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            All migration jobs and their current status
          </p>
        </div>
        <Link
          href="/dashboard"
          className={cn(buttonVariants({ size: "sm" }), "gap-2")}
        >
          <Plus className="h-4 w-4" />
          New Migration
        </Link>
      </div>

      {/* Empty state */}
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card py-20 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted mb-4">
          <Workflow className="h-6 w-6 text-muted-foreground" />
        </div>
        <h2 className="text-base font-semibold">No migrations yet</h2>
        <p className="mt-1.5 text-sm text-muted-foreground max-w-xs">
          Upload a .NET project from the dashboard to start your first
          migration.
        </p>
        <div className="mt-6 flex items-center gap-3">
          <Link
            href="/dashboard"
            className={cn(buttonVariants({ size: "sm" }), "gap-2")}
          >
            <Plus className="h-4 w-4" />
            Start Migration
          </Link>
          <Link
            href="/about"
            className={cn(
              buttonVariants({ variant: "outline", size: "sm" }),
              "gap-2",
            )}
          >
            <ArrowUpRight className="h-4 w-4" />
            View Architecture
          </Link>
        </div>
      </div>

      {/* Table shell */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/30">
          <span className="text-sm font-medium">Project</span>
          <div className="hidden sm:flex items-center gap-8 text-sm font-medium text-muted-foreground">
            <span>Files</span>
            <span>Duration</span>
            <span>Status</span>
            <span className="w-8" />
          </div>
        </div>

        {/* Ghost rows */}
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="flex items-center justify-between px-4 py-3.5 border-b border-border/50 last:border-0 opacity-25"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                <FileCode2 className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="space-y-1">
                <div className="h-3.5 w-32 rounded bg-muted" />
                <div className="h-2.5 w-20 rounded bg-muted" />
              </div>
            </div>
            <div className="hidden sm:flex items-center gap-8">
              <div className="h-3 w-8 rounded bg-muted" />
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                <div className="h-3 w-10 rounded bg-muted" />
              </div>
              <Badge variant="secondary" className="text-xs">
                Idle
              </Badge>
              <div className="w-8" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
