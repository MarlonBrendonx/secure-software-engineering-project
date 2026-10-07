import { FormEvent, useEffect, useState } from "react";
import { api, ErroApi, LoginOut, Me } from "../api";

interface Status {
  enrolled: boolean;
  required: boolean;
  session_verified: boolean;
  recovery_codes_left: number;
}

interface Setup {
  secret: string;
  otpauth_uri: string;
  qr_svg: string;
}

function Codigos({ codigos, aoConcluir }: { codigos: string[]; aoConcluir: () => void }) {
  const [guardei, setGuardei] = useState(false);
  const texto = `Billing - códigos de recuperação\nCada código vale uma vez.\n\n${codigos.join("\n")}\n`;
  return (
    <div className="painel">
      <h3>Guarde seus códigos de recuperação</h3>
      <p className="sutil">
        Se você perder o celular, cada código abaixo permite entrar uma vez no lugar do código do aplicativo. Eles não serão
        mostrados de novo.
      </p>
      <div className="codigos">
        {codigos.map((c) => (
          <span key={c}>{c}</span>
        ))}
      </div>
      <div className="linha-form">
        <button className="secundario" onClick={() => navigator.clipboard?.writeText(texto)}>
          Copiar
        </button>
        <button
          className="secundario"
          onClick={() => {
            const url = URL.createObjectURL(new Blob([texto], { type: "text/plain" }));
            Object.assign(document.createElement("a"), { href: url, download: "billing-codigos-recuperacao.txt" }).click();
            URL.revokeObjectURL(url);
          }}
        >
          Baixar .txt
        </button>
        <label className="inline">
          <input type="checkbox" checked={guardei} onChange={(e) => setGuardei(e.target.checked)} /> Guardei os códigos em lugar seguro
        </label>
        <span style={{ flex: 1 }} />
        <button className="primario" disabled={!guardei} onClick={aoConcluir}>
          Concluir
        </button>
      </div>
    </div>
  );
}

