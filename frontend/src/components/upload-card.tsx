"use client";

import * as React from "react";
import {
  CheckCircle2,
  CloudUpload,
  FileCode2,
  FolderArchive,
  Loader2,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useUploadFiles } from "@/hooks/use-migration";
import { ApiClientError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

const ACCEPTED_EXTENSIONS = [".cs", ".csproj", ".sln", ".config", ".xml", ".json", ".zip"];
const ACCEPT_STRING = ACCEPTED_EXTENSIONS.join(",");

interface UploadCardProps {
  migrationId: string | null;
  /** Called after a successful upload with the list of saved file names */
  onUploaded?: (files: string[]) => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadCard({ migrationId, onUploaded }: UploadCardProps) {
  const [dragging, setDragging] = React.useState(false);
  const [selectedFiles, setSelectedFiles] = React.useState<File[]>([]);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const { mutateAsync, isPending, uploadProgress } = useUploadFiles(migrationId);

  // ── File selection helpers ─────────────────────────────────────────

  function addFiles(incoming: FileList | null) {
    if (!incoming) return;
    const newFiles = Array.from(incoming).filter((f) => {
      const ext = "." + f.name.split(".").pop()?.toLowerCase();
      return ACCEPTED_EXTENSIONS.includes(ext);
    });
    setSelectedFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      return [...prev, ...newFiles.filter((f) => !existing.has(f.name))];
    });
  }

  function removeFile(name: string) {
    setSelectedFiles((prev) => prev.filter((f) => f.name !== name));
  }

  // ── Drag handlers ──────────────────────────────────────────────────

  function onDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragging(true);
  }
  function onDragLeave() {
    setDragging(false);
  }
  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  }

  // ── Upload ────────────────────────────────────────────────────────

  async function handleUpload() {
    if (!migrationId || selectedFiles.length === 0) return;
    try {
      const result = await mutateAsync(selectedFiles);
      setSelectedFiles([]);
      onUploaded?.(result.uploaded_files);
      toast.success(
        "Upload successful",
        `${result.uploaded_count} file(s) uploaded.`,
      );
    } catch (err) {
      const msg =
        err instanceof ApiClientError
          ? err.payload.message
          : "Upload failed. Please try again.";
      toast.error("Upload failed", msg);
    }
  }

  const canUpload = !!migrationId && selectedFiles.length > 0 && !isPending;

  return (
    <div className="rounded-xl border border-border bg-card p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-base font-semibold">Upload .NET Project</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            {migrationId
              ? "Drop files or browse — multiple files supported"
              : "Create a migration first to enable upload"}
          </p>
        </div>
        <div className="flex items-center gap-1 flex-wrap">
          {ACCEPTED_EXTENSIONS.slice(0, 4).map((ext) => (
            <Badge key={ext} variant="secondary" className="text-xs px-1.5 py-0 font-mono">
              {ext}
            </Badge>
          ))}
          <Badge variant="secondary" className="text-xs px-1.5 py-0 font-mono">…</Badge>
        </div>
      </div>

      {/* Drop zone */}
      <label
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={cn(
          "relative flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed",
          "min-h-32 cursor-pointer px-6 py-6 text-center transition-all duration-200",
          !migrationId && "pointer-events-none opacity-50",
          dragging
            ? "border-primary bg-primary/5 scale-[1.01]"
            : "border-border hover:border-primary/50 hover:bg-muted/40",
        )}
        aria-label="Drop zone for .NET project files"
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT_STRING}
          className="sr-only"
          onChange={(e) => addFiles(e.target.files)}
          aria-label="File input"
          disabled={!migrationId || isPending}
        />

        <div
          className={cn(
            "flex h-12 w-12 items-center justify-center rounded-2xl border-2 transition-colors",
            dragging
              ? "border-primary bg-primary/10 text-primary"
              : "border-border bg-muted/60 text-muted-foreground",
          )}
        >
          <CloudUpload className="h-5 w-5" />
        </div>
        <div className="space-y-0.5">
          <p className="text-sm font-medium text-foreground">
            Drop your .NET project here
          </p>
          <p className="text-xs text-muted-foreground">
            or{" "}
            <span className="text-primary underline-offset-2 hover:underline">
              browse files
            </span>
            {" "}— .cs .csproj .sln .xml .json .zip
          </p>
        </div>
      </label>

      {/* Selected files list */}
      {selectedFiles.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs text-muted-foreground font-medium">
            {selectedFiles.length} file(s) selected
          </p>
          <div className="max-h-36 overflow-y-auto space-y-1 pr-1">
            {selectedFiles.map((file) => (
              <div
                key={file.name}
                className="flex items-center gap-2.5 rounded-lg bg-muted/50 px-3 py-1.5"
              >
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-card">
                  {file.name.endsWith(".zip") ? (
                    <FolderArchive className="h-3.5 w-3.5 text-amber-500" />
                  ) : (
                    <FileCode2 className="h-3.5 w-3.5 text-blue-500" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate">{file.name}</p>
                  <p className="text-[10px] text-muted-foreground">
                    {formatBytes(file.size)}
                  </p>
                </div>
                {!isPending && (
                  <button
                    type="button"
                    onClick={() => removeFile(file.name)}
                    aria-label={`Remove ${file.name}`}
                    className="shrink-0 text-muted-foreground hover:text-destructive transition-colors"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload progress */}
      {isPending && uploadProgress > 0 && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Uploading…</span>
            <span className="tabular-nums">{uploadProgress}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Action button */}
      <Button
        className="w-full gap-2"
        disabled={!canUpload}
        onClick={handleUpload}
        aria-label="Upload selected files"
      >
        {isPending ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Uploading…
          </>
        ) : selectedFiles.length > 0 ? (
          <>
            <CloudUpload className="h-4 w-4" />
            Upload {selectedFiles.length} File{selectedFiles.length > 1 ? "s" : ""}
          </>
        ) : migrationId ? (
          <>
            <CheckCircle2 className="h-4 w-4" />
            Select Files to Upload
          </>
        ) : (
          <>
            <CloudUpload className="h-4 w-4" />
            Create Migration First
          </>
        )}
      </Button>
    </div>
  );
}
