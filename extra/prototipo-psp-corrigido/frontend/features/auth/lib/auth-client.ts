"use client";

import { useAuthContext } from "./auth-context";

const AUTH_BASE = `${(process.env.NEXT_PUBLIC_BACKEND_URL ?? "").replace(/\/$/, "")}/v1/auth`;

// ─── Types ────────────────────────────────────────────────────────────────

export type UserRole = "admin" | "manager" | "analyst" | "none";

export type SessionUser = {
  id: string;
  username?: string;
  name?: string;
  display_name?: string;
  email?: string;
  image?: string;
  role: UserRole;
};

export type Session = { user: SessionUser } | null;

// ─── Sign-in ──────────────────────────────────────────────────────────────

export interface SignInResult {
  user?: SessionUser;
  accessToken?: string;
  expiresIn?: number;
  error?: { message: string };
}

function decodeJwtClaims(token: string): {
  sub?: string;
  role?: string;
  display_name?: string;
  email?: string;
} | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json) as {
      sub?: string;
      role?: string;
      display_name?: string;
      email?: string;
    };
  } catch {
    return null;
  }
}

// otp é o segundo fator do protótipo (mock). Vai no body só quando preenchido,
// assim o login sem MFA continua enviando o mesmo payload de antes.
export async function signIn(opts: {
  username: string;
  password: string;
  otp?: string;
}): Promise<SignInResult> {
  if (!AUTH_BASE.startsWith("http")) {
    return { error: { message: "Backend URL not configured" } };
  }

  const res = await fetch(`${AUTH_BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: opts.username,
      password: opts.password,
      ...(opts.otp ? { otp: opts.otp } : {}),
    }),
    credentials: "include",
  });

  const body = (await res.json().catch(() => ({}))) as {
    access_token?: string;
    token?: string;
    token_type?: string;
    expires_in?: number;
    refresh_token?: string | null;
    user?: {
      username: string;
      name?: string;
      email?: string;
      role?: string;
      display_name?: string;
    };
    error?: { code?: string; message?: string } | string;
  };

  if (!res.ok) {
    const msg =
      typeof body.error === "object" && body.error?.message
        ? body.error.message
        : typeof body.error === "string"
          ? body.error
          : "Login failed";
    return { error: { message: String(msg) } };
  }

  const accessToken = body.access_token ?? body.token;

  if (!accessToken) {
    return { error: { message: "No access_token in response" } };
  }

  let user = body.user;
  if (!user) {
    const claims = decodeJwtClaims(accessToken);
    if (claims?.sub) {
      user = {
        username: claims.sub,
        role: claims.role,
        display_name: claims.display_name,
        email: claims.email,
      };
    }
  }

  if (!user) {
    return { error: { message: "No user info in login response" } };
  }

  const sessionUser: SessionUser = {
    id: user.username,
    username: user.username,
    name: user.display_name ?? user.name,
    display_name: user.display_name,
    email: user.email ?? user.username,
    role: (user.role as UserRole) ?? "none",
  };

  const expiresIn = body.expires_in ?? 300;

  // O backend já gravou o cookie HttpOnly. Não espelhamos o token em document.cookie:
  // isso o deixaria legível por qualquer script da página (XSS).
  return {
    user: sessionUser,
    accessToken,
    expiresIn,
  };
}

export async function signOut(): Promise<void> {
  try {
    await fetch(`${AUTH_BASE}/logout`, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    // Silencioso — redirect acontece de qualquer forma
  }

  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

export function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  const currentPath = window.location.pathname + window.location.search;
  const loginUrl =
    currentPath && currentPath !== "/" && currentPath !== "/login"
      ? `/login?callbackUrl=${encodeURIComponent(currentPath)}`
      : "/login";
  window.location.href = loginUrl;
}

// ─── Hooks ────────────────────────────────────────────────────────────────

export function useSession(): { data: Session; isPending: boolean } {
  const { user, isLoading } = useAuthContext();
  return {
    data: user ? { user } : null,
    isPending: isLoading,
  };
}
