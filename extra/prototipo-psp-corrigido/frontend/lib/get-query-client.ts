import {
  defaultShouldDehydrateQuery,
  isServer,
  QueryClient,
} from "@tanstack/react-query";
import { GC_TIMES, STALE_TIMES } from "./query-config";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: STALE_TIMES.USER_CONTENT,
        gcTime: GC_TIMES.MEDIUM,
        retry: (failureCount, error: Error) => {
          const status =
            error && typeof error === "object" && "status" in error
              ? (error as { status?: number }).status
              : undefined;
          if (status === 401 || status === 403 || status === 404) return false;
          return failureCount < 2;
        },
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: (failureCount, error: Error) => {
          const status =
            error && typeof error === "object" && "status" in error
              ? (error as { status?: number }).status
              : undefined;
          if (status && status >= 400 && status < 500) return false;
          return failureCount < 1;
        },
      },
      dehydrate: {
        shouldDehydrateQuery: (query) =>
          defaultShouldDehydrateQuery(query) ||
          query.state.status === "pending",
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

export function getQueryClient() {
  if (isServer) {
    return makeQueryClient();
  }
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}
