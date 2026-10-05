import { FormEvent, useEffect, useState } from "react";
import QRCode from "qrcode";
import { api, ErroApi, Usuario } from "../api";

type Etapa = "credenciais" | "mfa_cadastro" | "mfa_verificacao";

export default function Login({ aoEntrar }: { aoEntrar: (u: Usuario) => void }) {
  const [etapa, setEtapa] = useState<Etapa>("credenciais");
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [codigo, setCodigo] = useState("");
  const [segredo, setSegredo] = useState<{ segredo: string; uri: string } | null>(null);
  const [qr, setQr] = useState("");
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    if (segredo) QRCode.toDataURL(segredo.uri, { margin: 1, width: 200 }).then(setQr);
  }, [segredo]);

  async function executar(fn: () => Promise<void>) {
    setErro("");
    setOcupado(true);
    try {
      await fn();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível conectar ao servidor.");
      if (e instanceof ErroApi && e.status === 401 && etapa !== "credenciais" && /expirada/.test(e.message)) {
        setEtapa("credenciais");
      }
    } finally {
      setOcupado(false);
    }
  }

  const enviarCredenciais = (ev: FormEvent) => {
    ev.preventDefault();
    executar(async () => {
      const r = await api<{ etapa: Etapa }>("/auth/login", { method: "POST", json: { login, senha } });
      setSenha("");
      if (r.etapa === "mfa_cadastro") setSegredo(await api("/auth/mfa/cadastro", { method: "POST" }));
      setEtapa(r.etapa);
    });
  };

  const enviarCodigo = (ev: FormEvent) => {
    ev.preventDefault();
    executar(async () => {
      const u = await api<Usuario>("/auth/mfa/verificar", { method: "POST", json: { codigo } });
      aoEntrar(u);
    });
  };

  return (
    <div className="login-fundo">
      <div className="login-cartao">
        <div className="marca">Billing</div>
        {etapa === "credenciais" ? (
          <form onSubmit={enviarCredenciais}>
            <h1>Entrar</h1>
            <p className="sutil">Use seu usuário e senha corporativos.</p>
            <label>
              Usuário
              <input value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="username" autoFocus required />
            </label>
            <label>
              Senha
              <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} autoComplete="current-password" required />
            </label>
            {erro && <div className="erro">{erro}</div>}
            <button className="primario largo" disabled={ocupado}>Continuar</button>
          </form>
        ) : (
          <form onSubmit={enviarCodigo}>
            <h1>Verificação em duas etapas</h1>
            {etapa === "mfa_cadastro" && segredo && (
              <div className="mfa-cadastro">
                <p className="sutil">
                  Primeiro acesso: escaneie o código com um aplicativo autenticador (Google Authenticator, Microsoft
                  Authenticator ou similar).
                </p>
                {qr && <img src={qr} alt="QR code do segundo fator" width={200} height={200} />}
                <details>
                  <summary>Não consegue escanear?</summary>
                  <code className="segredo">{segredo.segredo}</code>
                </details>
              </div>
            )}
            <label>
              Código de 6 dígitos do aplicativo
              <input
                value={codigo}
                onChange={(e) => setCodigo(e.target.value.replace(/\D/g, "").slice(0, 6))}
                inputMode="numeric"
                autoComplete="one-time-code"
                autoFocus
                required
                pattern="\d{6}"
              />
            </label>
            {erro && <div className="erro">{erro}</div>}
            <button className="primario largo" disabled={ocupado || codigo.length !== 6}>Entrar</button>
            <button type="button" className="link" onClick={() => { setEtapa("credenciais"); setCodigo(""); setErro(""); }}>
              Voltar
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
