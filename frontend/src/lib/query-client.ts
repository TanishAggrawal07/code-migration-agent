import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,          // 10 s — don't refetch immediately
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});

// ── Query key factory ─────────────────────────────────────────────────────
// Centralise all cache keys so invalidations are type-safe.

export const queryKeys = {
  migrations: {
    all: () => ["migrations"] as const,
    list: () => ["migrations", "list"] as const,
    detail: (id: string) => ["migrations", "detail", id] as const,
    status: (id: string) => ["migrations", "status", id] as const,
    files: (id: string) => ["migrations", "files", id] as const,
  },
  health: () => ["health"] as const,
} as const;
