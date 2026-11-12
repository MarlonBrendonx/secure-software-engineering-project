"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  setApiBlocked,
  setOnTokenRefreshed,
  tryRefresh,
} from "@/lib/fetch-client";
import type { SessionUser, UserRole } from "./auth-client";
import { SessionSchema, TokenRefreshSchema } from "./schemas";

const VALID_ROLES = new Set<UserRole>(["admin", "manager", "analyst"]);

function parseRole(raw: string | undefined | null): UserRole {
  if (raw && VALID_ROLES.has(raw as UserRole)) return raw as UserRole;
  return "none";
}

interface AuthState {
  user: SessionUser | null;
  accessToken: string | null;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  setAuth: (user: SessionUser, accessToken: string, expiresIn: number) => void;
  clearAuth: () => void;
  updateToken: (accessToken: string, expiresIn: number) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const AUTH_BASE = `${(process.env.NEXT_PUBLIC_BACKEND_URL ?? "").replace(/\/$/, "")}/v1/auth`;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    accessToken: null,
    isLoading: true,
  });

  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );
  // Tracks whether the /refresh endpoint works. If it fails once, we stop
  // proactive scheduling to avoid flooding the backend with 401s.
  // Reactive refresh (fetch-client 401 handler) still works via cookies.
  const refreshAvailableRef = useRef(true);

  const scheduleRefresh = useCallback((expiresIn: number) => {
    clearTimeout(refreshTimerRef.current);
    if (!refreshAvailableRef.current) return;

    const ms = Math.max((expiresIn - 30) * 1000, 10_000);
    refreshTimerRef.current = setTimeout(async () => {
      const res = await tryRefresh();
      if (res) {
        const parsed = TokenRefreshSchema.safeParse(
          await res
            .clone()
            .json()
            .catch(() => null),
        );
        if (!parsed.success) {
          refreshAvailableRef.current = false;
          return;
        }
        setState((prev) => ({
          ...prev,
          accessToken: parsed.data.access_token,
        }));
        scheduleRefresh(parsed.data.expires_in);
      } else {
        // /refresh returned 401 or failed — stop proactive scheduling
        refreshAvailableRef.current = false;
      }
    }, ms);
  }, []);

  const setAuth = useCallback(
    (user: SessionUser, accessToken: string, expiresIn: number) => {
      setState({ user, accessToken, isLoading: false });
      scheduleRefresh(expiresIn);
    },
    [scheduleRefresh],
  );

  const clearAuth = useCallback(() => {
    clearTimeout(refreshTimerRef.current);
    setState({ user: null, accessToken: null, isLoading: false });
  }, []);

  const updateToken = useCallback(
    (accessToken: string, expiresIn: number) => {
      refreshAvailableRef.current = true;
      setState((prev) => ({ ...prev, accessToken }));
      scheduleRefresh(expiresIn);
    },
    [scheduleRefresh],
  );

  useEffect(() => {
    setOnTokenRefreshed((token, expiresIn) => {
      updateToken(token, expiresIn);
    });
    return () => setOnTokenRefreshed(null);
  }, [updateToken]);

  useEffect(() => {
    setApiBlocked(state.user?.role === "none");
  }, [state.user?.role]);

  useEffect(() => {
    let cancelled = false;

    async function checkSession() {
      try {
        const res = await fetch(`${AUTH_BASE}/get-session`, {
          credentials: "include",
        });
        if (!res.ok || cancelled) {
          setState({ user: null, accessToken: null, isLoading: false });
          return;
        }
        const parsed = SessionSchema.safeParse(
          await res.json().catch(() => null),
        );
        if (!parsed.success || cancelled) {
          setState({ user: null, accessToken: null, isLoading: false });
          return;
        }
        const data = parsed.data;

        const user: SessionUser = {
          id: data.username,
          username: data.username,
          name: data.display_name,
          display_name: data.display_name,
          email: data.email ?? data.username,
          role: parseRole(data.role),
        };

        // get-session não devolve access_token, então chamamos /refresh para obtê-lo.
        const refreshRes = await tryRefresh();
        if (cancelled) return;

        if (refreshRes) {
          try {
            const body = (await refreshRes.clone().json()) as {
              access_token?: string;
              expires_in?: number;
            };
            if (body.access_token && body.expires_in) {
              refreshAvailableRef.current = true;
              setState({
                user,
                accessToken: body.access_token,
                isLoading: false,
              });
              scheduleRefresh(body.expires_in);
              return;
            }
          } catch {
            // Fall through to stored token fallback
          }
        } else {
          // /refresh endpoint failed — don't attempt proactive refreshes
          refreshAvailableRef.current = false;
        }

        setState({ user, accessToken: null, isLoading: false });
      } catch {
        if (!cancelled) {
          setState({ user: null, accessToken: null, isLoading: false });
        }
      }
    }

    checkSession();
    return () => {
      cancelled = true;
    };
  }, [scheduleRefresh]);

  // Cleanup refresh timer
  useEffect(() => {
    return () => clearTimeout(refreshTimerRef.current);
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, setAuth, clearAuth, updateToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuthContext must be used within an AuthProvider");
  }
  return ctx;
}
