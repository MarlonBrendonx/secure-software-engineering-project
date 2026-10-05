import { FormEvent, useEffect, useMemo, useState } from "react";
import { api, ErroApi, moeda, periodoAtual } from "../api";

export interface Lancamento {
  id: number;
  cliente_id: number;
  cliente_nome: string;
  periodo: string;
  regra_servico_id: number;
  regra_nome: string;
  quantidade: string;
  valor_unitario: string;
  valor_total: string;
  observacao: string | null;
  status: "RASCUNHO" | "SUBMETIDO" | "APROVADO" | "REPROVADO";
  criado_por_nome: string;
}

interface Opcao { id: number; nome: string; cliente_id?: number; contrato_id?: number; valor_unitario?: string }

const ROTULO_STATUS = { RASCUNHO: "Rascunho", SUBMETIDO: "Aguardando aprovação", APROVADO: "Aprovado", REPROVADO: "Reprovado" };

export function Status({ s }: { s: Lancamento["status"] }) {
  return <span className={`status ${s.toLowerCase()}`}>{ROTULO_STATUS[s]}</span>;
}

export default function Lancamentos({ podeEditar }: { podeEditar: boolean }) {
  const [periodo, setPeriodo] = useState(periodoAtual());
  const [situacao, setSituacao] = useState("");
  const [lista, setLista] = useState<Lancamento[]>([]);
  const [clientes, setClientes] = useState<Opcao[]>([]);
  const [contratos, setContratos] = useState<Opcao[]>([]);
  const [regras, setRegras] = useState<Opcao[]>([]);
  const [form, setForm] = useState<{ id?: number; cliente_id: string; regra_servico_id: string; quantidade: string; observacao: string } | null>(null);
  const [historico, setHistorico] = useState<{ id: number; dados: { decisao: string; observacao: string | null; data_hora: string }[] } | null>(null);
  const [erro, setErro] = useState("");

  async function carregar() {
    const q = new URLSearchParams({ periodo, limite: "500", ...(situacao ? { status: situacao } : {}) });
    setLista((await api<{ itens: Lancamento[] }>(`/lancamentos?${q}`)).itens);
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [periodo, situacao]);

  useEffect(() => {
    if (!podeEditar) return;
    Promise.all(["clientes", "contratos", "regras-servico"].map((s) => api<{ itens: Opcao[] }>(`/cadastros/${s}?limite=500`)))
      .then(([c, ct, r]) => { setClientes(c.itens); setContratos(ct.itens); setRegras(r.itens); });
  }, [podeEditar]);

  // Só mostra as regras dos contratos do cliente escolhido
  const regrasDoCliente = useMemo(() => {
    if (!form?.cliente_id) return [];
    const ids = new Set(contratos.filter((c) => c.cliente_id === Number(form.cliente_id)).map((c) => c.id));
    return regras.filter((r) => ids.has(r.contrato_id!));
  }, [form?.cliente_id, contratos, regras]);

  const regraSel = regras.find((r) => r.id === Number(form?.regra_servico_id));
  const previa = regraSel && form?.quantidade ? Number(form.quantidade.replace(",", ".")) * Number(regraSel.valor_unitario) : null;

  async function executar(fn: () => Promise<unknown>) {
    setErro("");
    try {
      await fn();
      await carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Erro inesperado.");
    }
  }

  function salvar(ev: FormEvent) {
    ev.preventDefault();
    if (!form) return;
    const corpo = {
      cliente_id: Number(form.cliente_id), periodo, regra_servico_id: Number(form.regra_servico_id),
      quantidade: form.quantidade.replace(",", "."), observacao: form.observacao || null,
    };
    executar(async () => {
      if (form.id) await api(`/lancamentos/${form.id}`, { method: "PUT", json: corpo });
      else await api("/lancamentos", { method: "POST", json: corpo });
      setForm(null);
    });
  }

  async function verHistorico(l: Lancamento) {
    const r = await api<{ historico: { decisao: string; observacao: string | null; data_hora: string }[] }>(`/lancamentos/${l.id}`);
    setHistorico({ id: l.id, dados: r.historico });
  }

  const total = lista.reduce((s, l) => s + Number(l.valor_total), 0);

  return (
    <section>
      <div className="cabecalho">
        <h2>Lançamentos</h2>
        <label className="inline">Período <input type="month" value={periodo} onChange={(e) => setPeriodo(e.target.value)} /></label>
        <select value={situacao} onChange={(e) => setSituacao(e.target.value)}>
          <option value="">Todas as situações</option>
          {Object.entries(ROTULO_STATUS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        {podeEditar && (
          <button className="primario" onClick={() => setForm({ cliente_id: "", regra_servico_id: "", quantidade: "", observacao: "" })}>
            Novo lançamento
          </button>
        )}
      </div>

      {form && (
        <form className="painel grade-form" onSubmit={salvar}>
          <h3>{form.id ? "Editar lançamento" : `Novo lançamento — ${periodo}`}</h3>
          <label>Cliente
            <select value={form.cliente_id} required onChange={(e) => setForm({ ...form, cliente_id: e.target.value, regra_servico_id: "" })}>
              <option value="">—</option>
              {clientes.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
          </label>
          <label>Regra de serviço
            <select value={form.regra_servico_id} required onChange={(e) => setForm({ ...form, regra_servico_id: e.target.value })}>
              <option value="">{form.cliente_id ? (regrasDoCliente.length ? "—" : "Cliente sem regras") : "Escolha o cliente"}</option>
              {regrasDoCliente.map((r) => <option key={r.id} value={r.id}>{r.nome} ({moeda(r.valor_unitario!)})</option>)}
            </select>
          </label>
          <label>Quantidade
            <input inputMode="decimal" value={form.quantidade} required onChange={(e) => setForm({ ...form, quantidade: e.target.value })} />
          </label>
          <label>Observação
            <input value={form.observacao} onChange={(e) => setForm({ ...form, observacao: e.target.value })} />
          </label>
          <div className="largura-total sutil">
            {previa !== null && !Number.isNaN(previa) && <>Valor estimado: <strong>{moeda(previa)}</strong> (o valor final é calculado pelo servidor)</>}
          </div>
          {erro && <div className="erro largura-total">{erro}</div>}
          <div className="acoes largura-total">
            <button type="button" className="secundario" onClick={() => setForm(null)}>Cancelar</button>
            <button className="primario">Salvar como rascunho</button>
          </div>
        </form>
      )}
      {!form && erro && <div className="erro">{erro}</div>}

      <table>
        <thead>
          <tr><th>Cliente</th><th>Regra</th><th className="num">Qtd.</th><th className="num">Unitário</th><th className="num">Total</th><th>Situação</th><th>Lançado por</th><th /></tr>
        </thead>
        <tbody>
          {lista.map((l) => {
            const editavel = podeEditar && (l.status === "RASCUNHO" || l.status === "REPROVADO");
            return (
              <tr key={l.id}>
                <td>{l.cliente_nome}</td>
                <td>{l.regra_nome}</td>
                <td className="num">{Number(l.quantidade).toLocaleString("pt-BR")}</td>
                <td className="num">{moeda(l.valor_unitario)}</td>
                <td className="num">{moeda(l.valor_total)}</td>
                <td><Status s={l.status} /></td>
                <td>{l.criado_por_nome}</td>
                <td className="acoes-linha">
                  {editavel && (
                    <>
                      <button className="link" onClick={() => setForm({ id: l.id, cliente_id: String(l.cliente_id), regra_servico_id: String(l.regra_servico_id), quantidade: String(Number(l.quantidade)), observacao: l.observacao ?? "" })}>Editar</button>
                      <button className="link" onClick={() => executar(() => api(`/lancamentos/${l.id}/submeter`, { method: "POST" }))}>Submeter</button>
                      <button className="link perigo" onClick={() => confirm("Remover este lançamento?") && executar(() => api(`/lancamentos/${l.id}`, { method: "DELETE" }))}>Remover</button>
                    </>
                  )}
                  <button className="link" onClick={() => verHistorico(l)}>Histórico</button>
                </td>
              </tr>
            );
          })}
          {lista.length === 0 && <tr><td colSpan={8} className="sutil centro">Nenhum lançamento neste período.</td></tr>}
        </tbody>
        {lista.length > 0 && (
          <tfoot><tr><td colSpan={4}>Total do período</td><td className="num">{moeda(total)}</td><td colSpan={3} /></tr></tfoot>
        )}
      </table>

      {historico && (
        <div className="painel">
          <h3>Histórico de validação — lançamento #{historico.id}</h3>
          {historico.dados.length === 0 ? <p className="sutil">Ainda não foi validado.</p> : (
            <ul>{historico.dados.map((h, i) => <li key={i}><strong>{h.decisao}</strong> em {new Date(h.data_hora).toLocaleString("pt-BR")}{h.observacao && ` — ${h.observacao}`}</li>)}</ul>
          )}
          <button className="secundario" onClick={() => setHistorico(null)}>Fechar</button>
        </div>
      )}
    </section>
  );
}
