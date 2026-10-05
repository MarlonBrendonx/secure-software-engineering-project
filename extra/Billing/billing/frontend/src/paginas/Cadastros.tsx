import { FormEvent, useEffect, useState } from "react";
import { api, ErroApi } from "../api";

interface TipoCadastro {
  slug: string;
  rotulo: string;
  campos: string[];
  obrigatorios: string[];
  esquema: Record<string, { type?: string; anyOf?: { type?: string; format?: string }[]; format?: string; title?: string }>;
}

type Registro = Record<string, unknown> & { id: number; nome: string; ativo: boolean };

// chave estrangeira → cadastro de onde vêm as opções
const REFERENCIAS: Record<string, string> = {
  empresa_id: "empresas", grupo_economico_id: "grupos-economicos", segmento_id: "segmentos",
  cliente_id: "clientes", programa_id: "programas", centro_custo_id: "centros-custo",
  unidade_negocio_id: "unidades-negocio", fornecedor_id: "fornecedores", contrato_id: "contratos",
};

const ROTULOS: Record<string, string> = {
  nome: "Nome", cnpj: "CNPJ", codigo: "Código", numero: "Número", valor_unitario: "Valor unitário",
  unidade_medida: "Unidade de medida", vigencia_inicio: "Início da vigência", vigencia_fim: "Fim da vigência",
  empresa_id: "Empresa", grupo_economico_id: "Grupo econômico", segmento_id: "Segmento", cliente_id: "Cliente",
  programa_id: "Programa", centro_custo_id: "Centro de custo", unidade_negocio_id: "Unidade de negócio",
  fornecedor_id: "Fornecedor", contrato_id: "Contrato",
};

function formato(def: TipoCadastro["esquema"][string]): string {
  return def.format ?? def.anyOf?.find((a) => a.format)?.format ?? def.type ?? def.anyOf?.[0]?.type ?? "string";
}

