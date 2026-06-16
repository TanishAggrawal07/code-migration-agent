import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

const stack = [
  { category: "Frontend", items: ["Next.js 15", "TypeScript", "Tailwind CSS", "shadcn/ui", "React Query"] },
  { category: "Backend", items: ["Python 3.11", "FastAPI", "LangGraph", "ChromaDB", "Sentence Transformers"] },
  { category: "AI / LLM", items: ["Gemini 2.5 Flash", "RAG Pipeline", "MCP (Model Context Protocol)"] },
  { category: "Parsing", items: ["Tree-sitter (.NET grammar)", "AST traversal", "Type inference"] },
  { category: "Deployment", items: ["Vercel (Frontend)", "Render (Backend)", "Docker"] },
];

const pipeline = [
  { step: "01", title: "Upload", description: "User uploads a .NET project (.cs / .csproj / .sln / zip)." },
  { step: "02", title: "Parse", description: "Tree-sitter builds an AST for each C# file." },
  { step: "03", title: "Embed", description: "Sentence Transformers embed code chunks into ChromaDB." },
  { step: "04", title: "Retrieve", description: "RAG retrieves relevant Java migration patterns." },
  { step: "05", title: "Generate", description: "Gemini 2.5 Flash generates equivalent Java code." },
  { step: "06", title: "Validate", description: "MCP compiler tools validate and lint the output." },
  { step: "07", title: "Download", description: "User downloads the migrated Java project." },
];

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-4xl px-6 py-12">
        <Link href="/">
          <Button variant="ghost" size="sm" className="mb-8 gap-2 text-slate-400 hover:text-white">
            <ArrowLeft className="h-4 w-4" /> Back to Home
          </Button>
        </Link>

        <h1 className="mb-4 text-4xl font-bold">About the Migration Agent</h1>
        <p className="mb-12 text-lg text-slate-400">
          A resume-level AI system that automates the translation of enterprise .NET codebases to Java
          using a multi-agent RAG pipeline.
        </p>

        {/* Pipeline */}
        <section className="mb-16">
          <h2 className="mb-6 text-2xl font-semibold">Migration Pipeline</h2>
          <div className="space-y-4">
            {pipeline.map((p) => (
              <div
                key={p.step}
                className="flex gap-4 rounded-lg border border-slate-800 bg-slate-900 p-5"
              >
                <span className="text-lg font-bold text-blue-400">{p.step}</span>
                <div>
                  <p className="font-semibold text-slate-100">{p.title}</p>
                  <p className="mt-1 text-sm text-slate-400">{p.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Tech Stack */}
        <section>
          <h2 className="mb-6 text-2xl font-semibold">Technology Stack</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {stack.map((s) => (
              <div key={s.category} className="rounded-lg border border-slate-800 bg-slate-900 p-5">
                <h3 className="mb-3 font-semibold text-blue-400">{s.category}</h3>
                <ul className="space-y-1">
                  {s.items.map((item) => (
                    <li key={item} className="text-sm text-slate-300">
                      • {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
