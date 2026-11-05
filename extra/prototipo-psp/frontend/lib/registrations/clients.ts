import { useInfiniteQuery } from "@tanstack/react-query";
import { apiFetch } from "../fetch-client";
import { STALE_TIMES } from "../query-config";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export interface ClientSummary {
  uuid: string;
  name: string;
  client_code: string;
}

interface Pagination {
  page: number;
  per_page: number;
  total: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

interface ClientsResponse {
  success: boolean;
  data: ClientSummary[];
  pagination: Pagination;
}

const CLIENTS_SUMMARY_PER_PAGE = 100;
const CLIENTS_SEARCH_PER_PAGE = 20;

export function useClientsSummary() {
  const result = useInfiniteQuery({
    queryKey: ["clients", "summary"],
    queryFn: ({ pageParam }) =>
      apiFetch<ClientsResponse>(
        `${BACKEND_URL}/v1/registry/clients/summary?page=${pageParam}&per_page=${CLIENTS_SUMMARY_PER_PAGE}`,
      ),
    initialPageParam: 1,
    getNextPageParam: (lastPage, _allPages, lastPageParam) =>
      lastPage.pagination?.has_next ? lastPageParam + 1 : undefined,
    staleTime: STALE_TIMES.USER_CONTENT,
  });

  return {
    ...result,
    data: result.data?.pages.flatMap((p) => p.data) ?? [],
    hasNextPage: result.hasNextPage,
    isFetchingNextPage: result.isFetchingNextPage,
    fetchNextPage: result.fetchNextPage,
  };
}

export function useClientsSearch(search: string) {
  const term = search.trim();

  const result = useInfiniteQuery({
    queryKey: ["clients", "search", term],
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams({
        page: String(pageParam),
        per_page: String(CLIENTS_SEARCH_PER_PAGE),
        search: term,
      });
      return apiFetch<ClientsResponse>(
        `${BACKEND_URL}/v1/registry/clients?${params.toString()}`,
      );
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage, _allPages, lastPageParam) =>
      lastPage.pagination?.has_next ? lastPageParam + 1 : undefined,
    staleTime: STALE_TIMES.USER_CONTENT,
    enabled: term.length > 0,
  });

  return {
    ...result,
    data: result.data?.pages.flatMap((page) => page.data) ?? [],
    hasNextPage: result.hasNextPage,
    isFetchingNextPage: result.isFetchingNextPage,
    fetchNextPage: result.fetchNextPage,
  };
}
