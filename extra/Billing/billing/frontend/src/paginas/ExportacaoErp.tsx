import { useEffect, useState } from "react";
import { api, baixar, dataHora, ErroApi, moeda, periodoAtual } from "../api";

interface Exportacao {
  id: number;
  periodo: string;
  gerada_em: string;
  quantidade_lancamentos: number;
  valor_total: string;
}

export default function ExportacaoErp() {
  const [periodo, setPeriodo] = useState(periodoAtual());
  const [lista, setLista] = useState<Exportacao[]>([]);
  const [erro, setErro] = useState("");

  const carregar = () => api<Exportacao[]>("/exportacoes-erp").then(setLista);
  useEffect(() => {
    carregar();
  }, []);

  async function gerar() {
    setErro("");
    try {
      const e = await api<Exportacao>("/exportacoes-erp", { method: "POST", json: { periodo } });
      await carregar();
      await baixar(`/exportacoes-erp/${e.id}/arquivo`, `erp_${periodo}.csv`);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Erro inesperado.");
    }
  }

  return (
    <section>
      <div className="cabecalho"><h2>Planilha para o ERP</h2></div>
      <div className="painel linha-form">
        <label className="inline">Período <input type="month" value={periodo} onChange={(e) => setPeriodo(e.target.value)} /></label>
        <button className="primario" onClick={gerar}>Gerar e baixar</button>
        <span className="sutil">Inclui somente lançamentos aprovados do período.</span>
      </div>
      {erro && <div className="erro">{erro}</div>}
      <table>
        <thead><tr><th>Período</th><th>Gerada em</th><th className="num">Lançamentos</th><th className="num">Total</th><th /></tr></thead>
        <tbody>
          {lista.map((e) => (
            <tr key={e.id}>
              <td>{e.periodo}</td>
              <td>{dataHora(e.gerada_em)}</td>
              <td className="num">{e.quantidade_lancamentos}</td>
              <td className="num">{moeda(e.valor_total)}</td>
              <td className="acoes-linha"><button className="link" onClick={() => baixar(`/exportacoes-erp/${e.id}/arquivo`, `erp_${e.periodo}.csv`)}>Baixar</button></td>
            </tr>
          ))}
          {lista.length === 0 && <tr><td colSpan={5} className="sutil centro">Nenhuma planilha gerada.</td></tr>}
        </tbody>
      </table>
    </section>
  );
}
