import type { Metadata } from "next";
import { KeyRound, Palette, Save, ServerCog } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";

export const metadata: Metadata = {
  title: "Settings",
};

interface SettingRowProps {
  label: string;
  description: string;
  children: React.ReactNode;
}

function SettingRow({ label, description, children }: SettingRowProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
      <div className="max-w-sm">
        <p className="text-sm font-medium">{label}</p>
        <p className="text-sm text-muted-foreground mt-0.5">{description}</p>
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

interface SettingSectionProps {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
}

function SettingSection({ title, icon: Icon, children }: SettingSectionProps) {
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="flex items-center gap-2.5 px-5 py-4 border-b border-border bg-muted/30">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      <div className="px-5 divide-y divide-border/60">{children}</div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight">Settings</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Configure the migration agent, API keys, and appearance
        </p>
      </div>

      {/* API Keys */}
      <SettingSection title="API Keys" icon={KeyRound}>
        <SettingRow
          label="Gemini API Key"
          description="Used by Gemini 2.5 Flash for code generation"
        >
          <div className="flex items-center gap-2">
            <div className="h-9 w-48 rounded-lg border border-input bg-muted/50 flex items-center px-3">
              <span className="text-xs text-muted-foreground font-mono tracking-widest">
                ••••••••••••••••
              </span>
            </div>
            <Button size="sm" variant="outline" disabled>
              Update
            </Button>
          </div>
        </SettingRow>
        <SettingRow
          label="Environment"
          description="Loaded from .env file on the backend"
        >
          <Badge variant="secondary" className="text-xs">
            GEMINI_API_KEY
          </Badge>
        </SettingRow>
      </SettingSection>

      {/* Backend */}
      <SettingSection title="Backend Connection" icon={ServerCog}>
        <SettingRow
          label="API URL"
          description="FastAPI backend base URL"
        >
          <div className="flex items-center gap-2">
            <div className="h-9 w-48 rounded-lg border border-input bg-muted/50 flex items-center px-3">
              <span className="text-xs text-muted-foreground font-mono">
                http://localhost:8000
              </span>
            </div>
            <Button size="sm" variant="outline" disabled>
              Test
            </Button>
          </div>
        </SettingRow>
        <SettingRow
          label="Health Status"
          description="Last checked on page load"
        >
          <Badge className="text-xs bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
            Healthy
          </Badge>
        </SettingRow>
        <SettingRow
          label="ChromaDB Path"
          description="Vector store persistence directory"
        >
          <Badge variant="secondary" className="text-xs font-mono">
            ./chroma_db
          </Badge>
        </SettingRow>
      </SettingSection>

      <Separator />

      {/* Appearance */}
      <SettingSection title="Appearance" icon={Palette}>
        <SettingRow
          label="Theme"
          description="Choose between light, dark, or system default"
        >
          <div className="flex items-center gap-1.5">
            {(["light", "dark", "system"] as const).map((t) => (
              <Button
                key={t}
                size="sm"
                variant={t === "dark" ? "default" : "outline"}
                className="h-8 px-3 capitalize text-xs"
                disabled
              >
                {t}
              </Button>
            ))}
          </div>
        </SettingRow>
      </SettingSection>

      {/* Save button */}
      <div className="flex justify-end">
        <Button disabled className="gap-2">
          <Save className="h-4 w-4" />
          Save Changes
        </Button>
      </div>
    </div>
  );
}
