import { FormEvent, useEffect, useState } from "react";
import { api, ErroApi, Papel, Usuario } from "../api";

interface UsuarioAdmin extends Usuario {
  email: string | null;
  ativo: boolean;
  mfa_ativo: boolean;
  sessoes_ativas: number;
}

const PAPEIS: Papel[] = ["ADMINISTRADOR", "OPERACIONAL", "GESTOR", "AUDITOR", "OPERACAO"];

export default function Usuarios({ eu }: { eu: Usuario }) {
  const [lista, setLista] = useState<UsuarioAdmin[]>([]);
  const [novo, setNovo] = useState({ login: "", nome: "", email: "", papel: "OPERACIONAL" as Papel });
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");

  const carregar = () => api<UsuarioAdmin[]>("/usuarios").then(setLista);
  useEffect(() => {
    carregar();
  }, []);

  async function acao(fn: () => Promise<unknown>, msg?: string) {
    setErro("");
    setAviso("");
    try {
      await fn();
      if (msg) setAviso(msg);
      carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Erro inesperado.");
    }
  }

  function criar(ev: FormEvent) {
    ev.preventDefault();
    acao(async () => {
      await api("/usuarios", { method: "POST", json: { ...novo, email: novo.email || null } });
      setNovo({ login: "", nome: "", email: "", papel: "OPERACIONAL" });
    }, "Usuário cadastrado. O segundo fator será configurado no primeiro login.");
  }

  return (
    <section>
      <div className="cabecalho"><h2>Usuários</h2></div>
      <p className="sutil">
        A senha é a do login corporativo. Aqui se define quem pode entrar no sistema e com qual perfil. Mudar o
        perfil ou desativar encerra as sessões abertas do usuário.
      </p>

      <form className="painel linha-form" onSubmit={criar}>
        <input placeholder="Login corporativo" value={novo.login} onChange={(e) => setNovo({ ...novo, login: e.target.value })} required />
        <input placeholder="Nome" value={novo.nome} onChange={(e) => setNovo({ ...novo, nome: e.target.value })} required />
        <input placeholder="E-mail (opcional)" value={novo.email} onChange={(e) => setNovo({ ...novo, email: e.target.value })} />
        <select value={novo.papel} onChange={(e) => setNovo({ ...novo, papel: e.target.value as Papel })}>
          {PAPEIS.map((p) => <option key={p}>{p}</option>)}
        </select>
        <button className="primario">Adicionar</button>
      </form>
      {erro && <div className="erro">{erro}</div>}
      {aviso && <div className="aviso">{aviso}</div>}

      <table>
        <thead>
          <tr><th>Login</th><th>Nome</th><th>Perfil</th><th>Situação</th><th>2FA</th><th>Sessões</th><th /></tr>
        </thead>
        <tbody>
          {lista.map((u) => (
            <tr key={u.id} className={u.ativo ? "" : "inativo"}>
              <td>{u.login}</td>
              <td>{u.nome}</td>
              <td>
                <select
                  value={u.papel}
                  disabled={u.id === eu.id}
                  onChange={(e) => {
                    if (confirm(`Mudar o perfil de ${u.nome} para ${e.target.value}? As sessões dele serão encerradas.`))
                      acao(() => api(`/usuarios/${u.id}`, { method: "PUT", json: { papel: e.target.value } }));
                  }}
                >
                  {PAPEIS.map((p) => <option key={p}>{p}</option>)}
                </select>
              </td>
              <td>{u.ativo ? "Ativo" : "Inativo"}</td>
              <td>{u.mfa_ativo ? "Configurado" : "Pendente"}</td>
              <td>{u.sessoes_ativas}</td>
              <td className="acoes-linha">
                {u.id !== eu.id && (
                  <button className="link" onClick={() => acao(() => api(`/usuarios/${u.id}`, { method: "PUT", json: { ativo: !u.ativo } }))}>
                    {u.ativo ? "Desativar" : "Reativar"}
                  </button>
                )}
                <button className="link" onClick={() => acao(() => api(`/usuarios/${u.id}/revogar-sessoes`, { method: "POST" }), "Sessões encerradas.")}>
                  Encerrar sessões
                </button>
                <button
                  className="link"
                  onClick={() => confirm(`Redefinir o segundo fator de ${u.nome}? Ele precisará cadastrar de novo no próximo login.`) &&
                    acao(() => api(`/usuarios/${u.id}/redefinir-mfa`, { method: "POST" }), "Segundo fator redefinido.")}
                >
                  Redefinir 2FA
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
