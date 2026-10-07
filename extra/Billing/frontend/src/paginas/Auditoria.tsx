import { FormEvent, Fragment, useEffect, useState } from "react";
import { api, baixar, dataHora, ErroApi } from "../api";

interface Evento {
  seq: number;
  occurred_at: string;
  actor_id: string | null;
  actor_login: string | null;
  via_delegation_id: string | null;
  action: string;
  entity: string | null;
  entity_id: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  ip: string | null;
  hash: string;
}

interface Integridade {
  intact: boolean;
  events_checked: number;
  broken_seq?: number;
  reason?: string;
}

const ACOES: Record<string, string> = {
  create: "Criação",
  update: "Alteração",
  delete: "Exclusão",
  "auth.login": "Login",
  "auth.logout": "Logout",
  "auth.login_failed": "Falha de login",
  "auth.mfa_challenge": "Pedido de código 2FA",
  "auth.mfa_failed": "Código 2FA errado",
  "auth.sso_identity_linked": "Conta SSO vinculada",
  "mfa.enrolled": "2FA ativado",
  "mfa.disabled": "2FA desativado",
  "mfa.reset_by_admin": "2FA resetado pelo admin",
  "mfa.recovery_code_used": "Código de recuperação usado",
  "user.terminated": "Desligamento",
  "audit.query": "Consulta à auditoria",
  "audit.verify": "Verificação de integridade",
  "audit.export": "Exportação da auditoria",
  "mfa.code_rejected": "Código 2FA recusado",
  "mfa.recovery_codes_regenerated": "Novos códigos de recuperação",
  "auth.password_reset_requested": "Pedido de nova senha",
  "auth.refresh_reuse_detected": "Reuso de sessão roubada detectado",
  "cli.create_local_user": "Conta local criada (terminal)",
  "cli.bootstrap_admin": "Primeiro admin criado (terminal)",
  "cli.revoke_all_sessions": "Todas as sessões encerradas (terminal)",
  "cli.reencrypt_mfa_secrets": "Segredos 2FA recifrados (terminal)",
};

const MOTIVOS: Record<string, string> = {
  content_altered: "conteúdo alterado",
  prev_hash_mismatch: "encadeamento quebrado",
  missing: "evento removido",
};

type Filtros = { action: string; entity: string; date_from: string; date_to: string };

function params(f: Filtros, extra: Record<string, string> = {}) {
  const p = new URLSearchParams();
  Object.entries({ ...f, ...extra }).forEach(([k, v]) => v && p.set(k, v));
  return p.toString();
}

