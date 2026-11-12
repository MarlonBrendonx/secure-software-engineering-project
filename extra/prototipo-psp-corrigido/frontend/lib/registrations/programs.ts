import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../fetch-client";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export interface Program {
  uuid: string;
  client_uuid: string;
  name: string;
  status: string;
}

interface ProgramsResponse {
  success: boolean;
  data: Program[];
}

export function usePrograms(clientUuid: string | null) {
  const result = useQuery({
    queryKey: ["programs", clientUuid],
    queryFn: () =>
      apiFetch<ProgramsResponse>(
        `${BACKEND_URL}/v1/registry/clients/${clientUuid}/programs`,
      ),
    staleTime: 0,
    enabled: !!clientUuid,
  });

  return {
    ...result,
    data: result.data?.data ?? [],
  };
}
