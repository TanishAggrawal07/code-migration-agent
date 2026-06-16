"use client";

import * as React from "react";
import { CloudUpload, FileCode2, FolderArchive, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const ACCEPTED_EXTENSIONS = [".csproj", ".sln", ".cs", ".zip"];

interface MockFile {
  name: string;
  size: string;
}

export function UploadCard() {
  const [dragging, setDragging] = React.useState(false);
  const [mockFile, setMockFile] = React.useState<MockFile | null>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => setDragging(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      setMockFile({
        name: file.name,
        size: `${(file.size / 1024).toFixed(1)} KB`,
      });
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setMockFile({
        name: file.name,
        size: `${(file.size / 1024).toFixed(1)} KB`,
      });
    }
  };

  const clearFile = () => setMockFile(null);

  return (
    <div className="rounded-xl border border-border bg-card p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">Upload .NET Project</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Drop a file or browse to start migration
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          {ACCEPTED_EXTENSIONS.map((ext) => (
            <Badge
              key={ext}
              variant="secondary"
              className="text-xs px-1.5 py-0 font-mono"
            >
              {ext}
            </Badge>
          ))}
        </div>
      </div>

      {/* Drop zone */}
      <label
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "relative flex flex-col items-center justify-center gap-4 rounded-lg border-2 border-dashed",
          "min-h-40 cursor-pointer px-6 py-8 text-center transition-all duration-200",
          dragging
            ? "border-primary bg-primary/5 scale-[1.01]"
            : "border-border hover:border-primary/50 hover:bg-muted/40",
        )}
        aria-label="Upload .NET project file"
      >
        <input
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(",")}
          className="sr-only"
          onChange={handleFileChange}
          aria-label="File input"
        />

        {mockFile ? (
          <div className="flex items-center gap-3 w-full max-w-sm">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              {mockFile.name.endsWith(".zip") ? (
                <FolderArchive className="h-5 w-5 text-primary" />
              ) : (
                <FileCode2 className="h-5 w-5 text-primary" />
              )}
            </div>
            <div className="flex-1 text-left min-w-0">
              <p className="text-sm font-medium truncate">{mockFile.name}</p>
              <p className="text-xs text-muted-foreground">{mockFile.size}</p>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                clearFile();
              }}
              aria-label="Remove file"
              className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-destructive/10 hover:text-destructive transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <>
            <div
              className={cn(
                "flex h-14 w-14 items-center justify-center rounded-2xl border-2 transition-colors",
                dragging
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-muted/60 text-muted-foreground",
              )}
            >
              <CloudUpload className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground">
                Drop your .NET project here
              </p>
              <p className="text-xs text-muted-foreground">
                or{" "}
                <span className="text-primary underline-offset-2 hover:underline">
                  browse files
                </span>{" "}
                — .csproj, .sln, .cs, .zip
              </p>
            </div>
          </>
        )}
      </label>

      {/* Action */}
      <Button
        className="w-full gap-2"
        disabled={!mockFile}
        aria-label="Start migration"
      >
        <CloudUpload className="h-4 w-4" />
        {mockFile ? "Start Migration" : "Upload to Begin"}
      </Button>
    </div>
  );
}
