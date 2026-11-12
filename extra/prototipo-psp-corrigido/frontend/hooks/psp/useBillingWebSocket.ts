"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";
import { useAuthContext } from "@/features/auth/lib/auth-context";
import { tryRefresh } from "@/lib/fetch-client";
import type { WSEventMessage } from "@/lib/websocket";
import { useWebSocket } from "@/lib/websocket";

// Escuta o canal do período em exibição e refaz a consulta quando outro usuário altera algo.
export function useBillingWebSocket(year: number | null, month: number | null) {
  const queryClient = useQueryClient();
  const { accessToken, updateToken } = useAuthContext();

  const channel = useMemo(
    () =>
      year != null && month != null
        ? `billing:${year}-${String(month).padStart(2, "0")}`
        : null,
    [year, month],
  );

  const channels = useMemo(() => (channel ? [channel] : []), [channel]);

  const handleMessage = useCallback(
    (msg: WSEventMessage) => {
      if (
        !channel ||
        msg.channel !== channel ||
        msg.event !== "billing_changed"
      )
        return;

      // O aviso não traz dados. Buscar pela API garante que o escopo do usuário vale.
      queryClient.invalidateQueries({ queryKey: ["billings", year, month] });
    },
    [queryClient, year, month, channel],
  );

  const handleTokenExpired = useCallback(async (): Promise<string | null> => {
    const res = await tryRefresh();
    if (!res) return null;
    try {
      const body = (await res.clone().json()) as {
        access_token?: string;
        expires_in?: number;
      };
      if (body.access_token && body.expires_in) {
        updateToken(body.access_token, body.expires_in);
        return body.access_token;
      }
    } catch {
      // Sem token novo, o WebSocket não reconecta.
    }
    return null;
  }, [updateToken]);

  return useWebSocket({
    channels,
    accessToken,
    enabled: channel !== null,
    onMessage: handleMessage,
    onReconnect: () => {
      // Pode ter havido mudança enquanto a conexão estava fora do ar.
      if (year != null && month != null) {
        queryClient.invalidateQueries({ queryKey: ["billings", year, month] });
      }
    },
    onTokenExpired: handleTokenExpired,
  });
}
