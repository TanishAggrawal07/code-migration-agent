import Link from "next/link";
import { ArrowRight, Code2, Cpu, Database, GitBranch, Layers, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";

const features = [
  {
    icon: <Code2 className="h-6 w-6 text-blue-500" />,
    title: "AST-Powered Parsing",
    description:
      "Tree-sitter parses your .NET codebase into structured syntax trees for accurate, context-aware migration.",
  },
  {
    icon: <Database className="h-6 w-6 text-purple-500" />,
    title: "RAG with ChromaDB",
    description:
      "Retrieval-Augmented Generation ensures migration patterns are grounded in real Java idioms.",
  },
  {
    icon: <Cpu className="h-6 w-6 text-green-500" />,
    title: "Gemini 2.5 Flash",
    description:
      "Google's latest model handles complex .NET → Java transformations with high accuracy.",
  },
  {
    icon: <GitBranch className="h-6 w-6 text-orange-500" />,
    title: "LangGraph Orchestration",
    description:
      "Multi-step agent workflows ensure each file is parsed, translated, and validated systematically.",
  },
  {
    icon: <Layers className="h-6 w-6 text-pink-500" />,
    title: "MCP Integration",
    description:
      "Model Context Protocol provides standardized tool use for compilers, linters, and validators.",
  },
  {
    icon: <Zap className="h-6 w-6 text-yellow-500" />,
    title: "Instant Feedback",
    description:
      "Real-time streaming output lets you watch the migration happen and catch issues early.",
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-white">
      {/* Hero */}
      <section className="flex flex-col items-center justify-center px-6 py-32 text-center">
        <span className="mb-4 rounded-full border border-blue-500/30 bg-blue-500/10 px-4 py-1.5 text-sm font-medium text-blue-400">
          AI-Powered • .NET → Java
        </span>
        <h1 className="max-w-4xl text-5xl font-bold tracking-tight sm:text-6xl lg:text-7xl">
          Migrate .NET Projects to{" "}
          <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Java
          </span>{" "}
          with AI
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-slate-400">
          An intelligent code migration agent powered by Gemini 2.5 Flash, RAG, and LangGraph.
          Upload your .NET solution and get production-ready Java code in minutes.
        </p>
        <div className="mt-10 flex flex-col gap-4 sm:flex-row">
          <Link href="/dashboard">
            <Button size="lg" className="gap-2 bg-blue-600 hover:bg-blue-700">
              Start Migrating <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/about">
            <Button size="lg" variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-800">
              Learn More
            </Button>
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="mb-12 text-center text-3xl font-bold text-slate-100">
            Built for Production Migrations
          </h2>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f) => (
              <div
                key={f.title}
                className="rounded-xl border border-slate-700/50 bg-slate-800/50 p-6 transition hover:border-slate-600"
              >
                <div className="mb-4">{f.icon}</div>
                <h3 className="mb-2 text-lg font-semibold">{f.title}</h3>
                <p className="text-sm text-slate-400">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 px-6 py-8 text-center text-sm text-slate-500">
        Code Migration Agent &mdash; Built with Next.js 15 &amp; FastAPI
      </footer>
    </main>
  );
}
