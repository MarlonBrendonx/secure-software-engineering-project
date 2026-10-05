import { FormEvent, Fragment, useEffect, useState } from "react";
import { api, baixar, dataHora } from "../api";

interface Registro {
  id: number;
  data_hora: string;
  login: string | null;
  papel: string | null;
  ip: string | null;
  tipo_acao: string;
  entidade: string | null;
  entidade_id: string | null;
  detalhes: Record<string, unknown> | null;
}

const POR_PAGINA = 50;

export default function Auditoria() {
  const [tipos, setTipos] = useState<{ tipos_acao: string[]; papeis: string[] }>({ tipos_acao: [], papeis: [] });
  const [filtro, setFiltro] = useState({ login: "", papel: "", tipo_acao: "", entidade: "", de: "", ate: "" });
  const [pagina, setPagina] = useState(0);
  const [dados, setDados] = useState<{ total: number; itens: Registro[] }>({ total: 0, itens: [] });
  const [aberto, setAberto] = useState<number | null>(null);

  const params = () => {
    const p = new URLSearchParams();
    Object.entries(filtro).forEach(([k, v]) => {
      if (!v) return;
      p.set(k, k === "de" || k === "ate" ? new Date(v).toISOString() : v);
    });
    return p;
  };

  async function carregar(pg = pagina) {
    const p = params();
    p.set("limite", String(POR_PAGINA));
    p.set("deslocamento", String(pg * POR_PAGINA));
    setDados(await api(`/auditoria?${p}`));
  }

  useEffect(() => {
    api<typeof tipos>("/auditoria/tipos").then(setTipos);
    carregar(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function filtrar(ev: FormEvent) {
    ev.preventDefault();
    setPagina(0);
    carregar(0);
  }

  const paginas = Math.max(1, Math.ceil(dados.total / POR_PAGINA));

  return (
    <section>
      <div className="cabecalho"><h2>Trilha de auditoria</h2><span className="contador">{dados.total.toLocaleString("pt-BR")}</span></div>
      <form className="painel linha-form" onSubmit={filtrar}>
        <input placeholder="Login" value={filtro.login} onChange={(e) => setFiltro({ ...filtro, login: e.target.value })} />
        <select value={filtro.papel} onChange={(e) => setFiltro({ ...filtro, papel: e.target.value })}>
          <option value="">Todos os perfis</option>
          {tipos.papeis.map((p) => <option key={p}>{p}</option>)}
        </select>
        <select value={filtro.tipo_acao} onChange={(e) => setFiltro({ ...filtro, tipo_acao: e.target.value })}>
          <option value="">Todas as ações</option>
          {tipos.tipos_acao.map((t) => <option key={t}>{t}</option>)}
        </select>
        <input placeholder="Entidade (ex.: clientes)" value={filtro.entidade} onChange={(e) => setFiltro({ ...filtro, entidade: e.target.value })} />
        <label className="inline">De <input type="datetime-local" value={filtro.de} onChange={(e) => setFiltro({ ...filtro, de: e.target.value })} /></label>
        <label className="inline">Até <input type="datetime-local" value={filtro.ate} onChange={(e) => setFiltro({ ...filtro, ate: e.target.value })} /></label>
        <button className="primario">Filtrar</button>
        <button type="button" className="secundario" onClick={() => baixar(`/auditoria/exportar?${params()}`, "auditoria.csv")}>Exportar CSV</button>
      </form>

      <table>
        <thead><tr><th>Data e hora</th><th>Usuário</th><th>Perfil</th><th>IP</th><th>Ação</th><th>Dado afetado</th><th /></tr></thead>
        <tbody>
          {dados.itens.map((r) => (
            <Fragment key={r.id}>
              <tr className={r.tipo_acao === "ACESSO_NEGADO" || r.tipo_acao.includes("FALHA") || r.tipo_acao.includes("BLOQUEADO") ? "alerta" : ""}>
                <td>{dataHora(r.data_hora)}</td>
                <td>{r.login ?? "—"}</td>
                <td>{r.papel ?? "—"}</td>
                <td><code>{r.ip ?? "—"}</code></td>
                <td>{r.tipo_acao}</td>
                <td>{r.entidade ? `${r.entidade}${r.entidade_id ? ` #${r.entidade_id}` : ""}` : "—"}</td>
                <td>{r.detalhes && <button className="link" onClick={() => setAberto(aberto === r.id ? null : r.id)}>{aberto === r.id ? "Ocultar" : "Detalhes"}</button>}</td>
              </tr>
              {aberto === r.id && (
                <tr className="detalhe"><td colSpan={7}><pre>{JSON.stringify(r.detalhes, null, 2)}</pre></td></tr>
              )}
            </Fragment>
          ))}
          {dados.itens.length === 0 && <tr><td colSpan={7} className="sutil centro">Nenhum registro.</td></tr>}
        </tbody>
      </table>
      <div className="paginacao">
        <button className="secundario" disabled={pagina === 0} onClick={() => { setPagina(pagina - 1); carregar(pagina - 1); }}>Anterior</button>
        <span>Página {pagina + 1} de {paginas}</span>
        <button className="secundario" disabled={pagina + 1 >= paginas} onClick={() => { setPagina(pagina + 1); carregar(pagina + 1); }}>Próxima</button>
      </div>
    </section>
  );
}
