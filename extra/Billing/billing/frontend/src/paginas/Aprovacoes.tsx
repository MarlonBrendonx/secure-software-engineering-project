import { useEffect, useState } from "react";
import { api, ErroApi, moeda } from "../api";
import type { Lancamento } from "./Lancamentos";

export default function Aprovacoes() {
  const [pendentes, setPendentes] = useState<Lancamento[]>([]);
  const [motivos, setMotivos] = useState<Record<number, string>>({});
  const [erro, setErro] = useState("");

  const carregar = () => api<Lancamento[]>("/aprovacoes/pendentes").then(setPendentes);
  useEffect(() => {
    carregar();
  }, []);

  async function decidir(l: Lancamento, acao: "aprovar" | "reprovar") {
    setErro("");
    try {
      await api(`/lancamentos/${l.id}/${acao}`, { method: "POST", json: { observacao: motivos[l.id] || null } });
      carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Erro inesperado.");
    }
  }

  return (
    <section>
      <div className="cabecalho"><h2>Aprovações pendentes</h2><span className="contador">{pendentes.length}</span></div>
      {erro && <div className="erro">{erro}</div>}
      <table>
        <thead>
          <tr><th>Período</th><th>Cliente</th><th>Regra</th><th className="num">Qtd.</th><th className="num">Total</th><th>Lançado por</th><th>Observação / motivo</th><th /></tr>
        </thead>
        <tbody>
          {pendentes.map((l) => (
            <tr key={l.id}>
              <td>{l.periodo}</td>
              <td>{l.cliente_nome}</td>
              <td>{l.regra_nome}<div className="sutil pequeno">{moeda(l.valor_unitario)} por unidade</div></td>
              <td className="num">{Number(l.quantidade).toLocaleString("pt-BR")}</td>
              <td className="num"><strong>{moeda(l.valor_total)}</strong></td>
              <td>{l.criado_por_nome}{l.observacao && <div className="sutil pequeno">{l.observacao}</div>}</td>
              <td><input placeholder="Obrigatório para reprovar" value={motivos[l.id] ?? ""} onChange={(e) => setMotivos({ ...motivos, [l.id]: e.target.value })} /></td>
              <td className="acoes-linha">
                <button className="primario pequeno" onClick={() => decidir(l, "aprovar")}>Aprovar</button>
                <button className="secundario pequeno" onClick={() => decidir(l, "reprovar")}>Reprovar</button>
              </td>
            </tr>
          ))}
          {pendentes.length === 0 && <tr><td colSpan={8} className="sutil centro">Nada aguardando aprovação.</td></tr>}
        </tbody>
      </table>
    </section>
  );
}
