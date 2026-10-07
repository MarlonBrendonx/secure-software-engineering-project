import { useEffect, useState } from "react";
import { api, dataHora, ErroApi } from "../api";

interface Parametro {
  key: string;
  value: unknown;
  description: string;
  updated_at: string;
}

function Linha({ p, aoSalvar }: { p: Parametro; aoSalvar: (texto: string) => void }) {
  const tipo = typeof p.value === "boolean" ? "bool" : typeof p.value === "number" ? "int" : "texto";
  const [valor, setValor] = useState(String(p.value));
  const [erro, setErro] = useState("");
  const mudou = valor !== String(p.value);

  async function salvar() {
    setErro("");
    const v = tipo === "bool" ? valor === "true" : tipo === "int" ? Number(valor) : valor.replace(",", ".");
    try {
      await api(`/settings/${p.key}`, { method: "PUT", json: { value: v } });
      aoSalvar(`Parâmetro “${p.description}” atualizado.`);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível salvar.");
    }
  }

  return (
    <tr>
      <td>
        <strong>{p.description}</strong>
        <div className="sutil pequeno"><code>{p.key}</code> · alterado em {dataHora(p.updated_at)}</div>
        {erro && <div className="erro">{erro}</div>}
      </td>
      <td style={{ width: 220 }}>
        {tipo === "bool" ? (
          <select value={valor} onChange={(e) => setValor(e.target.value)}>
            <option value="true">Sim</option>
            <option value="false">Não</option>
          </select>
        ) : (
          <input value={valor} onChange={(e) => setValor(e.target.value)} inputMode="decimal" style={{ width: "100%" }} />
        )}
      </td>
      <td className="acoes-linha" style={{ width: 100 }}>
        <button className="primario pequeno" disabled={!mudou} onClick={salvar}>Salvar</button>
      </td>
    </tr>
  );
}

export default function Parametros() {
  const [lista, setLista] = useState<Parametro[]>([]);
  const [aviso, setAviso] = useState("");

  const carregar = () => api<Parametro[]>("/settings").then(setLista);
  useEffect(() => {
    carregar();
  }, []);

  return (
    <>
      <div className="cabecalho">
        <h2>Parâmetros do sistema</h2>
      </div>
      <p className="sutil" style={{ marginTop: -8, marginBottom: 16 }}>Toda alteração fica registrada na trilha de auditoria com o valor anterior e o novo.</p>
      {aviso && <div className="aviso">{aviso}</div>}
      <table>
        <thead><tr><th>Parâmetro</th><th>Valor</th><th></th></tr></thead>
        <tbody>
          {lista.map((p) => (
            <Linha key={`${p.key}-${p.updated_at}`} p={p} aoSalvar={(t) => { setAviso(t); carregar(); }} />
          ))}
        </tbody>
      </table>
    </>
  );
}
