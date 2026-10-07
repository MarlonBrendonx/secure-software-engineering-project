import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { api, dataHora, ErroApi, Me, perfil, PERFIS_ATRIBUIVEIS } from "../api";

export interface Usuario {
  id: string;
  login: string;
  name: string;
  email: string | null;
  source: "sso" | "local";
  status: "active" | "terminated";
  roles: string[];
  mfa_enrolled: boolean;
  sso_providers: string[];
  created_at: string;
  terminated_at: string | null;
}

interface Pedido {
  id: string;
  user_id: string;
  role_code: string;
  justification: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  decided_at: string | null;
  decision_comment: string | null;
}

type Modal =
  | { tipo: "perfis"; u: Usuario }
  | { tipo: "desligar"; u: Usuario }
  | { tipo: "reset2fa"; u: Usuario }
  | null;

function Janela({ titulo, children, fechar }: { titulo: string; children: ReactNode; fechar: () => void }) {
  return (
    <div className="modal-fundo" onClick={fechar}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{titulo}</h2>
        {children}
      </div>
    </div>
  );
}

const msg = (e: unknown) => (e instanceof ErroApi ? e.message : "Não foi possível conectar ao servidor.");

function NovoUsuario({ aoCriar, cancelar }: { aoCriar: () => void; cancelar: () => void }) {
  const [f, setF] = useState({ login: "", name: "", email: "", source: "sso", roles: [] as string[] });
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);

  async function salvar(ev: FormEvent) {
    ev.preventDefault();
    setErro("");
    setOcupado(true);
    try {
      await api("/users", { json: f });
      aoCriar();
    } catch (e) {
      setErro(msg(e));
    } finally {
      setOcupado(false);
    }
  }

  return (
    <form className="painel grade-form" onSubmit={salvar}>
      <h3>Novo usuário</h3>
      <label>Nome<input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required autoFocus /></label>
      <label>Login<input value={f.login} onChange={(e) => setF({ ...f, login: e.target.value })} required pattern="[A-Za-z0-9._@\-]+" /></label>
      <label>E-mail<input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} required /></label>
      <label>
        Forma de entrada
        <select value={f.source} onChange={(e) => setF({ ...f, source: e.target.value })}>
          <option value="sso">Google / Microsoft (SSO)</option>
          <option value="local">Usuário e senha (contas externas)</option>
        </select>
      </label>
      <div className="largura-total">
        <span className="sutil pequeno">Perfis</span>
        <div className="checks">
          {PERFIS_ATRIBUIVEIS.map((r) => (
            <label key={r} className="inline">
              <input type="checkbox" checked={f.roles.includes(r)}
                onChange={(e) => setF({ ...f, roles: e.target.checked ? [...f.roles, r] : f.roles.filter((x) => x !== r) })} />
              {perfil(r)}
            </label>
          ))}
        </div>
      </div>
      <p className="sutil pequeno largura-total">
        {f.source === "sso"
          ? "A pessoa entra com a conta Google ou Microsoft deste e-mail. O vínculo é feito no primeiro login."
          : "A pessoa recebe por e-mail um link para criar a senha."}
      </p>
      {erro && <div className="erro largura-total">{erro}</div>}
      <div className="acoes largura-total">
        <button type="button" className="secundario" onClick={cancelar}>Cancelar</button>
        <button className="primario" disabled={ocupado}>Cadastrar</button>
      </div>
    </form>
  );
}

function ModalPerfis({ u, fechar, aoSalvar }: { u: Usuario; fechar: () => void; aoSalvar: () => void }) {
  const [roles, setRoles] = useState(u.roles);
  const [erro, setErro] = useState("");
  async function salvar() {
    try {
      await api(`/users/${u.id}/roles`, { method: "PUT", json: { roles } });
      aoSalvar();
    } catch (e) {
      setErro(msg(e));
    }
  }
  return (
    <Janela titulo={`Perfis de ${u.name}`} fechar={fechar}>
      <div className="checks" style={{ flexDirection: "column" }}>
        {PERFIS_ATRIBUIVEIS.map((r) => (
          <label key={r} className="inline">
            <input type="checkbox" checked={roles.includes(r)}
              onChange={(e) => setRoles(e.target.checked ? [...roles, r] : roles.filter((x) => x !== r))} />
            {perfil(r)}
          </label>
        ))}
      </div>
      <p className="sutil pequeno">A mudança vale imediatamente, sem novo login. Gerente e Administrador exigem verificação em duas etapas.</p>
      {erro && <div className="erro">{erro}</div>}
      <div className="acoes">
        <button className="secundario" onClick={fechar}>Cancelar</button>
        <button className="primario" onClick={salvar}>Salvar</button>
      </div>
    </Janela>
  );
}