export default function Cadastros() {
  const [tipos, setTipos] = useState<TipoCadastro[]>([]);
  const [slug, setSlug] = useState("empresas");
  const [itens, setItens] = useState<Registro[]>([]);
  const [opcoes, setOpcoes] = useState<Record<string, Registro[]>>({});
  const [editando, setEditando] = useState<Registro | "novo" | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [busca, setBusca] = useState("");
  const [erro, setErro] = useState("");

  const tipo = tipos.find((t) => t.slug === slug);

  useEffect(() => {
    api<TipoCadastro[]>("/cadastros").then(setTipos);
  }, []);

  async function carregar() {
    const q = new URLSearchParams({ limite: "500", ...(busca ? { busca } : {}) });
    const r = await api<{ itens: Registro[] }>(`/cadastros/${slug}?${q}`);
    setItens(r.itens);
  }

  useEffect(() => {
    carregar();
    setEditando(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  useEffect(() => {
    if (!tipo) return;
    const refs = tipo.campos.filter((c) => REFERENCIAS[c]);
    Promise.all(refs.map((c) => api<{ itens: Registro[] }>(`/cadastros/${REFERENCIAS[c]}?limite=500`)))
      .then((rs) => setOpcoes(Object.fromEntries(refs.map((c, i) => [c, rs[i].itens]))));
  }, [tipo]);

  function abrir(r: Registro | "novo") {
    setErro("");
    setEditando(r);
    setForm(Object.fromEntries((tipo?.campos ?? []).map((c) => [c, r === "novo" ? "" : String(r[c] ?? "")])));
  }

  async function salvar(ev: FormEvent) {
    ev.preventDefault();
    if (!tipo) return;
    const corpo: Record<string, unknown> = {};
    for (const c of tipo.campos) {
      const v = form[c];
      if (v === "" || v === undefined) {
        // Campo opcional que aceita nulo: envia null (permite limpar). Senão, omite e vale o padrão do servidor.
        const aceitaNulo = tipo.esquema[c]?.anyOf?.some((a) => a.type === "null");
        if (!tipo.obrigatorios.includes(c) && aceitaNulo) corpo[c] = null;
        continue;
      }
      corpo[c] = REFERENCIAS[c] ? Number(v) : v;
    }
    try {
      if (editando === "novo") await api(`/cadastros/${slug}`, { method: "POST", json: corpo });
      else if (editando) await api(`/cadastros/${slug}/${editando.id}`, { method: "PUT", json: corpo });
      setEditando(null);
      carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Erro ao salvar.");
    }
  }

  async function remover(r: Registro) {
    if (!confirm(`Remover "${r.nome}"? O registro deixa de aparecer, mas continua no histórico.`)) return;
    await api(`/cadastros/${slug}/${r.id}`, { method: "DELETE" });
    carregar();
  }

  const colunas = (tipo?.campos ?? []).slice(0, 5);
  const exibir = (c: string, v: unknown): string => {
    if (REFERENCIAS[c]) return opcoes[c]?.find((o) => o.id === v)?.nome ?? (v == null ? "—" : String(v));
    return v === null || v === undefined || v === "" ? "—" : String(v);
  };

  return (
    <div className="com-lateral">
      <aside className="lateral">
        {tipos.map((t) => (
          <button key={t.slug} className={t.slug === slug ? "item ativo" : "item"} onClick={() => setSlug(t.slug)}>
            {t.rotulo}
          </button>
        ))}
      </aside>
      <section>
        <div className="cabecalho">
          <h2>{tipo?.rotulo}</h2>
          <form className="busca" onSubmit={(e) => { e.preventDefault(); carregar(); }}>
            <input placeholder="Buscar por nome" value={busca} onChange={(e) => setBusca(e.target.value)} />
          </form>
          <button className="primario" onClick={() => abrir("novo")}>Novo</button>
        </div>

        {editando && tipo && (
          <form className="painel grade-form" onSubmit={salvar}>
            <h3>{editando === "novo" ? "Novo registro" : `Editar: ${editando.nome}`}</h3>
            {tipo.campos.map((c) => {
              const f = formato(tipo.esquema[c]);
              const obrig = tipo.obrigatorios.includes(c);
              return (
                <label key={c}>
                  <span>{ROTULOS[c] ?? c} {obrig && <span className="obrig">*</span>}</span>
                  {REFERENCIAS[c] ? (
                    <select value={form[c]} required={obrig} onChange={(e) => setForm({ ...form, [c]: e.target.value })}>
                      <option value="">—</option>
                      {(opcoes[c] ?? []).map((o) => <option key={o.id} value={o.id}>{o.nome}</option>)}
                    </select>
                  ) : (
                    <input
                      type={f === "date" ? "date" : "text"}
                      inputMode={c === "valor_unitario" ? "decimal" : undefined}
                      value={form[c]}
                      required={obrig}
                      onChange={(e) => setForm({ ...form, [c]: e.target.value })}
                    />
                  )}
                </label>
              );
            })}
            {erro && <div className="erro largura-total">{erro}</div>}
            <div className="acoes largura-total">
              <button type="button" className="secundario" onClick={() => setEditando(null)}>Cancelar</button>
              <button className="primario">Salvar</button>
            </div>
          </form>
        )}

        <table>
          <thead>
            <tr>
              {colunas.map((c) => <th key={c}>{ROTULOS[c] ?? c}</th>)}
              <th />
            </tr>
          </thead>
          <tbody>
            {itens.map((r) => (
              <tr key={r.id}>
                {colunas.map((c) => <td key={c}>{exibir(c, r[c])}</td>)}
                <td className="acoes-linha">
                  <button className="link" onClick={() => abrir(r)}>Editar</button>
                  <button className="link perigo" onClick={() => remover(r)}>Remover</button>
                </td>
              </tr>
            ))}
            {itens.length === 0 && (
              <tr><td colSpan={colunas.length + 1} className="sutil centro">Nenhum registro.</td></tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
