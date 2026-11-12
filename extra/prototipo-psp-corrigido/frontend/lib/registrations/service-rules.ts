import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  ServiceRange,
  ServiceRule,
  ServiceRuleProgram,
} from "@/components/registrations/service-rules/types";
import { apiFetch } from "../fetch-client";
import { DEFAULT_PER_PAGE } from "../query-config";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

interface Pagination {
  page: number;
  per_page: number;
  total: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

interface ServiceRulesResponse {
  success: boolean;
  data: ServiceRule[];
  pagination: Pagination;
}

export type CreateServiceRulePayload = {
  name: string;
  status: string;
  rule_type: string;
  percentage?: number | null;
  base_value?: number | null;
  requires_client_approval: boolean;
  ranges?: ServiceRange[];
  programs: ServiceRuleProgram[];
};

function rulesUrl(clientUuid: string, ruleUuid?: string): string {
  const base = `${BACKEND_URL}/v1/registry/clients/${clientUuid}/service-rules`;
  return ruleUuid ? `${base}/${ruleUuid}` : base;
}

export function useServiceRules(
  clientUuid: string | null,
  programName?: string,
  serviceName?: string,
  page = 1,
) {
  const result = useQuery({
    queryKey: ["service-rules", clientUuid, programName, serviceName, page],
    queryFn: () => {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("per_page", String(DEFAULT_PER_PAGE));
      if (programName) params.set("program_name", programName);
      if (serviceName) params.set("service_name", serviceName);
      return apiFetch<ServiceRulesResponse>(
        `${rulesUrl(clientUuid as string)}?${params.toString()}`,
      );
    },
    staleTime: 0,
    enabled: !!clientUuid,
  });

  return {
    ...result,
    data: result.data?.data ?? [],
    pagination: result.data?.pagination ?? null,
  };
}

// Mexer numa regra muda as linhas da tela de faturamento (serviço sem lançamento,
// nome, tipo de cálculo), então a lista de lançamentos também é recarregada.
function useInvalidateAfterRuleChange() {
  const queryClient = useQueryClient();
  return (clientUuid: string) => {
    queryClient.invalidateQueries({ queryKey: ["service-rules", clientUuid] });
    queryClient.invalidateQueries({ queryKey: ["billings"] });
  };
}

export function useCreateServiceRule() {
  const invalidate = useInvalidateAfterRuleChange();

  return useMutation({
    mutationFn: ({
      clientUuid,
      data,
    }: {
      clientUuid: string;
      data: CreateServiceRulePayload;
    }) =>
      apiFetch<{ success: boolean; data: ServiceRule }>(rulesUrl(clientUuid), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    onSuccess: (_data, variables) => invalidate(variables.clientUuid),
  });
}

export function useUpdateServiceRule() {
  const invalidate = useInvalidateAfterRuleChange();

  return useMutation({
    mutationFn: ({
      serviceRuleUuid,
      clientUuid,
      data,
      version,
    }: {
      serviceRuleUuid: string;
      clientUuid: string;
      data: CreateServiceRulePayload;
      version: number;
    }) =>
      apiFetch<{ success: boolean; data: ServiceRule }>(
        rulesUrl(clientUuid, serviceRuleUuid),
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...data, version }),
        },
      ),
    onSuccess: (_data, variables) => invalidate(variables.clientUuid),
  });
}

export function useDeleteServiceRule() {
  const invalidate = useInvalidateAfterRuleChange();

  return useMutation({
    mutationFn: ({
      serviceRuleUuid,
      clientUuid,
    }: {
      serviceRuleUuid: string;
      clientUuid: string;
    }) =>
      apiFetch<{ success: boolean }>(rulesUrl(clientUuid, serviceRuleUuid), {
        method: "DELETE",
      }),
    onSuccess: (_data, variables) => invalidate(variables.clientUuid),
  });
}
