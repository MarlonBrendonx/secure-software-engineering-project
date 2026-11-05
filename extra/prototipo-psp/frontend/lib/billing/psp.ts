import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import type {
  BatchStatusPayload,
  BatchStatusResponse,
  BillingAverageResponse,
  BillingHistoryEntry,
  BillingItemHistoryEntry,
  BillingListPagination,
  BillingListResponse,
  ChangeBillingStatusPayload,
  CreateBillingItemPayload,
  ReplicateBillingItemPayload,
  UpdateBillingItemPayload,
} from "@/components/psp/types";
import { apiStatusToLabel, labelToApiStatus } from "@/utils/psp/statusMap";
import { apiFetch } from "../fetch-client";
import { STALE_TIMES } from "../query-config";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

const PER_PAGE = 5;

export function useBillings(
  year: number | null,
  month: number | null,
  page: number,
  clientName?: string,
) {
  const result = useQuery({
    queryKey: ["billings", year, month, page, clientName ?? ""],
    queryFn: () => {
      const params = new URLSearchParams({
        year: String(year!),
        month: String(month!),
        page: String(page),
        per_page: String(PER_PAGE),
      });
      if (clientName) params.set("client_name", clientName);
      return apiFetch<BillingListResponse>(
        `${BACKEND_URL}/v1/billing?${params}`,
      );
    },
    enabled: year !== null && month !== null,
    staleTime: STALE_TIMES.USER_CONTENT,
    placeholderData: (prev) => prev,
  });

  const clients = useMemo(
    () =>
      result.data?.data.map((client) => ({
        ...client,
        services: client.services.map((s) => ({
          ...s,
          status: apiStatusToLabel(s.status),
          total_value: s.total_value != null ? Number(s.total_value) : null,
          billing_total_value:
            s.billing_total_value != null
              ? Number(s.billing_total_value)
              : null,
        })),
      })) ?? [],
    [result.data],
  );

  const statusSummary = useMemo(
    () =>
      result.data?.status_summary.map((s) => ({
        ...s,
        status: apiStatusToLabel(s.status),
        total_value: Number(s.total_value),
      })) ?? [],
    [result.data],
  );

  const pagination: BillingListPagination | null =
    result.data?.pagination ?? null;

  return {
    clients,
    statusSummary,
    pagination,
    isLoading: result.isLoading,
    isError: result.isError,
    refetch: result.refetch,
  };
}

export function useBillingAverage(
  clientUuid: string | null,
  year: number,
  month: number,
) {
  const result = useQuery({
    queryKey: ["billing-average", clientUuid, year, month],
    queryFn: () =>
      apiFetch<BillingAverageResponse>(
        `${BACKEND_URL}/v1/billing/clients/${clientUuid}/average?year=${year}&month=${month}`,
      ),
    staleTime: STALE_TIMES.USER_CONTENT,
    enabled: !!clientUuid,
    select: (data) => {
      const map = new Map<string, number>();
      for (const [serviceRuleUuid, avg] of Object.entries(data.data)) {
        map.set(serviceRuleUuid, avg);
      }
      return map;
    },
  });

  return {
    averageMap: result.data ?? new Map<string, number>(),
    isLoading: result.isLoading,
  };
}

export function useBillingHistory(billingUuid: string | null) {
  return useQuery({
    queryKey: ["billing-history", billingUuid],
    queryFn: () =>
      apiFetch<{ data: BillingHistoryEntry[] }>(
        `${BACKEND_URL}/v1/billing/${billingUuid}/history`,
      ),
    staleTime: STALE_TIMES.USER_CONTENT,
    enabled: !!billingUuid,
    select: (response) =>
      response.data.map((entry) => ({
        id: entry.uuid,
        billingId: billingUuid as string,
        previousStatus: entry.previous_status
          ? apiStatusToLabel(entry.previous_status)
          : null,
        newStatus: apiStatusToLabel(entry.new_status),
        notes: entry.notes ?? "",
        changedBy: entry.changed_by ?? null,
        created_at: entry.created_at,
        changes: entry.changes ?? null,
      })),
  });
}

export function useItemHistory(itemUuid: string | null, status?: string) {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";

  return useQuery({
    queryKey: ["item-history", itemUuid, status ?? null],
    queryFn: () =>
      apiFetch<{ data: BillingItemHistoryEntry[] }>(
        `${BACKEND_URL}/v1/billing/items/${itemUuid}/history${query}`,
      ),
    staleTime: STALE_TIMES.USER_CONTENT,
    enabled: !!itemUuid,
    select: (response) =>
      response.data.map((entry) => ({
        id: entry.uuid,
        itemId: entry.billing_item_uuid,
        action: entry.action,
        previousStatus: entry.previous_status
          ? apiStatusToLabel(entry.previous_status)
          : null,
        newStatus: apiStatusToLabel(entry.new_status),
        notes: entry.notes ?? "",
        changedBy: entry.changed_by ?? null,
        created_at: entry.created_at,
        changes: entry.changes ?? null,
      })),
  });
}

export function useCreateBillingItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateBillingItemPayload) =>
      apiFetch<{ data: unknown; warnings?: unknown[] }>(
        `${BACKEND_URL}/v1/billing/items`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billings"] });
    },
  });
}

export function useUpdateBillingItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      uuid,
      data,
    }: {
      uuid: string;
      data: UpdateBillingItemPayload;
    }) =>
      apiFetch<{ data: unknown; warnings?: unknown[] }>(
        `${BACKEND_URL}/v1/billing/items/${uuid}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billings"] });
    },
  });
}

export function useDeleteBillingItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (uuid: string) =>
      apiFetch<void>(`${BACKEND_URL}/v1/billing/items/${uuid}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billings"] });
    },
  });
}

export function useReplicateBillingItems() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ReplicateBillingItemPayload) =>
      apiFetch<{ data: unknown[] }>(
        `${BACKEND_URL}/v1/billing/items/replicate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billings"] });
    },
  });
}

export function useChangeBillingStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      itemUuid,
      data,
    }: {
      itemUuid: string;
      data: ChangeBillingStatusPayload;
    }) =>
      apiFetch<{ data: unknown }>(
        `${BACKEND_URL}/v1/billing/items/${itemUuid}/status`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...data,
            new_status: labelToApiStatus(data.new_status),
          }),
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billings"] });
      queryClient.invalidateQueries({ queryKey: ["billing-history"] });
      queryClient.invalidateQueries({ queryKey: ["item-history"] });
    },
  });
}

export function useBatchBillingStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: BatchStatusPayload) =>
      apiFetch<BatchStatusResponse>(
        `${BACKEND_URL}/v1/billing/items/batch-status`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...data,
            new_status: labelToApiStatus(data.new_status),
          }),
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billings"] });
      queryClient.invalidateQueries({ queryKey: ["billing-history"] });
    },
  });
}