export default function Seguranca({ me, recarregar }: { me: Me; recarregar: () => Promise<void> }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [setup, setSetup] = useState<Setup | null>(null);
  const [codigo, setCodigo] = useState("");
  const [codigos, setCodigos] = useState<string[] | null>(null);
  const [acao, setAcao] = useState<"" | "regenerar" | "desativar">("");
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState(false);

  const carregar = () => api<Status>("/auth/mfa").then(setStatus);
  useEffect(() => {
    carregar();
  }, []);

  async function executar(fn: () => Promise<void>) {
    setErro("");
    setAviso("");
    setOcupado(true);
    try {
      await fn();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível conectar ao servidor.");
    } finally {
      setOcupado(false);
    }
  }

  const iniciar = () => executar(async () => setSetup(await api<Setup>("/auth/mfa/totp/setup", { method: "POST" })));

  const confirmar = (ev: FormEvent) => {
    ev.preventDefault();
    executar(async () => {
      const r = await api<{ recovery_codes: string[]; me: LoginOut["me"] }>("/auth/mfa/totp/confirm", { json: { code: codigo } });
      setSetup(null);
      setCodigo("");
      setCodigos(r.recovery_codes);
    });
  };

  const enviarAcao = (ev: FormEvent) => {
    ev.preventDefault();
    executar(async () => {
      if (acao === "regenerar") {
        const r = await api<{ recovery_codes: string[] }>("/auth/mfa/recovery-codes", { json: { code: codigo } });
        setCodigos(r.recovery_codes);
      } else {
        await api("/auth/mfa/disable", { json: { code: codigo } });
        setAviso("Verificação em duas etapas desativada. As suas outras sessões foram encerradas.");
        await recarregar();
      }
      setAcao("");
      setCodigo("");
      await carregar();
    });
  };

  if (!status) return <div className="centro sutil">Carregando…</div>;

  if (codigos) {
    return (
      <>
        <div className="cabecalho">
          <h2>Segurança da conta</h2>
        </div>
        <Codigos
          codigos={codigos}
          aoConcluir={async () => {
            setCodigos(null);
            await Promise.all([carregar(), recarregar()]);
            setAviso("Verificação em duas etapas ativa. A partir de agora o login pede o código do aplicativo.");
          }}
        />
      </>
    );
  }

  return (
    <>
      <div className="cabecalho">
        <h2>Segurança da conta</h2>
      </div>
      {aviso && <div className="aviso">{aviso}</div>}

      <div className="painel">
        <h3>Sua conta</h3>
        <table>
          <tbody>
            <tr><td className="sutil">Nome</td><td>{me.name}</td></tr>
            <tr><td className="sutil">Login</td><td>{me.login}</td></tr>
            <tr><td className="sutil">E-mail</td><td>{me.email ?? "—"}</td></tr>
            <tr><td className="sutil">Forma de entrada</td><td>{me.source === "sso" ? "Google / Microsoft / login corporativo" : "Usuário e senha"}</td></tr>
          </tbody>
        </table>
      </div>

      <div className="painel">
        <h3>Verificação em duas etapas</h3>
        {status.enrolled ? (
          <>
            <p>
              <span className="status ativo">Ativa</span>{" "}
              <span className="sutil">
                O login pede o código do aplicativo autenticador. Códigos de recuperação restantes: <strong>{status.recovery_codes_left}</strong>.
              </span>
            </p>
            {status.recovery_codes_left <= 3 && (
              <div className="faixa"><strong>Restam poucos códigos de recuperação. Gere novos.</strong></div>
            )}
            {!acao ? (
              <div className="linha-form">
                <button className="secundario" onClick={() => { setAcao("regenerar"); setErro(""); }}>
                  Gerar novos códigos de recuperação
                </button>
                {!status.required && (
                  <button className="link perigo" onClick={() => { setAcao("desativar"); setErro(""); }}>
                    Desativar
                  </button>
                )}
                {status.required && <span className="sutil pequeno">Seu perfil exige a verificação; ela não pode ser desativada.</span>}
              </div>
            ) : (
              <form className="linha-form" onSubmit={enviarAcao}>
                <label>
                  {acao === "regenerar" ? "Código atual do aplicativo" : "Código do aplicativo ou de recuperação"}
                  <input value={codigo} onChange={(e) => setCodigo(e.target.value.trim())} autoFocus required placeholder="000000" />
                </label>
                <button className={acao === "desativar" ? "secundario" : "primario"} disabled={ocupado}>
                  {acao === "regenerar" ? "Gerar códigos" : "Confirmar desativação"}
                </button>
                <button type="button" className="link" onClick={() => { setAcao(""); setCodigo(""); setErro(""); }}>
                  Cancelar
                </button>
              </form>
            )}
          </>
        ) : setup ? (
          <div className="duas-colunas">
            <img className="qr" src={setup.qr_svg} alt="QR code para o aplicativo autenticador" />
            <form onSubmit={confirmar} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <ol className="lista-simples">
                <li>Instale um aplicativo autenticador: Google Authenticator, Microsoft Authenticator, Authy ou similar.</li>
                <li>No aplicativo, toque em “adicionar” e leia o QR code ao lado.</li>
                <li>Digite abaixo o código de 6 dígitos que aparecer.</li>
              </ol>
              <details>
                <summary className="sutil">Não consegue ler o QR code?</summary>
                <p className="sutil pequeno">Escolha “inserir chave manualmente” no aplicativo e digite:</p>
                <code className="segredo">{setup.secret}</code>
              </details>
              <label>
                Código de 6 dígitos
                <input
                  value={codigo}
                  onChange={(e) => setCodigo(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="000000"
                  autoFocus
                  required
                />
              </label>
              <div className="linha-form">
                <button className="primario" disabled={ocupado || codigo.length !== 6}>
                  Ativar
                </button>
                <button type="button" className="link" onClick={() => { setSetup(null); setCodigo(""); setErro(""); }}>
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        ) : (
          <>
            <p className="sutil">
              {status.required
                ? "Seu perfil exige verificação em duas etapas. Enquanto ela não estiver ativa, parte das suas permissões fica bloqueada."
                : "Proteja sua conta: além do login, o sistema passa a pedir um código do aplicativo autenticador do seu celular."}
            </p>
            <button className="primario" onClick={iniciar} disabled={ocupado}>
              Ativar verificação em duas etapas
            </button>
          </>
        )}
        {erro && <div className="erro">{erro}</div>}
      </div>
    </>
  );
}
