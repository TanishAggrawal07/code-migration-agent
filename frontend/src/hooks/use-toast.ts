"use client";

/**
 * Minimal toast hook — uses browser-native APIs so we don't need
 * an extra toast library while keeping the design system clean.
 * Emits custom DOM events consumed by <ToastContainer />.
 */

export type ToastVariant = "success" | "error" | "info" | "warning";

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
}

// Global event bus
const TOAST_EVENT = "cma:toast";

function emit(toast: Omit<Toast, "id">) {
  if (typeof window === "undefined") return;
  const id = Math.random().toString(36).slice(2);
  window.dispatchEvent(
    new CustomEvent<Toast>(TOAST_EVENT, {
      detail: { ...toast, id },
    }),
  );
}

export const toast = {
  success: (title: string, description?: string) =>
    emit({ title, description, variant: "success" }),
  error: (title: string, description?: string) =>
    emit({ title, description, variant: "error" }),
  info: (title: string, description?: string) =>
    emit({ title, description, variant: "info" }),
  warning: (title: string, description?: string) =>
    emit({ title, description, variant: "warning" }),
};

export { TOAST_EVENT };
