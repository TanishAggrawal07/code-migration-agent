import Link from "next/link";
import {
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  Coffee,
  DatabaseZap,
  GitBranch,
  Layers,
  Network,
  Sparkles,
  Wrench,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Navbar } from "@/components/navbar";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const FEATURES = [
  {
    icon: DatabaseZap,
    title: "RAG-Powered Retrieval",
    description:
      "ChromaDB stores migration patterns as embeddings. Every translation is grounded in real Java idioms retrieved at inference time.",
    color: "text-cyan-500 bg-cyan-500/10 border-cyan-500/20",
  },
  {
    icon: Network,
    title: "MCP Integration",
    description:
      "Model Context Protocol gives the agent standardised access to compilers, linters, and validation tools during migration.",
    color: "text-violet-500 bg-violet-500/10 border-violet-500/20",
  },
  {
    icon: BrainCircuit,
    title: "Semantic Code Understanding",
    description:
      "Tree-sitter builds full ASTs for every C# file, so the agent understands structure, types, and dependencies — not just text.",
    color: "text-purple-500 bg-purple-500/10 border-purple-500/20",
  },
  {
    icon: Wrench,
    title: "Self-Healing Compilation",
    description:
      "If generated Java fails to compile, LangGraph loops the error back to Gemini for an automatic fix — no manual intervention.",
    color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
  },
  {
    icon: Layers,
    title: "LangGraph Orchestration",
    description:
      "A stateful multi-agent graph ensures each file is parsed, translated, compiled, and validated in the correct order.",
    color: "text-blue-500 bg-blue-500/10 border-blue-500/20",
  },
  {
    icon: Sparkles,
    title: "Gemini 2.5 Flash",
    description:
      "Google's fastest multimodal model handles complex .NET → Java transformations with high accuracy and low latency.",
    color: "text-amber-500 bg-amber-500/10 border-amber-500/20",
  },
] as const;

const PIPELINE = [
  { label: ".NET Project", icon: GitBranch,   color: "bg-blue-500/10 text-blue-500 border-blue-500/20" },
  { label: "AST Parser",   icon: Layers,      color: "bg-violet-500/10 text-violet-500 border-violet-500/20" },
  { label: "Embeddings",   icon: DatabaseZap, color: "bg-cyan-500/10 text-cyan-500 border-cyan-500/20" },
  { label: "RAG Retrieval",icon: BrainCircuit,color: "bg-purple-500/10 text-purple-500 border-purple-500/20" },
  { label: "LLM Migration",icon: Sparkles,    color: "bg-amber-500/10 text-amber-500 border-amber-500/20" },
  { label: "Java Project", icon: Coffee,      color: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" },
] as const;

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />

      <main className="flex-1">
        {/* ── Hero ──────────────────────────────────────────────────────── */}
        <section className="relative overflow-hidden px-6 py-24 sm:py-32 text-center">
          {/* Ambient glow */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
          >
            <div className="absolute left-1/2 top-0 h-[600px] w-[800px] -translate-x-1/2 -translate-y-1/3 rounded-full bg-primary/8 blur-[120px]" />
          </div>

          <div className="mx-auto max-w-4xl space-y-6">
            <Badge
              variant="secondary"
              className="gap-1.5 px-3 py-1 text-xs font-medium border border-primary/20 bg-primary/8 text-primary"
            >
              <Zap className="h-3 w-3" />
              Powered by Gemini 2.5 Flash · RAG · LangGraph
            </Badge>

            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl xl:text-7xl">
              AI-Powered{" "}
              <span className="gradient-text">.NET to Java</span>
              <br />
              Migration
            </h1>

            <p className="mx-auto max-w-2xl text-base sm:text-lg text-muted-foreground leading-relaxed">
              Migrate legacy applications using RAG, MCP, and LLM-powered agents.
              Upload your .NET solution and receive production-ready Java code in minutes.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <Link
                href="/dashboard"
                className={cn(
                  buttonVariants({ size: "lg" }),
                  "gap-2 h-11 px-6 text-sm font-medium shadow-md",
                )}
              >
                Start Migration
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/about"
                className={cn(
                  buttonVariants({ variant: "outline", size: "lg" }),
                  "gap-2 h-11 px-6 text-sm",
                )}
              >
                View Architecture
                <Layers className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </section>

        {/* ── Mini pipeline ─────────────────────────────────────────────── */}
        <section className="px-6 pb-16">
          <div className="mx-auto max-w-5xl">
            <div className="flex flex-wrap items-center justify-center gap-2">
              {PIPELINE.map(({ label, icon: Icon, color }, idx) => (
                <div key={label} className="flex items-center gap-2">
                  <div
                    className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium ${color}`}
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </div>
                  {idx < PIPELINE.length - 1 && (
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/40 shrink-0" />
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Features ──────────────────────────────────────────────────── */}
        <section className="px-6 pb-24">
          <div className="mx-auto max-w-5xl">
            <div className="text-center mb-12">
              <h2 className="text-2xl font-bold sm:text-3xl">
                Built for Production Migrations
              </h2>
              <p className="mt-3 text-muted-foreground">
                A full AI stack purpose-built for enterprise .NET → Java projects.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map(({ icon: Icon, title, description, color }) => (
                <div
                  key={title}
                  className="group relative rounded-xl border border-border bg-card p-6 hover:border-border/80 hover:shadow-md transition-all duration-200"
                >
                  <div
                    className={`mb-4 flex h-10 w-10 items-center justify-center rounded-lg border ${color}`}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="mb-2 text-sm font-semibold">{title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── CTA banner ────────────────────────────────────────────────── */}
        <section className="px-6 pb-24">
          <div className="mx-auto max-w-3xl">
            <div className="relative overflow-hidden rounded-2xl gradient-brand px-8 py-12 text-center shadow-xl">
              <div
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 -z-10"
              >
                <div className="absolute right-0 top-0 h-64 w-64 -translate-y-1/3 translate-x-1/3 rounded-full bg-white/10 blur-3xl" />
                <div className="absolute bottom-0 left-0 h-48 w-48 translate-y-1/3 -translate-x-1/3 rounded-full bg-white/10 blur-3xl" />
              </div>
              <CheckCircle2 className="mx-auto mb-4 h-10 w-10 text-white/80" />
              <h2 className="text-2xl font-bold text-white">
                Ready to migrate your .NET project?
              </h2>
              <p className="mt-3 text-white/70 text-sm">
                Upload your solution, configure the agent, and get Java code in minutes.
              </p>
              <Link
                href="/dashboard"
                className={cn(
                  buttonVariants({ size: "lg" }),
                  "mt-6 inline-flex bg-white text-primary hover:bg-white/90 gap-2 shadow-md",
                )}
              >
                Open Dashboard <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/60 px-6 py-6 text-center text-xs text-muted-foreground">
        Code Migration Agent &mdash; Next.js 15 · FastAPI · Gemini 2.5 Flash · LangGraph
      </footer>
    </div>
  );
}
