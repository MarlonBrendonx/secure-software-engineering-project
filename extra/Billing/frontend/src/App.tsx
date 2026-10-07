import { ReactNode, useCallback, useEffect, useState } from "react";
import { api, ErroApi, Me, perfil } from "./api";
import Login from "./paginas/Login";
import NovaSenha from "./paginas/NovaSenha";
import Inicio from "./paginas/Inicio";
import Seguranca from "./paginas/Seguranca";
import Usuarios from "./paginas/Usuarios";
import Substituicoes from "./paginas/Substituicoes";
import Auditoria from "./paginas/Auditoria";
import Parametros from "./paginas/Parametros";

interface Pagina {
  caminho: string;
  titulo: string;
  permissao?: string;
  render: (me: Me, recarregar: () => Promise<void>, ir: (c: string) => void) => ReactNode;
}

const PAGINAS: Pagina[] = [
  { caminho: "/", titulo: "Início", render: (me, rec, ir) => <Inicio me={me} recarregar={rec} ir={ir} /> },
  { caminho: "/usuarios", titulo: "Usuários", permissao: "users.manage", render: (me) => <Usuarios me={me} /> },
  { caminho: "/substituicoes", titulo: "Substituições", permissao: "delegations.manage", render: (me) => <Substituicoes me={me} /> },
  { caminho: "/auditoria", titulo: "Auditoria", permissao: "audit.read", render: () => <Auditoria /> },
  { caminho: "/parametros", titulo: "Parâmetros", permissao: "settings.manage", render: () => <Parametros /> },
  { caminho: "/seguranca", titulo: "Segurança da conta", render: (me, rec) => <Seguranca me={me} recarregar={rec} /> },
];

function rotaAtual() {
  return { caminho: window.location.pathname, busca: new URLSearchParams(window.location.search) };
}

export default function App() {
  const [rota, setRota] = useState(rotaAtual);
  const [me, setMe] = useState<Me | null>(null);
  const [carregando, setCarregando] = useState(true);

  const ir = useCallback((caminho: string) => {
    window.history.pushState(null, "", caminho);
    setRota(rotaAtual());
  }, []);

  useEffect(() => {
    const voltar = () => setRota(rotaAtual());
    window.addEventListener("popstate", voltar);
    return () => window.removeEventListener("popstate", voltar);
  }, []);

  const recarregar = useCallback(async () => {
    try {
      setMe(await api<Me>("/me"));
    } catch (e) {
      if (!(e instanceof ErroApi && e.status === 401)) console.error(e);
      setMe(null);
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    // Na tela de verificação do código ainda não existe sessão: não adianta perguntar /me.
    if (rota.caminho.startsWith("/login") || rota.caminho === "/nova-senha") setCarregando(false);
    else recarregar();
  }, [rota.caminho, recarregar]);

  async function sair() {
    try {
      await api("/auth/logout", { method: "POST" });
    } finally {
      setMe(null);
      ir("/login");
    }
  }

  if (rota.caminho === "/nova-senha") return <NovaSenha token={rota.busca.get("token") ?? ""} ir={ir} />;
  if (carregando) return <div className="centro sutil">Carregando…</div>;

  if (!me || rota.caminho.startsWith("/login")) {
    return (
      <Login
        etapaInicial={rota.caminho === "/login/verificacao" ? "codigo" : "entrar"}
        erroInicial={rota.busca.get("erro")}
        aoEntrar={(u) => {
          setMe(u);
          ir("/");
        }}
      />
    );
  }

  const visiveis = PAGINAS.filter((p) => !p.permissao || me.permissions.includes(p.permissao));
  const atual = visiveis.find((p) => p.caminho === rota.caminho) ?? visiveis[0];
  const perfisVisiveis = [
    ...me.roles.filter((r) => r !== "none").map(perfil),
    ...me.roles_pending_mfa.map((r) => `${perfil(r)} (falta 2FA)`),
  ];
  const viaSubstituicao = me.delegations.some((d) => me.roles_pending_mfa.includes(d.role));

  return (
    <div className="layout">
      <header className="topo">
        <div className="marca">Billing</div>
        <nav>
          {visiveis.map((p) => (
            <button key={p.caminho} className={p === atual ? "aba ativa" : "aba"} onClick={() => ir(p.caminho)}>
              {p.titulo}
            </button>
          ))}
        </nav>
        <div className="quem">
          <div>
            <strong>{me.name}</strong>
            <span className="papel">{perfisVisiveis.length ? perfisVisiveis.join(" · ") : "Sem perfil"}</span>
          </div>
          <div className="sutil pequeno">
            {me.email ?? me.login} · {me.mfa ? "verificação em 2 etapas ✓" : "sem verificação em 2 etapas"}
          </div>
        </div>
        <button className="secundario" onClick={sair}>
          Sair
        </button>
      </header>
      <main className="conteudo">
        {me.mfa_enrollment_required && atual.caminho !== "/seguranca" && (
          <div className="faixa">
            <strong>
              {viaSubstituicao
                ? "A substituição que você recebeu exige verificação em duas etapas. Ative o autenticador para usá-la."
                : "Seu perfil exige verificação em duas etapas. Ative o autenticador para liberar todas as suas permissões."}
            </strong>
            <button className="primario" onClick={() => ir("/seguranca")}>
              Ativar agora
            </button>
          </div>
        )}
        {atual.render(me, recarregar, ir)}
      </main>
    </div>
  );
}
