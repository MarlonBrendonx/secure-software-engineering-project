export class ApiError extends Error {
  status?: number;
  statusText?: string;
  code?: string;
  data?: Record<string, unknown>;

  constructor(
    message: string,
    opts?: {
      status?: number;
      statusText?: string;
      code?: string;
      data?: Record<string, unknown>;
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = opts?.status;
    this.statusText = opts?.statusText;
    this.code = opts?.code;
    this.data = opts?.data;
  }

  static sessionExpired(): ApiError {
    return new ApiError("Session expired", {
      status: 401,
      code: "SESSION_EXPIRED",
    });
  }
}

const AUTH_BASE = `${(process.env.NEXT_PUBLIC_BACKEND_URL ?? "").replace(/\/$/, "")}/v1/auth`;

let refreshPromise: Promise<Response | null> | null = null;

export async function tryRefresh(): Promise<Response | null> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = fetch(`${AUTH_BASE}/refresh`, {
    method: "POST",
    credentials: "include",
  })
    .then((res) => (res.ok ? res : null))
    .catch(() => null)
    .finally(() => {
      refreshPromise = null;
    });
  return refreshPromise;
}

let onTokenRefreshed: ((token: string, expiresIn: number) => void) | null =
  null;

export function setOnTokenRefreshed(
  cb: ((token: string, expiresIn: number) => void) | null,
) {
  onTokenRefreshed = cb;
}

let apiBlocked = false;

export function setApiBlocked(blocked: boolean): void {
  apiBlocked = blocked;
}

function doFetch(url: string, options: RequestInit, headers: Headers) {
  return fetch(url, { ...options, headers, credentials: "include" });
}

async function parseBody<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

function notifyTokenRefresh(refreshRes: Response): void {
  if (!onTokenRefreshed) return;
  refreshRes
    .clone()
    .json()
    .then((body: { access_token?: string; expires_in?: number }) => {
      if (body.access_token && body.expires_in && onTokenRefreshed) {
        onTokenRefreshed(body.access_token, body.expires_in);
      }
    })
    .catch(() => {
      // Não crítico: a sessão HTTP continua válida pelo cookie mesmo sem atualizar o token em memória.
    });
}

async function handleErrorResponse(response: Response): Promise<never> {
  const { status, statusText } = response;

  if (status >= 500) {
    throw new ApiError(
      "Erro interno do servidor. Tente novamente mais tarde.",
      { status, statusText },
    );
  }

  const errorText = await response.text();
  let errorData: Record<string, unknown>;

  try {
    errorData = JSON.parse(errorText);
  } catch {
    throw new ApiError(`Erro na requisição (${status})`, {
      status,
      statusText,
    });
  }

  // Backend returns { errors: [{ message, field?, occurrences?, rows? }] }
  if (Array.isArray(errorData.errors) && errorData.errors.length > 0) {
    const errors = errorData.errors as Array<{
      code?: string;
      message: string;
      field?: string;
      occurrences?: number;
      rows?: number[];
    }>;
    const messages = errors.map((e) =>
      e.message.replace(/^Value error,\s*/i, ""),
    );
    const hasBulkErrors = errors.some((e) => e.occurrences !== undefined);
    throw new ApiError(messages.join(". "), {
      status,
      statusText,
      code: errorData.code as string | undefined,
      data: hasBulkErrors ? { validationErrors: errors } : undefined,
    });
  }

  const errorField = errorData.error;
  const field =
    typeof errorField === "object"
      ? (errorField as { field?: string })?.field
      : undefined;
  const rawMessage =
    typeof errorField === "string"
      ? errorField
      : ((errorField as { message?: string })?.message ??
        (errorData.message as string) ??
        `Erro na requisição (${status})`);

  const message = field ? `[${field}] ${rawMessage}` : rawMessage;

  // O backend do protótipo põe o código dentro de `error` (ex.: mfa_necessario).
  // Sem ler esse campo, o código de MFA se perde e a UI trata o 401 como sessão expirada.
  const nestedCode =
    typeof errorField === "object"
      ? (errorField as { code?: string })?.code
      : undefined;

  throw new ApiError(message, {
    status,
    statusText,
    code: (errorData.code as string | undefined) ?? nestedCode,
    data: Array.isArray(errorData.conflicts)
      ? { conflicts: errorData.conflicts }
      : undefined,
  });
}

async function refreshAndRetry<T>(
  url: string,
  options: RequestInit,
  headers: Headers,
): Promise<T> {
  const refreshRes = await tryRefresh();
  if (!refreshRes) throw ApiError.sessionExpired();

  notifyTokenRefresh(refreshRes);

  const retryResponse = await doFetch(url, options, headers);

  if (retryResponse.ok) return parseBody<T>(retryResponse);
  return handleErrorResponse(retryResponse);
}

export async function apiFetch<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  if (apiBlocked) {
    throw new ApiError("Acesso não autorizado", {
      status: 403,
      code: "ACCESS_DENIED",
    });
  }

  const headers = new Headers(options.headers);

  // ── Execute request ───────────────────────────────────────────────────
  let response: Response;
  try {
    response = await doFetch(url, options, headers);
  } catch {
    const refreshRes = await tryRefresh().catch(() => null);

    if (refreshRes) {
      notifyTokenRefresh(refreshRes);
      try {
        const retryResponse = await doFetch(url, options, headers);
        if (retryResponse.ok) return parseBody<T>(retryResponse);
        return handleErrorResponse(retryResponse);
      } catch {
        // Retry also failed at network level
      }
    }
    throw new ApiError(
      "Erro de conexão com o servidor. Verifique sua rede e tente novamente.",
      { status: 0, statusText: "Network Error" },
    );
  }

  if (response.status === 401) {
    return refreshAndRetry<T>(url, options, headers);
  }

  if (!response.ok) {
    return handleErrorResponse(response);
  }

  return parseBody<T>(response);
}
