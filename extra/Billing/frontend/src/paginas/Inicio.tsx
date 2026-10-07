import { FormEvent, useState } from "react";
import { api, data, ErroApi, Me, perfil, PERFIS_ATRIBUIVEIS } from "../api";

const PERMISSOES: Record<string, string> = {
  "access.request": "Solicitar acesso",
  "entries.read": "Consultar lançamentos e dados",
  "entries.write": "Criar e corrigir lançamentos",
  "entries.approve": "Aprovar ou devolver lançamentos",
  "reports.generate": "Gerar relatórios",
  "erp.generate": "Gerar carga para o ERP",
  "erp.download": "Baixar carga do ERP",
  "periods.close": "Fechar período",
  "periods.reopen.request": "Solicitar reabertura de período",
  "periods.reopen.approve": "Aprovar reabertura de período",
  "contracts.read": "Consultar contratos",
  "contracts.manage": "Alterar regras contratuais",
  "users.manage": "Gerir usuários e perfis",
  "delegations.manage": "Conceder substituições temporárias",
  "settings.manage": "Alterar parâmetros do sistema",
  "audit.read": "Consultar trilha de auditoria",
};

function PedirAcesso({ me, destaque }: { me: Me; destaque: boolean }) {
  const opcoes = PERFIS_ATRIBUIVEIS.filter((r) => !me.roles.includes(r) && !me.roles_pending_mfa.includes(r));
  const [perfilPedido, setPerfilPedido] = useState(opcoes[0] ?? "");
  const [justificativa, setJustificativa] = useState("");
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState(false);

  async function enviar(ev: FormEvent) {
    ev.preventDefault();
    setErro("");
    setAviso("");
    setOcupado(true);
    try {
      await api("/access-requests", { json: { role_code: perfilPedido, justification: justificativa } });
      setAviso(`Pedido enviado. Um administrador vai analisar o acesso de ${perfil(perfilPedido)}.`);
      setJustificativa("");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível conectar ao servidor.");
    } finally {
      setOcupado(false);
    }
  }

  if (!opcoes.length) return null;
  const formulario = (
      <form className="grade-form" onSubmit={enviar}>
        <label>
          Perfil
          <select value={perfilPedido} onChange={(e) => setPerfilPedido(e.target.value)}>
            {opcoes.map((r) => (
              <option key={r} value={r}>{perfil(r)}</option>
            ))}
          </select>
        </label>
        <label className="largura-total">
          Justificativa
          <textarea value={justificativa} onChange={(e) => setJustificativa(e.target.value)} minLength={5} required
            placeholder="Ex.: entrei na equipe de Faturamento e Contas" />
        </label>
        {erro && <div className="erro largura-total">{erro}</div>}
        {aviso && <div className="aviso largura-total">{aviso}</div>}
        <div className="acoes largura-total">
          <button className="primario" disabled={ocupado}>Enviar pedido</button>
        </div>
      </form>
  );
  return destaque ? (
    <div className="painel">
      <h3>Solicitar acesso</h3>
      {formulario}
    </div>
  ) : (
    <details className="painel">
      <summary className="sutil">Precisa de outro perfil? Solicitar acesso</summary>
      <div style={{ marginTop: 12 }}>{formulario}</div>
    </details>
  );
}

export default function Inicio({ me }: { me: Me; recarregar: () => Promise<void>; ir: (c: string) => void }) {
  const semPerfil = me.roles.every((r) => r === "none") && me.roles_pending_mfa.length === 0;
  return (
    <>
      <div className="cabecalho">
        <h2>Olá, {me.name.split(" ")[0]}</h2>
      </div>

      {semPerfil && (
        <div className="painel">
          <h3>Você ainda não tem perfil de acesso</h3>
          <p className="sutil">Seu login funcionou, mas um administrador precisa liberar o perfil adequado ao seu trabalho.</p>
        </div>
      )}
      {me.permissions.includes("access.request") && <PedirAcesso me={me} destaque={semPerfil} />}

      <div className="painel">
        <h3>Seus perfis e permissões</h3>
        <div className="etiquetas" style={{ marginBottom: 12 }}>
          {me.roles.map((r) => (
            <span key={r} className={r === "none" ? "etiqueta cinza" : "etiqueta"}>{perfil(r)}</span>
          ))}
          {me.roles_pending_mfa.map((r) => (
            <span key={r} className="etiqueta cinza">{perfil(r)} · falta 2FA</span>
          ))}
        </div>
        <ul className="lista-simples">
          {me.permissions.filter((p) => p !== "access.request").map((p) => (
            <li key={p}>{PERMISSOES[p] ?? p}</li>
          ))}
        </ul>
        {me.permissions_requiring_mfa.length > 0 && (
          <>
            <p className="sutil" style={{ marginTop: 12 }}>Liberadas depois que você ativar a verificação em duas etapas:</p>
            <ul className="lista-simples sutil">
              {me.permissions_requiring_mfa.filter((p) => p !== "access.request").map((p) => (
                <li key={p}>{PERMISSOES[p] ?? p}</li>
              ))}
            </ul>
          </>
        )}
      </div>

      {me.delegations.length > 0 && (
        <div className="painel">
          <h3>Substituições ativas</h3>
          <ul className="lista-simples">
            {me.delegations.map((d) => (
              <li key={d.id}>
                Você está substituindo como <strong>{perfil(d.role)}</strong> até {data(d.ends_at)}. As ações ficam registradas no seu nome.
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="painel">
        <h3>Próximas etapas do sistema</h3>
        <p className="sutil">
          Contratos, lançamentos, fila de aprovação, fechamento e carga ERP chegam nos próximos módulos. Esta versão traz o acesso:
          login, verificação em duas etapas, usuários, substituições, auditoria e parâmetros.
        </p>
      </div>
    </>
  );
}
