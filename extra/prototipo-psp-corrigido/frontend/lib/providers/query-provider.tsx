"use client";

import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { ReactQueryStreamedHydration } from "@tanstack/react-query-next-experimental";
import type { ReactNode } from "react";
import { toast } from "sonner";
import { redirectToLogin } from "@/features/auth/lib/auth-client";
import { getQueryClient as getBaseQueryClient } from "../get-query-client";

interface ErrorWithStatus extends Error {
  status?: number;
  code?: string;
}

function getErrorStatus(error: unknown): number | undefined {
  if (error && typeof error === "object" && "status" in error) {
    return (error as ErrorWithStatus).status;
  }
  return undefined;
}

function getErrorCode(error: unknown): string | undefined {
  if (error && typeof error === "object" && "code" in error) {
    return (error as ErrorWithStatus).code;
  }
  return undefined;
}

// 401 with MFA code means the session is valid but lacks a second factor.
// Redirecting to login would hide the backend message, so it is excluded here.
const MFA_REQUIRED_CODE = "mfa_necessario";

function isSessionExpired(
  status: number | undefined,
  code: string | undefined,
) {
  if (code === MFA_REQUIRED_CODE) return false;
  return status === 401 || code === "SESSION_EXPIRED";
}

let signingOut = false;

function handleUnauthorized() {
  if (signingOut) return;
  signingOut = true;
  toast.error("Sessão expirada", {
    description: "Você será redirecionado para o login.",
  });
  setTimeout(() => {
    redirectToLogin();
  }, 2000);
}

const queryCache = new QueryCache({
  onError: (error, query) => {
    if (query.meta?.errorMessage === false) return;

    const status = getErrorStatus(error);
    const code = getErrorCode(error);

    if (isSessionExpired(status, code)) {
      handleUnauthorized();
      return;
    }
    if (status === 404) return;

    if (status === 403 || code === "INSUFFICIENT_PERMISSIONS") {
      toast.error("Acesso negado", {
        description: "Você não tem permissão para acessar este recurso.",
      });
      return;
    }

    const isNetworkError = status === 0;

    toast.error("Erro ao carregar dados", {
      description: error instanceof Error ? error.message : "Erro desconhecido",
      ...(isNetworkError && { id: "network-error" }),
    });
  },
});

const mutationCache = new MutationCache({
  onError: (error, _variables, _context, mutation) => {
    if (mutation.meta?.errorMessage === false) return;

    const status = getErrorStatus(error);
    const code = getErrorCode(error);

    if (isSessionExpired(status, code)) {
      handleUnauthorized();
      return;
    }

    if (status === 403 || code === "INSUFFICIENT_PERMISSIONS") {
      toast.error("Acesso negado", {
        description: "Você não tem permissão para realizar esta ação.",
      });
      return;
    }

    const isNetworkError = status === 0;
    toast.error("Erro", {
      description: error instanceof Error ? error.message : "Erro inesperado",
      ...(isNetworkError && { id: "network-error" }),
    });
  },
});

let clientQueryClient: QueryClient | undefined;

function getClientQueryClient() {
  if (!clientQueryClient) {
    const baseClient = getBaseQueryClient();
    clientQueryClient = new QueryClient({
      queryCache,
      mutationCache,
      defaultOptions: baseClient.getDefaultOptions(),
    });
  }
  return clientQueryClient;
}

interface QueryProviderProps {
  children: ReactNode;
}

export function QueryProvider({ children }: QueryProviderProps) {
  const queryClient = getClientQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <ReactQueryStreamedHydration>{children}</ReactQueryStreamedHydration>
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
