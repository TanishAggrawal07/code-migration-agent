"use client";

import * as React from "react";
import { CheckCircle2, Info, TriangleAlert, X, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { TOAST_EVENT, type Toast, type ToastVariant } from "@/hooks/use-toast";

const VARIANT_STYLES: Record<
  ToastVariant,
  { bar: string; icon: React.ReactNode }
> = {
  success: {
    bar: "bg-emerald-500",
    icon: <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />,
  },
  error: {
    bar: "bg-destructive",
    icon: <XCircle className="h-4 w-4 text-destructive shrink-0" />,
  },
  info: {
    bar: "bg-blue-500",
    icon: <Info className="h-4 w-4 text-blue-500 shrink-0" />,
  },
  warning: {
    bar: "bg-yellow-500",
    icon: <TriangleAlert className="h-4 w-4 text-yellow-500 shrink-0" />,
  },
};

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: () => void;
}) {
  const { bar, icon } = VARIANT_STYLES[toast.variant];

  // Auto-dismiss after 4 s
  React.useEffect(() => {
    const timer = setTimeout(onDismiss, 4000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="pointer-events-auto flex w-full max-w-sm overflow-hidden rounded-xl border border-border bg-card shadow-lg animate-in slide-in-from-right-4 duration-300"
    >
      {/* Accent bar */}
      <div className={cn("w-1 shrink-0", bar)} />

      <div className="flex flex-1 items-start gap-3 p-4">
        {icon}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold leading-snug">{toast.title}</p>
          {toast.description && (
            <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
              {toast.description}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss notification"
          className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

export function ToastContainer() {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  React.useEffect(() => {
    function handler(e: Event) {
      const toast = (e as CustomEvent<Toast>).detail;
      setToasts((prev) => [...prev.slice(-4), toast]); // max 5
    }
    window.addEventListener(TOAST_EVENT, handler);
    return () => window.removeEventListener(TOAST_EVENT, handler);
  }, []);

  const dismiss = (id: string) =>
    setToasts((prev) => prev.filter((t) => t.id !== id));

  if (toasts.length === 0) return null;

  return (
    <div
      aria-label="Notifications"
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2 items-end"
    >
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={() => dismiss(t.id)} />
      ))}
    </div>
  );
}
