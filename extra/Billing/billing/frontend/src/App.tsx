import { useCallback, useEffect, useState } from "react";
import { api, dataHora, definirAoExpirar, Papel, renovar, Usuario } from "./api";
import Login from "./paginas/Login";
import Cadastros from "./paginas/Cadastros";
import Usuarios from "./paginas/Usuarios";
import Lancamentos from "./paginas/Lancamentos";
import Aprovacoes from "./paginas/Aprovacoes";
import ExportacaoErp from "./paginas/ExportacaoErp";
import Auditoria from "./paginas/Auditoria";

interface Pagina {
  id: string;
  titulo: string;
  componente: (u: Usuario) => JSX.Element;
}

const PAGINAS: Record<Papel, Pagina[]> = {
  ADMINISTRADOR: [
    { id: "cadastros", titulo: "Cadastros", componente: () => <Cadastros /> },
    { id: "usuarios", titulo: "Usuários", componente: (u) => <Usuarios eu={u} /> },
  ],
  OPERACIONAL: [
    { id: "lancamentos", titulo: "Lançamentos", componente: () => <Lancamentos podeEditar /> },
    { id: "erp", titulo: "Planilha ERP", componente: () => <ExportacaoErp /> },
  ],
  GESTOR: [
    { id: "aprovacoes", titulo: "Aprovações", componente: () => <Aprovacoes /> },
    { id: "lancamentos", titulo: "Lançamentos", componente: () => <Lancamentos podeEditar={false} /> },
  ],
  AUDITOR: [{ id: "auditoria", titulo: "Auditoria", componente: () => <Auditoria /> }],
  OPERACAO: [],
};

const RENOVAR_A_CADA_MS = 10 * 60 * 1000; // antes dos 15 min do token de acesso

export default function App() {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [expira, setExpira] = useState<string>("");
  const [carregando, setCarregando] = useState(true);
  const [pagina, setPagina] = useState<string>("");

  const sair = useCallback(async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } finally {
      setUsuario(null);
      setPagina("");
    }
  }, []);

  const carregarSessao = useCallback(async () => {
    try {
      let s = await api<{ usuario: Usuario; sessao_expira_em: string }>("/auth/sessao").catch(async (e) => {
        if (await renovar()) return api<{ usuario: Usuario; sessao_expira_em: string }>("/auth/sessao");
        throw e;
      });
      setUsuario(s.usuario);
      setExpira(s.sessao_expira_em);
    } catch {
      setUsuario(null);
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    definirAoExpirar(() => setUsuario(null));
    carregarSessao();
  }, [carregarSessao]);

  useEffect(() => {
    if (!usuario) return;
    const t = setInterval(async () => {
      if (!(await renovar())) setUsuario(null);
    }, RENOVAR_A_CADA_MS);
    return () => clearInterval(t);
  }, [usuario]);

  if (carregando) return <div className="centro sutil">Carregando…</div>;
  if (!usuario) return <Login aoEntrar={() => { setCarregando(true); carregarSessao(); }} />;

  const paginas = PAGINAS[usuario.papel];
  const atual = paginas.find((p) => p.id === pagina) ?? paginas[0];

  return (
    <div className="layout">
      <header className="topo">
        <div className="marca">Billing</div>
        <nav>
          {paginas.map((p) => (
            <button key={p.id} className={p === atual ? "aba ativa" : "aba"} onClick={() => setPagina(p.id)}>
              {p.titulo}
            </button>
          ))}
        </nav>
        <div className="quem">
          <div>
            <strong>{usuario.nome}</strong>
            <span className="papel">{usuario.papel}</span>
          </div>
          {expira && <div className="sutil pequeno">Sessão até {dataHora(expira)}</div>}
        </div>
        <button className="secundario" onClick={sair}>Sair</button>
      </header>
      <main className="conteudo">
        {atual ? (
          atual.componente(usuario)
        ) : (
          <div className="vazio">
            <h2>Perfil de Operação</h2>
            <p>
              Este perfil não tem telas de billing. A saúde do provedor de identidade é consultada pelo endpoint
              <code> GET /api/saude/provedor-identidade</code> com o cabeçalho <code>X-Ops-Token</code>.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