export default function Auditoria() {
  const vazio: Filtros = { action: "", entity: "", date_from: "", date_to: "" };
  const [filtros, setFiltros] = useState<Filtros>(vazio);
  const [aplicados, setAplicados] = useState<Filtros>(vazio);
  const [eventos, setEventos] = useState<Evento[]>([]);
  const [proximo, setProximo] = useState<number | null>(null);
  const [aberto, setAberto] = useState<number | null>(null);
  const [integridade, setIntegridade] = useState<Integridade | null>(null);
  const [erro, setErro] = useState("");

  async function carregar(f: Filtros, antes?: number) {
    setErro("");
    try {
      const r = await api<{ items: Evento[]; next_before_seq: number | null }>(
        `/audit-events?${params(f, { limit: "50", ...(antes ? { before_seq: String(antes) } : {}) })}`,
      );
      setEventos((atual) => (antes ? [...atual, ...r.items] : r.items));
      setProximo(r.next_before_seq);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível conectar ao servidor.");
    }
  }

  useEffect(() => {
    carregar(vazio);
  }, []);

  const filtrar = (ev: FormEvent) => {
    ev.preventDefault();
    const f = {
      ...filtros,
      date_from: filtros.date_from ? new Date(filtros.date_from).toISOString() : "",
      date_to: filtros.date_to ? new Date(filtros.date_to).toISOString() : "",
    };
    setAplicados(f);
    carregar(f);
  };

  async function verificar() {
    setIntegridade(await api<Integridade>("/audit-events/verify"));
  }

  return (
    <>
      <div className="cabecalho">
        <h2>Trilha de auditoria</h2>
        {integridade && (
          integridade.intact ? (
            <span className="status integro">Íntegra · {integridade.events_checked} eventos conferidos</span>
          ) : (
            <span className="status quebrado">
              Adulteração detectada no evento #{integridade.broken_seq} ({MOTIVOS[integridade.reason ?? ""] ?? integridade.reason})
            </span>
          )
        )}
        <button className="secundario" onClick={verificar}>Verificar integridade</button>
        <button className="secundario" onClick={() => baixar(`/audit-events/export?${params(aplicados)}`, "auditoria.csv")}>Exportar CSV</button>
      </div>

      <form className="painel linha-form" onSubmit={filtrar}>
        <label>Ação<input value={filtros.action} onChange={(e) => setFiltros({ ...filtros, action: e.target.value })} placeholder="ex.: auth.* ou mfa.*" /></label>
        <label>Entidade<input value={filtros.entity} onChange={(e) => setFiltros({ ...filtros, entity: e.target.value })} placeholder="ex.: app_user, setting" /></label>
        <label>De<input type="datetime-local" value={filtros.date_from} onChange={(e) => setFiltros({ ...filtros, date_from: e.target.value })} /></label>
        <label>Até<input type="datetime-local" value={filtros.date_to} onChange={(e) => setFiltros({ ...filtros, date_to: e.target.value })} /></label>
        <button className="primario" style={{ alignSelf: "flex-end" }}>Filtrar</button>
        <button type="button" className="link" style={{ alignSelf: "flex-end" }} onClick={() => { setFiltros(vazio); setAplicados(vazio); carregar(vazio); }}>Limpar</button>
      </form>

      {erro && <div className="erro">{erro}</div>}
      <table>
        <thead><tr><th>#</th><th>Quando</th><th>Quem</th><th>Ação</th><th>Registro</th><th>IP</th><th></th></tr></thead>
        <tbody>
          {eventos.map((e) => (
            <Fragment key={e.seq}>
              <tr>
                <td className="num sutil">{e.seq}</td>
                <td>{dataHora(e.occurred_at)}</td>
                <td>
                  {e.actor_login ?? <span className="sutil">anônimo</span>}
                  {e.via_delegation_id && <div><span className="etiqueta">via substituição</span></div>}
                </td>
                <td>{ACOES[e.action] ?? e.action}</td>
                <td>{e.entity ? <><code>{e.entity}</code><div className="sutil pequeno">{e.entity_id}</div></> : "—"}</td>
                <td className="sutil">{e.ip ?? "—"}</td>
                <td className="acoes-linha">
                  {(e.before || e.after) && (
                    <button className="link" onClick={() => setAberto(aberto === e.seq ? null : e.seq)}>{aberto === e.seq ? "Ocultar" : "Detalhes"}</button>
                  )}
                </td>
              </tr>
              {aberto === e.seq && (
                <tr className="detalhe">
                  <td colSpan={7}>
                    <div className="grade-form">
                      {e.before && <div><div className="sutil pequeno">Antes</div><pre>{JSON.stringify(e.before, null, 2)}</pre></div>}
                      {e.after && <div><div className="sutil pequeno">{e.before ? "Depois" : "Dados"}</div><pre>{JSON.stringify(e.after, null, 2)}</pre></div>}
                    </div>
                    <div className="sutil pequeno" style={{ marginTop: 6 }}>hash {e.hash}</div>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
      {eventos.length === 0 && !erro && <div className="vazio">Nenhum evento encontrado.</div>}
      <div className="paginacao">
        {proximo && <button className="secundario" onClick={() => carregar(aplicados, proximo)}>Carregar mais antigos</button>}
      </div>
    </>
  );
}
