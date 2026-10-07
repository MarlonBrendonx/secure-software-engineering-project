import { FormEvent, useEffect, useState } from "react";
import { api, ERROS_LOGIN, ErroApi, LoginOut, Me } from "../api";

type Etapa = "entrar" | "codigo" | "esqueci";

interface Provedor {
  id: string;
  name: string;
  login_url: string;
}

const INICIAL: Record<string, string> = { google: "G", microsoft: "M" };

export default function Login({
  etapaInicial,
  erroInicial,
  aoEntrar,
}: {
  etapaInicial: Etapa;
  erroInicial: string | null;
  aoEntrar: (u: Me) => void;
}) {
  const [etapa, setEtapa] = useState<Etapa>(etapaInicial);
  const [provedores, setProvedores] = useState<Provedor[] | null>(null);
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [codigo, setCodigo] = useState("");
  const [recuperacao, setRecuperacao] = useState(false);
  const [erro, setErro] = useState(erroInicial ? ERROS_LOGIN[erroInicial] ?? "Não foi possível entrar." : "");
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [mostrarLocal, setMostrarLocal] = useState(false);

  useEffect(() => {
    api<Provedor[]>("/auth/providers")
      .then(setProvedores)
      .catch(() => setProvedores([]));
  }, []);

  async function executar(fn: () => Promise<void>) {
    setErro("");
    setAviso("");
    setOcupado(true);
    try {
      await fn();
    } catch (e) {
      if (e instanceof ErroApi) {
        if (e.codigo === "invalid_code" && typeof e.extra.attempts_left === "number") {
          setErro(`Código inválido. Restam ${e.extra.attempts_left} tentativa(s).`);
        } else if (e.codigo === "mfa_challenge_expired") {
          setEtapa("entrar");
          setErro(e.message);
        } else {
          setErro(e.message);
        }
      } else {
        setErro("Não foi possível conectar ao servidor.");
      }
    } finally {
      setOcupado(false);
    }
  }

  const entrarLocal = (ev: FormEvent) => {
    ev.preventDefault();
    executar(async () => {
      const r = await api<LoginOut>("/auth/local/login", { json: { login, password: senha } });
      setSenha("");
      if (r.status === "mfa_required") {
        setCodigo("");
        setEtapa("codigo");
      } else if (r.me) {
        aoEntrar(r.me);
      }
    });
  };

  const verificar = (ev: FormEvent) => {
    ev.preventDefault();
    executar(async () => {
      const r = await api<LoginOut>("/auth/mfa/verify", { json: { code: codigo } });
      if (r.me) aoEntrar(r.me);
    });
  };

  const pedirNovaSenha = (ev: FormEvent) => {
    ev.preventDefault();
    executar(async () => {
      const r = await api<{ message: string }>("/auth/password/reset-request", { json: { login } });
      setAviso(r.message);
    });
  };

  const codigoValido = recuperacao ? codigo.replace(/[^A-Za-z0-9]/g, "").length === 10 : codigo.length === 6;

  return (
    <div className="login-fundo">
      <div className="login-cartao">
        <div className="marca">Billing</div>

        {etapa === "entrar" && (
          <div className="provedores">
            <h1>Entrar</h1>
            <p className="sutil">Use a conta da empresa no Google ou na Microsoft.</p>
            {provedores === null && <p className="sutil">Carregando…</p>}
            {provedores?.map((p) => (
              <a key={p.id} className="provedor" href={p.login_url}>
                <span className="icone">{INICIAL[p.id] ?? p.name.charAt(0)}</span>
                Entrar com {p.name}
              </a>
            ))}
            {provedores?.length === 0 && <p className="sutil">Nenhum provedor de login configurado.</p>}
            {erro && <div className="erro">{erro}</div>}

            <div className="divisor">ou</div>
            {!mostrarLocal ? (
              <button type="button" className="link" onClick={() => setMostrarLocal(true)}>
                Entrar com usuário e senha (contas externas)
              </button>
            ) : (
              <form onSubmit={entrarLocal}>
                <label>
                  Usuário
                  <input value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="username" autoFocus required />
                </label>
                <label>
                  Senha
                  <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} autoComplete="current-password" required />
                </label>
                <button className="primario largo" disabled={ocupado}>
                  Continuar
                </button>
                <button type="button" className="link" onClick={() => { setEtapa("esqueci"); setErro(""); }}>
                  Esqueci minha senha
                </button>
              </form>
            )}
          </div>
        )}

        {etapa === "codigo" && (
          <form onSubmit={verificar}>
            <h1>Verificação em duas etapas</h1>
            <p className="sutil">
              {recuperacao
                ? "Digite um dos códigos de recuperação que você guardou ao ativar o autenticador. Cada código vale uma vez."
                : "Abra o aplicativo autenticador no celular e digite o código de 6 dígitos do Billing."}
            </p>
            <label>
              {recuperacao ? "Código de recuperação" : "Código do aplicativo"}
              <input
                value={codigo}
                onChange={(e) =>
                  setCodigo(recuperacao ? e.target.value.toUpperCase().slice(0, 11) : e.target.value.replace(/\D/g, "").slice(0, 6))
                }
                inputMode={recuperacao ? "text" : "numeric"}
                autoComplete="one-time-code"
                placeholder={recuperacao ? "XXXXX-XXXXX" : "000000"}
                autoFocus
                required
              />
            </label>
            {erro && <div className="erro">{erro}</div>}
            <button className="primario largo" disabled={ocupado || !codigoValido}>
              Entrar
            </button>
            <button type="button" className="link" onClick={() => { setRecuperacao(!recuperacao); setCodigo(""); setErro(""); }}>
              {recuperacao ? "Usar o código do aplicativo" : "Perdi o celular: usar código de recuperação"}
            </button>
            <button type="button" className="link" onClick={() => { setEtapa("entrar"); setCodigo(""); setErro(""); window.history.replaceState(null, "", "/login"); }}>
              Voltar
            </button>
          </form>
        )}

        {etapa === "esqueci" && (
          <form onSubmit={pedirNovaSenha}>
            <h1>Criar nova senha</h1>
            <p className="sutil">Vale só para contas com usuário e senha. Quem entra pelo Google ou Microsoft troca a senha no próprio provedor.</p>
            <label>
              Usuário
              <input value={login} onChange={(e) => setLogin(e.target.value)} autoFocus required />
            </label>
            {erro && <div className="erro">{erro}</div>}
            {aviso && <div className="aviso">{aviso}</div>}
            <button className="primario largo" disabled={ocupado}>
              Enviar link por e-mail
            </button>
            <button type="button" className="link" onClick={() => { setEtapa("entrar"); setAviso(""); setErro(""); }}>
              Voltar
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
