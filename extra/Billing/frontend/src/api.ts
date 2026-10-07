// Cliente da API: cookies HttpOnly (o JavaScript nunca vê o token), cabeçalho
// CSRF em toda requisição que altera dados e renovação automática da sessão.

const BASE = "/api/v1";

export interface Me {
  id: string;
  login: string;
  name: string;
  email: string | null;
  source: "sso" | "local";
  mfa: boolean;
  mfa_enrolled: boolean;
  mfa_enrollment_required: boolean;
  roles: string[];
  roles_pending_mfa: string[];
  permissions: string[];
  permissions_requiring_mfa: string[];
  delegations: { id: string; role: string; titular_id: string; ends_at: string }[];
}

export interface LoginOut {
  status: "authenticated" | "mfa_required";
  me: Me | null;
}

export class ErroApi extends Error {
  constructor(public status: number, public codigo: string, message: string, public extra: Record<string, unknown> = {}) {
    super(message);
  }
}

function csrf(): string {
  return document.cookie.split("; ").find((c) => c.startsWith("nbb_csrf="))?.slice(9) ?? "";
}

interface Opcoes {
  method?: string;
  json?: unknown;
  semRenovar?: boolean;
}

let renovando: Promise<boolean> | null = null;

export function renovar(): Promise<boolean> {
  // Sem o cookie CSRF não há sessão a renovar (tela de login, depois de sair).
  if (!csrf()) return Promise.resolve(false);
  // Várias requisições podem receber 401 ao mesmo tempo: só uma renova.
  renovando ??= fetch(`${BASE}/auth/refresh`, { method: "POST", headers: { "X-CSRF-Token": csrf() } })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => setTimeout(() => (renovando = null), 0));
  return renovando;
}

async function erroDe(r: Response): Promise<ErroApi> {
  let corpo: { detail?: unknown } = {};
  try {
    corpo = await r.json();
  } catch {
    /* corpo vazio */
  }
  const d = corpo.detail;
  if (d && typeof d === "object" && !Array.isArray(d) && "message" in d) {
    const { code, message, ...extra } = d as { code: string; message: string };
    return new ErroApi(r.status, code, message, extra);
  }
  if (Array.isArray(d)) {
    // Erro de validação do FastAPI (422).
    const msgs = d.map((e: { loc?: string[]; msg?: string }) => `${(e.loc ?? []).slice(-1)[0] ?? ""}: ${e.msg ?? ""}`);
    return new ErroApi(r.status, "validation", msgs.join("; "));
  }
  return new ErroApi(r.status, "http_" + r.status, r.status >= 500 ? "Erro no servidor. Tente novamente." : "Falha na requisição.");
}

export async function api<T = unknown>(caminho: string, op: Opcoes = {}): Promise<T> {
  const method = op.method ?? (op.json !== undefined ? "POST" : "GET");
  const headers: Record<string, string> = {};
  if (op.json !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") headers["X-CSRF-Token"] = csrf();
  const r = await fetch(BASE + caminho, {
    method,
    headers,
    body: op.json !== undefined ? JSON.stringify(op.json) : undefined,
    credentials: "same-origin",
  });
  if (r.status === 401 && !op.semRenovar && (await renovar())) {
    return api<T>(caminho, { ...op, semRenovar: true });
  }
  if (!r.ok) throw await erroDe(r);
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

export async function baixar(caminho: string, nome: string): Promise<void> {
  let r = await fetch(BASE + caminho, { credentials: "same-origin" });
  if (r.status === 401 && (await renovar())) r = await fetch(BASE + caminho, { credentials: "same-origin" });
  if (!r.ok) throw await erroDe(r);
  const url = URL.createObjectURL(await r.blob());
  Object.assign(document.createElement("a"), { href: url, download: nome }).click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------- formatação
export const dataHora = (v: string | null | undefined) => (v ? new Date(v).toLocaleString("pt-BR") : "—");
export const data = (v: string | null | undefined) => (v ? new Date(v).toLocaleDateString("pt-BR") : "—");

export const PERFIS: Record<string, string> = {
  none: "Sem perfil",
  analyst: "Analista",
  manager: "Gerente / Coordenador",
  admin: "Administrador",
  auditor: "Auditoria / Controladoria",
};
export const perfil = (c: string) => PERFIS[c] ?? c;
export const PERFIS_ATRIBUIVEIS = ["analyst", "manager", "admin", "auditor"];

export const ERROS_LOGIN: Record<string, string> = {
  domain_not_allowed: "Contas desse domínio de e-mail não têm acesso por este provedor.",
  not_registered: "Seu e-mail não está cadastrado. Peça ao administrador para liberar o acesso.",
  email_not_verified: "O provedor não confirmou o seu e-mail. Use uma conta com e-mail verificado.",
  identity_conflict: "Já existe um usuário com este e-mail vinculado de outra forma. Procure o administrador.",
  user_blocked: "Acesso bloqueado. Procure o administrador.",
  provider_error: "O provedor de login recusou a autenticação. Tente novamente.",
  cancelled: "Login cancelado.",
  expired: "O login demorou demais e expirou. Tente novamente.",
  invalid_state: "Login inválido. Tente novamente.",
  rate_limited: "Muitas tentativas de login. Aguarde um minuto.",
  unknown_provider: "Provedor de login não configurado.",
};
