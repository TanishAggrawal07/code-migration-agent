"use client";

import Link from "next/link";
import { GitBranch, Zap } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/60 bg-background/80 backdrop-blur-md">
      <div className="flex h-14 items-center px-4 gap-4">
        {/* Brand */}
        <Link
          href="/"
          className="flex items-center gap-2.5 font-semibold text-foreground hover:opacity-80 transition-opacity"
          aria-label="AI Code Migration Agent home"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-lg gradient-brand shadow-sm">
            <Zap className="h-4 w-4 text-white" strokeWidth={2.5} />
          </div>
          <span className="text-sm font-semibold tracking-tight hidden sm:block">
            AI Code Migration Agent
          </span>
          <span className="text-sm font-semibold tracking-tight sm:hidden">
            CMA
          </span>
        </Link>

        <Badge
          variant="secondary"
          className="hidden sm:flex text-xs px-2 py-0.5 bg-primary/10 text-primary border-primary/20"
        >
          .NET → Java
        </Badge>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Right actions */}
        <nav className="flex items-center gap-1" aria-label="Global actions">
          {/* GitHub link — plain anchor styled as icon button */}
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="View source on GitHub"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <GitBranch className="h-4 w-4" />
          </a>

          <ThemeToggle />

          {/* Avatar placeholder */}
          <button
            type="button"
            aria-label="User account"
            className="ml-1 flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-semibold ring-1 ring-border hover:ring-primary/40 transition-all"
          >
            U
          </button>
        </nav>
      </div>
    </header>
  );
}
