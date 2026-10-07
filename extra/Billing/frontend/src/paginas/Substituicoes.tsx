import { FormEvent, useEffect, useMemo, useState } from "react";
import { api, data, ErroApi, Me, perfil } from "../api";
import type { Usuario } from "./Usuarios";

interface Delegacao {
  id: string;
  titular_id: string;
  substitute_id: string;
  role_code: string;
  starts_at: string;
  ends_at: string;
  justification: string;
  document_ref: string | null;
  granted_by: string;
  revoked_at: string | null;
  active: boolean;
}

const msg = (e: unknown) => (e instanceof ErroApi ? e.message : "Não foi possível conectar ao servidor.");
const local = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);

export default function Substituicoes({ me }: { me: Me }) {
  const [lista, setLista] = useState<Delegacao[]>([]);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [criando, setCriando] = useState(false);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const amanha = new Date(Date.now() + 15 * 86400000);
  const [f, setF] = useState({
    titular_id: "", substitute_id: "", role_code: "", starts_at: local(new Date()), ends_at: local(amanha),
    justification: "", document_ref: "",
  });

  const porId = useMemo(() => Object.fromEntries(usuarios.map((u) => [u.id, u])), [usuarios]);
  const ativos = usuarios.filter((u) => u.status === "active");
  const titulares = ativos.filter((u) => u.roles.length > 0);
  const titular = porId[f.titular_id];

  const carregar = async () => {
    try {
      const [d, u] = await Promise.all([api<Delegacao[]>("/delegations"), api<Usuario[]>("/users")]);
      setLista(d);
      setUsuarios(u);
    } catch (e) {
      setErro(msg(e));
    }
  };
  useEffect(() => {
    carregar();
  }, []);

  async function salvar(ev: FormEvent) {
    ev.preventDefault();
    setErro("");
    try {
      await api("/delegations", {
        json: {
          ...f,
          starts_at: new Date(f.starts_at).toISOString(),
          ends_at: new Date(f.ends_at).toISOString(),
          document_ref: f.document_ref || null,
        },
      });
      setCriando(false);
      setAviso("Substituição concedida. A permissão vale só dentro do período informado.");
      carregar();
    } catch (e) {
      setErro(msg(e));
    }
  }

  async function revogar(d: Delegacao) {
    if (!window.confirm("Encerrar esta substituição agora?")) return;
    try {
      await api(`/delegations/${d.id}/revoke`, { method: "POST" });
      setAviso("Substituição encerrada.");
      carregar();
    } catch (e) {
      setErro(msg(e));
    }
  }

  const nome = (id: string) => porId[id]?.name ?? "—";
  const situacao = (d: Delegacao) =>
    d.revoked_at ? ["encerrado", "Revogada"] : d.active ? ["ativo", "Ativa"] : new Date(d.starts_at) > new Date() ? ["pendente", "Agendada"] : ["encerrado", "Encerrada"];

  return (
    <>
      <div className="cabecalho">
        <h2>Substituições em férias</h2>
        <span className="contador">{(() => { const n = lista.filter((d) => d.active).length; return `${n} ${n === 1 ? "ativa" : "ativas"}`; })()}</span>
        {!criando && <button className="primario" onClick={() => setCriando(true)}>Nova substituição</button>}
      </div>
      <p className="sutil" style={{ marginTop: -8, marginBottom: 16 }}>
        O substituto recebe temporariamente um perfil do titular. As ações dele ficam registradas no nome dele, com referência a esta substituição.
      </p>
      {aviso && <div className="aviso">{aviso}</div>}
      {erro && <div className="erro">{erro}</div>}

      {criando && (
        <form className="painel grade-form" onSubmit={salvar}>
          <h3>Nova substituição</h3>
          <label>
            Titular (quem sai de férias)
            <select value={f.titular_id} onChange={(e) => setF({ ...f, titular_id: e.target.value, role_code: "" })} required>
              <option value="">Selecione…</option>
              {titulares.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
          </label>
          <label>
            Perfil delegado
            <select value={f.role_code} onChange={(e) => setF({ ...f, role_code: e.target.value })} required disabled={!titular}>
              <option value="">Selecione…</option>
              {titular?.roles.map((r) => <option key={r} value={r}>{perfil(r)}</option>)}
            </select>
          </label>
          <label>
            Substituto
            <select value={f.substitute_id} onChange={(e) => setF({ ...f, substitute_id: e.target.value })} required>
              <option value="">Selecione…</option>
              {ativos.filter((u) => u.id !== f.titular_id && u.id !== me.id).map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
          </label>
          <label>Início<input type="datetime-local" value={f.starts_at} onChange={(e) => setF({ ...f, starts_at: e.target.value })} required /></label>
          <label>Término<input type="datetime-local" value={f.ends_at} onChange={(e) => setF({ ...f, ends_at: e.target.value })} required /></label>
          <label>Documento (opcional)<input value={f.document_ref} onChange={(e) => setF({ ...f, document_ref: e.target.value })} placeholder="Ex.: memorando 12/2026" /></label>
          <label className="largura-total">
            Justificativa
            <textarea value={f.justification} onChange={(e) => setF({ ...f, justification: e.target.value })} minLength={5} required placeholder="Ex.: férias do titular de 10 a 24/10" />
          </label>
          <div className="acoes largura-total">
            <button type="button" className="secundario" onClick={() => setCriando(false)}>Cancelar</button>
            <button className="primario">Conceder</button>
          </div>
        </form>
      )}

      {lista.length === 0 ? (
        <div className="vazio">Nenhuma substituição registrada.</div>
      ) : (
        <table>
          <thead><tr><th>Titular</th><th>Substituto</th><th>Perfil</th><th>Período</th><th>Justificativa</th><th>Situação</th><th></th></tr></thead>
          <tbody>
            {lista.map((d) => {
              const [cls, rot] = situacao(d);
              return (
                <tr key={d.id} className={cls === "encerrado" ? "inativo" : ""}>
                  <td>{nome(d.titular_id)}</td>
                  <td><strong>{nome(d.substitute_id)}</strong></td>
                  <td>{perfil(d.role_code)}</td>
                  <td>{data(d.starts_at)} a {data(d.ends_at)}</td>
                  <td>{d.justification}{d.document_ref && <div className="sutil pequeno">{d.document_ref}</div>}</td>
                  <td><span className={`status ${cls}`}>{rot}</span></td>
                  <td className="acoes-linha">{!d.revoked_at && new Date(d.ends_at) > new Date() && <button className="link perigo" onClick={() => revogar(d)}>Encerrar</button>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </>
  );
}
