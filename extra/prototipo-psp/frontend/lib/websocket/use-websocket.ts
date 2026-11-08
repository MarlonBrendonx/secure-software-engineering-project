"use client";

import { useCallback, useEffect, useRef } from "react";
import type { WSAuthMessage, WSControlMessage, WSEventMessage } from "./types";
import { WS_CLOSE_CODES } from "./types";

const WS_BASE_URL = (
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"
)
  .replace(/\/$/, "")
  .replace(/^http/, "ws");

const MAX_RETRIES = 5;
const MAX_BACKOFF_MS = 30_000;

export type WSMessageHandler = (msg: WSEventMessage) => void;

interface UseWebSocketOptions {
  channels: string[];
  accessToken: string | null;
  onMessage: WSMessageHandler;
  onAuthError?: (reason: string) => void;
  onReconnect?: () => void;
  // Devolve o token novo (ou null se a renovação falhou). Não dá para ler o token de volta
  // pelo ref: ele só atualiza no próximo render, depois que a renovação já terminou.
  onTokenExpired?: () =>
    | Promise<string | null | undefined>
    | string
    | null
    | undefined;
  enabled?: boolean;
}

export function useWebSocket({
  channels,
  accessToken,
  onMessage,
  onAuthError,
  onReconnect,
  onTokenExpired,
  enabled = true,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );
  const isReconnectRef = useRef(false);
  const authFailedRef = useRef(false);

  // Callbacks em refs: trocar um callback não pode derrubar e refazer a conexão.
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  const onAuthErrorRef = useRef(onAuthError);
  onAuthErrorRef.current = onAuthError;
  const onReconnectRef = useRef(onReconnect);
  onReconnectRef.current = onReconnect;
  const onTokenExpiredRef = useRef(onTokenExpired);
  onTokenExpiredRef.current = onTokenExpired;

  // O token só é usado no handshake. Renovar o token não deve reconectar: o back
  // encerra a conexão com 4003 quando o token expira, e aí reconectamos com o novo.
  const accessTokenRef = useRef(accessToken);
  accessTokenRef.current = accessToken;

  const hasToken = !!accessToken;

  useEffect(() => {
    if (!enabled || !hasToken) return;

    let cleaned = false;
    // Zera a falha de auth: permite reconectar depois de um novo login.
    authFailedRef.current = false;

    function connect(freshToken?: string) {
      if (cleaned || authFailedRef.current) return;

      const token = freshToken ?? accessTokenRef.current;
      if (!token) return;
      // Recusa do handshake (auth_error) é definitiva; expiração fecha com 4003 sem auth_error.
      let rejected = false;

      const ws = new WebSocket(`${WS_BASE_URL}/ws`);

      ws.onopen = () => {
        if (cleaned) {
          ws.close(WS_CLOSE_CODES.NORMAL);
          return;
        }

        retriesRef.current = 0;

        // O token vai na primeira mensagem, não na URL: URL aparece em log de proxy.
        const authMsg: WSAuthMessage = { type: "auth", token, channels };
        ws.send(JSON.stringify(authMsg));
      };

      ws.onmessage = (evt) => {
        if (cleaned) return;

        try {
          const msg = JSON.parse(evt.data);

          if (msg.type === "auth_ok") {
            if (isReconnectRef.current) {
              onReconnectRef.current?.();
            }
            isReconnectRef.current = true;
            return;
          }

          if (msg.type === "auth_error") {
            const ctrl = msg as WSControlMessage & { type: "auth_error" };
            // Token inválido ou sem MFA: reconectar só repetiria a recusa (e o alerta no back).
            rejected = true;
            authFailedRef.current = true;
            onAuthErrorRef.current?.(ctrl.reason);
            return;
          }

          onMessageRef.current(msg as WSEventMessage);
        } catch {
          // Mensagem malformada: ignora.
        }
      };

      ws.onclose = (evt) => {
        wsRef.current = null;

        if (cleaned || authFailedRef.current) return;

        // 4003 sem auth_error: o token expirou ou a sessão foi revogada.
        if (evt.code === WS_CLOSE_CODES.TOKEN_EXPIRED && !rejected) {
          (async () => {
            // O auth-context renova o token antes de expirar: se o ref já tem outro token,
            // basta reconectar com ele, sem pedir uma renovação a mais.
            let next: string | null | undefined = accessTokenRef.current;
            if (!next || next === token) {
              try {
                next = await onTokenExpiredRef.current?.();
              } catch {
                next = null;
              }
            }

            if (cleaned) return;

            if (next && next !== token) {
              retriesRef.current = 0;
              connect(next);
            } else {
              // Sem token novo a sessão acabou; reconectar só repetiria a recusa.
              authFailedRef.current = true;
            }
          })();
          return;
        }

        // Queda de rede ou fechamento inesperado: tenta de novo com espera crescente.
        if (retriesRef.current < MAX_RETRIES) {
          const delay = Math.min(
            1000 * 2 ** retriesRef.current,
            MAX_BACKOFF_MS,
          );
          retriesRef.current++;
          reconnectTimerRef.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        // O onclose roda logo depois do onerror; a reconexão fica lá.
      };

      wsRef.current = ws;
    }

    connect();

    return () => {
      cleaned = true;
      clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close(WS_CLOSE_CODES.NORMAL);
      wsRef.current = null;
    };
  }, [enabled, hasToken, channels]);

  const subscribe = useCallback((channel: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(`subscribe:${channel}`);
    }
  }, []);

  const unsubscribe = useCallback((channel: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(`unsubscribe:${channel}`);
    }
  }, []);

  return { subscribe, unsubscribe };
}
