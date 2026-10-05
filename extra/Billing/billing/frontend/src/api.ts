// Cliente HTTP. Os tokens ficam em cookies HttpOnly: o JavaScript nunca os vê.
// Em 401, tenta renovar a sessão uma vez; se não der, avisa a aplicação para voltar ao login.

export type Papel = "ADMINISTRADOR" | "OPERACIONAL" | "GESTOR" | "AUDITOR" | "OPERACAO";

export interface Usuario {
  id: number;
  login: string;
  nome: string;
  papel: Papel;
}

export class ErroApi extends Error {
  constructor(public status: number, mensagem: string) {
    super(mensagem);
  }
}

let aoExpirar: () => void = () => {};
export function definirAoExpirar(fn: () => void) {
  aoExpirar = fn;
}

function mensagem(corpo: unknown, status: number): string {
  const d = (corpo as { detail?: unknown })?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((e) => `${(e.loc ?? []).slice(-1)[0] ?? ""}: ${e.msg}`).join("; ");
  return `Erro ${status}`;
}

let renovando: Promise<boolean> | null = null;
export function renovar(): Promise<boolean> {
  renovando ??= fetch("/api/auth/renovar", { method: "POST", credentials: "same-origin" })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => setTimeout(() => (renovando = null), 0));
  return renovando;
}

export async function api<T = unknown>(caminho: string, opcoes: RequestInit & { json?: unknown } = {}, tentou = false): Promise<T> {
  const { json, ...resto } = opcoes;
  const r = await fetch("/api" + caminho, {
    credentials: "same-origin",
    ...resto,
    headers: json !== undefined ? { "Content-Type": "application/json", ...resto.headers } : resto.headers,
    body: json !== undefined ? JSON.stringify(json) : resto.body,
  });
  if (r.status === 401 && !caminho.startsWith("/auth/") && !tentou) {
    if (await renovar()) return api<T>(caminho, opcoes, true);
    aoExpirar();
  }
  if (r.status === 204) return undefined as T;
  const tipo = r.headers.get("content-type") ?? "";
  const corpo = tipo.includes("json") ? await r.json() : await r.text();
  if (!r.ok) throw new ErroApi(r.status, mensagem(corpo, r.status));
  return corpo as T;
}

export async function baixar(caminho: string, nomePadrao: string) {
  let r = await fetch("/api" + caminho, { credentials: "same-origin" });
  if (r.status === 401 && (await renovar())) r = await fetch("/api" + caminho, { credentials: "same-origin" });
  if (!r.ok) throw new ErroApi(r.status, "Falha no download");
  const nome = /filename="([^"]+)"/.exec(r.headers.get("content-disposition") ?? "")?.[1] ?? nomePadrao;
  const url = URL.createObjectURL(await r.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: nome });
  a.click();
  URL.revokeObjectURL(url);
}

export const moeda = (v: string | number) =>
  Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export const dataHora = (v: string) => new Date(v.endsWith("Z") || v.includes("+") ? v : v + "Z").toLocaleString("pt-BR");

export function periodoAtual(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}