function ModalMotivo({ titulo, texto, rotulo, botao, url, fechar, aoSalvar }: {
  titulo: string; texto: string; rotulo: string; botao: string; url: string; fechar: () => void; aoSalvar: () => void;
}) {
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState("");
  async function salvar(ev: FormEvent) {
    ev.preventDefault();
    try {
      await api(url, { json: { reason: motivo } });
      aoSalvar();
    } catch (e) {
      setErro(msg(e));
    }
  }
  return (
    <Janela titulo={titulo} fechar={fechar}>
      <form onSubmit={salvar} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <p className="sutil">{texto}</p>
        <label>{rotulo}<textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} minLength={5} required autoFocus /></label>
        {erro && <div className="erro">{erro}</div>}
        <div className="acoes">
          <button type="button" className="secundario" onClick={fechar}>Cancelar</button>
          <button className="primario">{botao}</button>
        </div>
      </form>
    </Janela>
  );
}

function Pedidos({ usuarios, aoMudar }: { usuarios: Usuario[]; aoMudar: () => void }) {
  const [filtro, setFiltro] = useState<"pending" | "approved" | "rejected">("pending");
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [erro, setErro] = useState("");
  const nomes = useMemo(() => Object.fromEntries(usuarios.map((u) => [u.id, u])), [usuarios]);

  const carregar = () => api<Pedido[]>(`/access-requests?status=${filtro}`).then(setPedidos).catch((e) => setErro(msg(e)));
  useEffect(() => {
    carregar();
  }, [filtro]);

  async function decidir(p: Pedido, approve: boolean) {
    const comment = approve ? null : window.prompt("Motivo da recusa (opcional):") ?? undefined;
    if (comment === undefined) return;
    setErro("");
    try {
      await api(`/access-requests/${p.id}/decision`, { json: { approve, comment } });
      await carregar();
      aoMudar();
    } catch (e) {
      setErro(msg(e));
    }
  }

  return (
    <>
      <div className="cabecalho">
        <h2>Pedidos de acesso</h2>
        <select value={filtro} onChange={(e) => setFiltro(e.target.value as typeof filtro)}>
          <option value="pending">Pendentes</option>
          <option value="approved">Aprovados</option>
          <option value="rejected">Recusados</option>
        </select>
      </div>
      {erro && <div className="erro">{erro}</div>}
      {pedidos.length === 0 ? (
        <div className="vazio">Nenhum pedido {filtro === "pending" ? "pendente" : filtro === "approved" ? "aprovado" : "recusado"}.</div>
      ) : (
        <table>
          <thead><tr><th>Pessoa</th><th>Perfil pedido</th><th>Justificativa</th><th>Quando</th><th></th></tr></thead>
          <tbody>
            {pedidos.map((p) => (
              <tr key={p.id}>
                <td><strong>{nomes[p.user_id]?.name ?? "—"}</strong><div className="sutil pequeno">{nomes[p.user_id]?.email}</div></td>
                <td>{perfil(p.role_code)}</td>
                <td>{p.justification}{p.decision_comment && <div className="sutil pequeno">Decisão: {p.decision_comment}</div>}</td>
                <td>{dataHora(p.created_at)}</td>
                <td className="acoes-linha">
                  {p.status === "pending" ? (
                    <>
                      <button className="primario pequeno" onClick={() => decidir(p, true)}>Aprovar</button>
                      <button className="link perigo" onClick={() => decidir(p, false)}>Recusar</button>
                    </>
                  ) : (
                    <span className={`status ${p.status === "approved" ? "aprovado" : "reprovado"}`}>
                      {p.status === "approved" ? "Aprovado" : "Recusado"}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

export default function Usuarios({ me }: { me: Me }) {
  const [secao, setSecao] = useState<"usuarios" | "pedidos">("usuarios");
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [busca, setBusca] = useState("");
  const [mostrarDesligados, setMostrarDesligados] = useState(false);
  const [criando, setCriando] = useState(false);
  const [modal, setModal] = useState<Modal>(null);
  const [aviso, setAviso] = useState("");
  const [erro, setErro] = useState("");
  const [pendentes, setPendentes] = useState(0);

  const carregar = async () => {
    try {
      setUsuarios(await api<Usuario[]>("/users"));
      setPendentes((await api<Pedido[]>("/access-requests?status=pending")).length);
    } catch (e) {
      setErro(msg(e));
    }
  };
  useEffect(() => {
    carregar();
  }, []);

  const lista = usuarios.filter(
    (u) =>
      (mostrarDesligados || u.status === "active") &&
      (!busca || `${u.name} ${u.login} ${u.email ?? ""}`.toLowerCase().includes(busca.toLowerCase())),
  );

  const concluir = (texto: string) => {
    setModal(null);
    setAviso(texto);
    carregar();
  };

  return (
    <div className="com-lateral">
      <aside className="lateral">
        <button className={secao === "usuarios" ? "item ativo" : "item"} onClick={() => setSecao("usuarios")}>Usuários</button>
        <button className={secao === "pedidos" ? "item ativo" : "item"} onClick={() => setSecao("pedidos")}>
          Pedidos de acesso {pendentes > 0 && <span className="contador" style={{ marginLeft: 6 }}>{pendentes}</span>}
        </button>
      </aside>
      <section>
        {secao === "pedidos" ? (
          <Pedidos usuarios={usuarios} aoMudar={carregar} />
        ) : (
          <>
            <div className="cabecalho">
              <h2>Usuários</h2>
              <span className="contador">{lista.length}</span>
              <input placeholder="Buscar por nome, login ou e-mail" value={busca} onChange={(e) => setBusca(e.target.value)} />
              <label className="inline"><input type="checkbox" checked={mostrarDesligados} onChange={(e) => setMostrarDesligados(e.target.checked)} /> Mostrar desligados</label>
              {!criando && <button className="primario" onClick={() => setCriando(true)}>Novo usuário</button>}
            </div>
            {aviso && <div className="aviso">{aviso}</div>}
            {erro && <div className="erro">{erro}</div>}
            {criando && <NovoUsuario cancelar={() => setCriando(false)} aoCriar={() => { setCriando(false); concluir("Usuário cadastrado."); }} />}
            <table>
              <thead>
                <tr><th>Nome</th><th>Entrada</th><th>Perfis</th><th>2 etapas</th><th>Situação</th><th></th></tr>
              </thead>
              <tbody>
                {lista.map((u) => {
                  const eu = u.id === me.id;
                  return (
                    <tr key={u.id} className={u.status === "terminated" ? "inativo" : ""}>
                      <td><strong>{u.name}</strong>{eu && <span className="sutil"> (você)</span>}<div className="sutil pequeno">{u.login} · {u.email}</div></td>
                      <td>
                        {u.source === "local" ? "Usuário e senha" : u.sso_providers.length ? u.sso_providers.map((p) => p[0].toUpperCase() + p.slice(1)).join(", ") : <span className="sutil">SSO (ainda não entrou)</span>}
                      </td>
                      <td>
                        <div className="etiquetas">
                          {u.roles.length ? u.roles.map((r) => <span key={r} className="etiqueta">{perfil(r)}</span>) : <span className="etiqueta cinza">Sem perfil</span>}
                        </div>
                      </td>
                      <td>{u.mfa_enrolled ? <span className="etiqueta verde">Ativa</span> : <span className="etiqueta cinza">Não</span>}</td>
                      <td>{u.status === "active" ? <span className="status ativo">Ativo</span> : <span className="status encerrado">Desligado em {dataHora(u.terminated_at)}</span>}</td>
                      <td className="acoes-linha">
                        {u.status === "active" && !eu && (
                          <>
                            <button className="link" onClick={() => setModal({ tipo: "perfis", u })}>Perfis</button>
                            {u.mfa_enrolled && <button className="link" onClick={() => setModal({ tipo: "reset2fa", u })}>Resetar 2FA</button>}
                            <button className="link perigo" onClick={() => setModal({ tipo: "desligar", u })}>Desligar</button>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </>
        )}
      </section>

      {modal?.tipo === "perfis" && (
        <ModalPerfis u={modal.u} fechar={() => setModal(null)} aoSalvar={() => concluir(`Perfis de ${modal.u.name} atualizados.`)} />
      )}
      {modal?.tipo === "desligar" && (
        <ModalMotivo titulo={`Desligar ${modal.u.name}`} url={`/users/${modal.u.id}/terminate`} rotulo="Motivo" botao="Desligar agora"
          texto="O acesso é bloqueado na hora: todas as sessões abertas são encerradas e as substituições ligadas à pessoa são revogadas."
          fechar={() => setModal(null)} aoSalvar={() => concluir(`${modal.u.name} foi desligado(a) e as sessões foram encerradas.`)} />
      )}
      {modal?.tipo === "reset2fa" && (
        <ModalMotivo titulo={`Resetar 2FA de ${modal.u.name}`} url={`/users/${modal.u.id}/mfa/reset`} rotulo="Motivo (ex.: perdeu o celular, chamado 1234)" botao="Resetar"
          texto="Remove o autenticador e encerra as sessões. No próximo login a pessoa cadastra o novo celular."
          fechar={() => setModal(null)} aoSalvar={() => concluir(`2FA de ${modal.u.name} removido.`)} />
      )}
    </div>
  );
}
