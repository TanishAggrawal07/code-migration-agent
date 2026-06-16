import type { Metadata } from "next";
import {
  ArrowRight,
  Binary,
  BookOpen,
  BrainCircuit,
  Coffee,
  DatabaseZap,
  GitBranch,
  Layers,
  Network,
  ScanSearch,
  Server,
  Sparkles,
  Workflow,
  Wrench,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export const metadata: Metadata = {
  title: "Architecture",
};

const TECH_STACK = [
  {
    category: "Frontend",
    color: "text-blue-500 bg-blue-500/10 border-blue-500/20",
    items: ["Next.js 15 (App Router)", "TypeScript", "Tailwind CSS v4", "shadcn/ui", "React Query", "Lucide React"],
    icon: Layers,
  },
  {
    category: "Backend",
    color: "text-violet-500 bg-violet-500/10 border-violet-500/20",
    items: ["Python 3.11", "FastAPI", "LangGraph", "Pydantic Settings", "Uvicorn", "aiofiles"],
    icon: Server,
  },
  {
    category: "AI / LLM",
    color: "text-amber-500 bg-amber-500/10 border-amber-500/20",
    items: ["Gemini 2.5 Flash API", "RAG Pipeline", "MCP (Model Context Protocol)", "LangChain Core"],
    icon: Sparkles,
  },
  {
    category: "Vector Store",
    color: "text-cyan-500 bg-cyan-500/10 border-cyan-500/20",
    items: ["ChromaDB", "Sentence Transformers", "all-MiniLM-L6-v2", "Semantic chunking"],
    icon: DatabaseZap,
  },
  {
    category: "Code Parsing",
    color: "text-purple-500 bg-purple-500/10 border-purple-500/20",
    items: ["Tree-sitter (C# grammar)", "AST traversal", "Type inference", "Dependency graph"],
    icon: ScanSearch,
  },
  {
    category: "Deployment",
    color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
    items: ["Vercel (Frontend)", "Render (Backend)", "Docker / Compose", "GitHub Actions CI"],
    icon: GitBranch,
  },
] as const;

const PIPELINE_STEPS = [
  {
    step: "01",
    title: "Upload",
    description: "User uploads a .NET project — .cs, .csproj, .sln, or a zip archive.",
    icon: BookOpen,
    color: "text-blue-500 bg-blue-500/10 border-blue-500/20",
  },
  {
    step: "02",
    title: "Parse",
    description: "Tree-sitter generates a full Abstract Syntax Tree for each C# source file.",
    icon: ScanSearch,
    color: "text-violet-500 bg-violet-500/10 border-violet-500/20",
  },
  {
    step: "03",
    title: "Analyze",
    description: "Semantic analysis extracts types, methods, namespaces, and dependency edges.",
    icon: BrainCircuit,
    color: "text-purple-500 bg-purple-500/10 border-purple-500/20",
  },
  {
    step: "04",
    title: "Embed",
    description: "Code chunks are embedded via Sentence Transformers and stored in ChromaDB.",
    icon: Binary,
    color: "text-indigo-500 bg-indigo-500/10 border-indigo-500/20",
  },
  {
    step: "05",
    title: "Retrieve",
    description: "RAG retrieves the closest Java migration patterns for each C# construct.",
    icon: DatabaseZap,
    color: "text-cyan-500 bg-cyan-500/10 border-cyan-500/20",
  },
  {
    step: "06",
    title: "Generate",
    description: "Gemini 2.5 Flash translates each class with retrieved context as grounding.",
    icon: Sparkles,
    color: "text-amber-500 bg-amber-500/10 border-amber-500/20",
  },
  {
    step: "07",
    title: "Compile",
    description: "MCP compiler tools validate the Java output and loop errors back to the LLM.",
    icon: Wrench,
    color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
  },
  {
    step: "08",
    title: "Download",
    description: "The user downloads the migrated, compiled, and lint-clean Java project.",
    icon: Coffee,
    color: "text-orange-500 bg-orange-500/10 border-orange-500/20",
  },
] as const;

export default function AboutPage() {
  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="max-w-2xl">
        <Badge
          variant="secondary"
          className="mb-3 border border-primary/20 bg-primary/8 text-primary"
        >
          Architecture Overview
        </Badge>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
          How the Migration Agent Works
        </h1>
        <p className="mt-3 text-muted-foreground leading-relaxed">
          A multi-stage AI pipeline that combines AST parsing, retrieval-augmented generation,
          and self-healing compilation to produce production-ready Java from .NET source code.
        </p>
      </div>

      {/* Architecture diagram placeholder */}
      <div className="rounded-xl border border-dashed border-border bg-muted/30 p-8">
        <div className="flex flex-col items-center gap-6">
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
            Architecture Diagram
          </p>

          {/* Simple visual flow */}
          <div className="flex flex-wrap items-center justify-center gap-2 w-full">
            {[
              { label: "Next.js UI",     icon: Layers,      color: "border-blue-500/30 text-blue-500 bg-blue-500/5" },
              { label: "FastAPI",        icon: Network,      color: "border-violet-500/30 text-violet-500 bg-violet-500/5" },
              { label: "LangGraph",      icon: Workflow,     color: "border-purple-500/30 text-purple-500 bg-purple-500/5" },
              { label: "ChromaDB",       icon: DatabaseZap,  color: "border-cyan-500/30 text-cyan-500 bg-cyan-500/5" },
              { label: "Gemini 2.5",     icon: Sparkles,     color: "border-amber-500/30 text-amber-500 bg-amber-500/5" },
              { label: "Java Output",    icon: Coffee,       color: "border-emerald-500/30 text-emerald-500 bg-emerald-500/5" },
            ].map(({ label, icon: Icon, color }, idx, arr) => (
              <div key={label} className="flex items-center gap-2">
                <div className={`flex items-center gap-2 rounded-lg border px-3 py-2.5 text-sm font-medium ${color}`}>
                  <Icon className="h-4 w-4" />
                  {label}
                </div>
                {idx < arr.length - 1 && (
                  <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground/40" />
                )}
              </div>
            ))}
          </div>

          <p className="text-xs text-muted-foreground italic">
            Interactive diagram coming in a future module
          </p>
        </div>
      </div>

      <Separator />

      {/* Pipeline steps */}
      <div>
        <h2 className="text-lg font-semibold mb-6">Migration Pipeline — 8 Stages</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {PIPELINE_STEPS.map(({ step, title, description, icon: Icon, color }) => (
            <div
              key={step}
              className="flex gap-4 rounded-xl border border-border bg-card p-4 hover:shadow-sm hover:border-border/80 transition-all"
            >
              <div
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border text-sm font-bold ${color}`}
              >
                {step}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Icon className={`h-3.5 w-3.5 ${color.split(" ")[0]}`} />
                  <p className="text-sm font-semibold">{title}</p>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <Separator />

      {/* Tech stack */}
      <div>
        <h2 className="text-lg font-semibold mb-6">Technology Stack</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {TECH_STACK.map(({ category, color, items, icon: Icon }) => (
            <div
              key={category}
              className="rounded-xl border border-border bg-card p-5 hover:shadow-sm transition-all"
            >
              <div className="flex items-center gap-2.5 mb-4">
                <div className={`flex h-8 w-8 items-center justify-center rounded-lg border ${color}`}>
                  <Icon className="h-4 w-4" />
                </div>
                <h3 className="font-semibold text-sm">{category}</h3>
              </div>
              <ul className="space-y-1.5">
                {items.map((item) => (
                  <li key={item} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span className="h-1 w-1 rounded-full bg-muted-foreground/40 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
