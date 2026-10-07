import { FormEvent, useState } from "react";
import { api, ErroApi } from "../api";

export default function NovaSenha({ token, ir }: { token: string; ir: (c: string) => void }) {
  const [senha, setSenha] = useState("");
  const [repetir, setRepetir] = useState("");
  const [erro, setErro] = useState("");
  const [pronto, setPronto] = useState(false);
  const [ocupado, setOcupado] = useState(false);

  async function salvar(ev: FormEvent) {
    ev.preventDefault();
    if (senha !== repetir) return setErro("As senhas não conferem.");
    setErro("");
    setOcupado(true);
    try {
      await api("/auth/password/reset", { json: { token, new_password: senha } });
      setPronto(true);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível conectar ao servidor.");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="login-fundo">
      <div className="login-cartao">
        <div className="marca">Billing</div>
        {pronto ? (
          <form onSubmit={(e) => { e.preventDefault(); ir("/login"); }}>
            <h1>Senha criada</h1>
            <div className="aviso">Pronto. Use a nova senha para entrar.</div>
            <button className="primario largo">Ir para o login</button>
          </form>
        ) : (
          <form onSubmit={salvar}>
            <h1>Criar nova senha</h1>
            <p className="sutil">Mínimo de 12 caracteres, combinando ao menos 3 tipos: minúsculas, maiúsculas, dígitos e símbolos.</p>
            <label>
              Nova senha
              <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} autoComplete="new-password" autoFocus required />
            </label>
            <label>
              Repita a senha
              <input type="password" value={repetir} onChange={(e) => setRepetir(e.target.value)} autoComplete="new-password" required />
            </label>
            {erro && <div className="erro">{erro}</div>}
            <button className="primario largo" disabled={ocupado || !token}>
              Salvar
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
