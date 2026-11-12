"use client";

import { type UserRole, useSession } from "@/features/auth/lib/auth-client";

export function useUserRole() {
  const { data: session } = useSession();
  const role: UserRole = session?.user?.role ?? "none";
  const displayName = session?.user?.display_name ?? session?.user?.name;

  return {
    role,
    displayName,
    // Cadastro de regras de serviço: escrita só do admin (a API aplica a mesma regra).
    canManageServiceRules: role === "admin",
    billing: {
      canSendToApproval: role === "admin" || role === "analyst",
      canApproveOrReject: role === "admin" || role === "manager",
    },
  };
}
