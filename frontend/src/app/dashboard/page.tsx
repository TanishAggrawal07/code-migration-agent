import { Upload, FileCode2, CheckCircle, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";

const stats = [
  { label: "Projects Migrated", value: "0", icon: <CheckCircle className="h-5 w-5 text-green-500" /> },
  { label: "Files Processed", value: "0", icon: <FileCode2 className="h-5 w-5 text-blue-500" /> },
  { label: "In Progress", value: "0", icon: <Clock className="h-5 w-5 text-yellow-500" /> },
];

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-slate-800 px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <h1 className="text-xl font-bold text-slate-100">Migration Dashboard</h1>
          <Button size="sm" className="gap-2 bg-blue-600 hover:bg-blue-700">
            <Upload className="h-4 w-4" /> Upload Project
          </Button>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-6 py-8">
        {/* Stats */}
        <div className="mb-8 grid gap-4 sm:grid-cols-3">
          {stats.map((s) => (
            <div
              key={s.label}
              className="flex items-center gap-4 rounded-xl border border-slate-800 bg-slate-900 p-5"
            >
              {s.icon}
              <div>
                <p className="text-2xl font-bold">{s.value}</p>
                <p className="text-sm text-slate-400">{s.label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Upload Zone Placeholder */}
        <div className="rounded-xl border-2 border-dashed border-slate-700 bg-slate-900/50 p-16 text-center">
          <Upload className="mx-auto mb-4 h-12 w-12 text-slate-600" />
          <p className="text-lg font-medium text-slate-300">Drop your .NET project here</p>
          <p className="mt-2 text-sm text-slate-500">
            Supports .csproj, .sln, .cs files and zip archives
          </p>
          <Button variant="outline" className="mt-6 border-slate-600 text-slate-300 hover:bg-slate-800">
            Browse Files
          </Button>
        </div>

        {/* Recent Migrations Placeholder */}
        <div className="mt-8">
          <h2 className="mb-4 text-lg font-semibold text-slate-200">Recent Migrations</h2>
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-sm text-slate-500">
            No migrations yet. Upload a .NET project to get started.
          </div>
        </div>
      </div>
    </main>
  );
}
