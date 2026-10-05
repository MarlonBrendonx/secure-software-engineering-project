"""Testes do módulo de autenticação (critérios de aceite 1 a 6)."""
import re
from datetime import timedelta

import pyotp

from app import db as db_mod
from app.main import app
from app.models import Papel, Sessao, TipoAcao, Usuario, agora
from app.seguranca import TIPO_ACESSO, emitir_jwt

from .conftest import SENHA, cliente_http, entrar, logs

ROTAS_PUBLICAS = {
    "/api/auth/login", "/api/auth/mfa/cadastro", "/api/auth/mfa/verificar",
    "/api/auth/renovar", "/api/auth/logout", "/api/saude/provedor-identidade", "/api/saude/api",
}


# --- Critério 1: usuário não autenticado só acessa o login --------------------
def test_todas_as_rotas_protegidas_recusam_quem_nao_esta_logado(client):
    verificadas = 0
    for caminho_modelo, operacoes in app.openapi()["paths"].items():
        if caminho_modelo in ROTAS_PUBLICAS:
            continue
        caminho = re.sub(r"\{[^}]+\}", "1", caminho_modelo)
        for metodo in operacoes:
            r = client.request(metodo, caminho, json={})
            assert r.status_code == 401, f"{metodo} {caminho} respondeu {r.status_code}"
            verificadas += 1
    assert verificadas > 25


def test_fluxo_completo_de_login_com_cadastro_do_segundo_fator(client, novo_usuario):
    novo_usuario("maria", Papel.OPERACIONAL)
    r = client.post("/api/auth/login", json={"login": "Maria", "senha": SENHA})
    assert r.json() == {"etapa": "mfa_cadastro"}
    cad = client.post("/api/auth/mfa/cadastro").json()
    assert cad["uri"].startswith("otpauth://totp/")
    r = client.post("/api/auth/mfa/verificar", json={"codigo": pyotp.TOTP(cad["segredo"]).now()})
    assert r.status_code == 200
    assert r.json()["papel"] == "OPERACIONAL"

    sessao = client.get("/api/auth/sessao")
    assert sessao.status_code == 200
    assert sessao.json()["usuario"]["login"] == "maria"
    assert 0 < sessao.json()["acesso_expira_em_segundos"] <= 15 * 60
    assert logs(TipoAcao.LOGIN_OK, login="maria")
    assert logs(TipoAcao.MFA_CADASTRADO, login="maria")

    # Segundo login: já pede só o código
    c2 = cliente_http()
    assert c2.post("/api/auth/login", json={"login": "maria", "senha": SENHA}).json() == {"etapa": "mfa_verificacao"}


def test_cookies_de_sessao_sao_httponly_secure_e_samesite(client, novo_usuario):
    novo_usuario("ana", Papel.GESTOR)
    client.post("/api/auth/login", json={"login": "ana", "senha": SENHA})
    segredo = client.post("/api/auth/mfa/cadastro").json()["segredo"]
    r = client.post("/api/auth/mfa/verificar", json={"codigo": pyotp.TOTP(segredo).now()})
    cookies = r.headers.get_list("set-cookie")
    for nome in ("billing_access", "billing_refresh"):
        c = next(c for c in cookies if c.startswith(nome + "="))
        assert "HttpOnly" in c and "Secure" in c and "SameSite=strict" in c


def test_credenciais_erradas_ou_usuario_sem_cadastro_local_recebem_a_mesma_resposta(client, novo_usuario, ambiente):
    novo_usuario("joao", Papel.OPERACIONAL)
    ambiente.usuarios["externo"] = SENHA  # existe no login corporativo, mas não na base do sistema
    r1 = client.post("/api/auth/login", json={"login": "joao", "senha": "errada"})
    r2 = client.post("/api/auth/login", json={"login": "externo", "senha": SENHA})
    r3 = client.post("/api/auth/login", json={"login": "ninguem", "senha": "x"})
    assert r1.status_code == r2.status_code == r3.status_code == 401
    assert r1.json() == r2.json() == r3.json()
    motivos = {l.detalhes["motivo"] for l in logs(TipoAcao.LOGIN_FALHA)}
    assert motivos == {"credenciais_invalidas", "usuario_sem_cadastro_local"}
    falha = logs(TipoAcao.LOGIN_FALHA, login="joao")[0]
    assert falha.ip and falha.data_hora


def test_usuario_inativo_nao_entra(client, novo_usuario):
    novo_usuario("inativo", Papel.OPERACIONAL, ativo=False)
    assert client.post("/api/auth/login", json={"login": "inativo", "senha": SENHA}).status_code == 401


# --- Critério 2: limite de 10 tentativas por minuto por IP --------------------
def test_decima_primeira_tentativa_no_mesmo_minuto_e_bloqueada(client, novo_usuario):
    novo_usuario("alvo", Papel.OPERACIONAL)
    for _ in range(10):
        assert client.post("/api/auth/login", json={"login": "alvo", "senha": "chute"}).status_code == 401
    r = client.post("/api/auth/login", json={"login": "alvo", "senha": SENHA})  # nem a senha certa passa
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) <= 60
    for _ in range(5):
        client.post("/api/auth/login", json={"login": "alvo", "senha": "chute"})
    assert len(logs(TipoAcao.LOGIN_BLOQUEADO)) == 1  # um registro por janela, não um por tentativa


def test_limite_tambem_vale_para_o_codigo_do_segundo_fator(client, novo_usuario):
    novo_usuario("pedro", Papel.OPERACIONAL)
    client.post("/api/auth/login", json={"login": "pedro", "senha": SENHA})
    client.post("/api/auth/mfa/cadastro")
    codigos = [client.post("/api/auth/mfa/verificar", json={"codigo": "000000"}).status_code for _ in range(11)]
    assert codigos[-1] == 429


# --- Critério 3: sem o segundo fator, o login não é concluído -----------------
def test_sem_segundo_fator_nao_ha_sessao(client, novo_usuario):
    novo_usuario("carla", Papel.GESTOR)
    client.post("/api/auth/login", json={"login": "carla", "senha": SENHA})
    assert client.get("/api/auth/sessao").status_code == 401
    client.post("/api/auth/mfa/cadastro")
    assert client.post("/api/auth/mfa/verificar", json={"codigo": "123456"}).status_code == 401
    assert client.get("/api/auth/sessao").status_code == 401
    assert logs(TipoAcao.MFA_FALHA, login="carla")


def test_verificar_codigo_sem_passar_pela_senha_e_recusado(client):
    assert client.post("/api/auth/mfa/verificar", json={"codigo": "123456"}).status_code == 401


def test_token_do_desafio_nao_serve_como_token_de_acesso(client, novo_usuario):
    novo_usuario("bia", Papel.GESTOR)
    client.post("/api/auth/login", json={"login": "bia", "senha": SENHA})
    desafio = client.cookies.get("billing_mfa")
    c = cliente_http()
    c.cookies.set("billing_access", desafio, domain="testserver")
    assert c.get("/api/auth/sessao").status_code == 401


# --- Critério 4: token revogado ou expirado é recusado -----------------------
def test_token_expirado_e_recusado(client, novo_usuario):
    u = novo_usuario("leo", Papel.GESTOR)
    entrar(client, "leo")
    sid = client.get("/api/auth/sessao").json() and _sessao_de("leo").id
    vencido = emitir_jwt({"sub": str(u.id), "papel": "GESTOR", "sid": sid, "typ": TIPO_ACESSO}, timedelta(seconds=-5))
    c = cliente_http()
    c.cookies.set("billing_access", vencido, domain="testserver")
    assert c.get("/api/auth/sessao").status_code == 401


def test_token_assinado_com_outra_chave_e_recusado(client, novo_usuario):
    import jwt

    u = novo_usuario("eva", Papel.ADMINISTRADOR)
    entrar(client, "eva")
    forjado = jwt.encode({"sub": str(u.id), "papel": "ADMINISTRADOR", "sid": _sessao_de("eva").id, "typ": TIPO_ACESSO,
                          "iat": agora(), "exp": agora() + timedelta(minutes=5), "jti": "x"},
                         "chave-falsa", algorithm="HS256", headers={"kid": "k1"})
    c = cliente_http()
    c.cookies.set("billing_access", forjado, domain="testserver")
    assert c.get("/api/auth/sessao").status_code == 401


def test_revogacao_tem_efeito_imediato(logado):
    gestor = logado(Papel.GESTOR, "gil")
    admin = logado(Papel.ADMINISTRADOR, "adm")
    assert gestor.get("/api/auth/sessao").status_code == 200
    uid = _usuario("gil").id
    assert admin.post(f"/api/usuarios/{uid}/revogar-sessoes").json() == {"sessoes_revogadas": 1}
    assert gestor.get("/api/auth/sessao").status_code == 401   # o token ainda não expirou, mas a sessão caiu
    assert gestor.post("/api/auth/renovar").status_code == 401
    assert logs(TipoAcao.SESSAO_REVOGADA, entidade_id=str(uid))


def test_desativar_usuario_derruba_as_sessoes(logado):
    op = logado(Papel.OPERACIONAL, "otto")
    admin = logado(Papel.ADMINISTRADOR, "adm")
    admin.put(f"/api/usuarios/{_usuario('otto').id}", json={"ativo": False})
    assert op.get("/api/auth/sessao").status_code == 401


def test_renovacao_troca_o_token_e_o_anterior_deixa_de_valer(client, novo_usuario):
    novo_usuario("rui", Papel.OPERACIONAL)
    entrar(client, "rui")
    antigo = client.cookies.get("billing_refresh")
    assert client.post("/api/auth/renovar").status_code == 204
    novo = client.cookies.get("billing_refresh")
    assert novo and novo != antigo
    assert client.get("/api/auth/sessao").status_code == 200

    c = cliente_http()
    c.cookies.set("billing_refresh", antigo, domain="testserver", path="/api/auth")
    assert c.post("/api/auth/renovar").status_code == 401


def test_sessao_nao_renova_depois_do_limite_absoluto(client, novo_usuario):
    novo_usuario("tia", Papel.OPERACIONAL)
    entrar(client, "tia")
    s = db_mod.nova_sessao()
    sess = s.query(Sessao).one()
    sess.expira_em = agora() - timedelta(seconds=1)
    s.commit()
    s.close()
    assert client.post("/api/auth/renovar").status_code == 401
    assert client.get("/api/auth/sessao").status_code == 401


# --- Critério 5: logout encerra de verdade ------------------------------------
def test_logout_revoga_no_servidor_e_apaga_os_cookies(client, novo_usuario):
    novo_usuario("lia", Papel.GESTOR)
    entrar(client, "lia")
    acesso_antigo = client.cookies.get("billing_access")
    r = client.post("/api/auth/logout")
    assert r.status_code == 204
    assert "cookies" in r.headers["clear-site-data"]
    apagados = [c for c in r.headers.get_list("set-cookie") if "Max-Age=0" in c or "expires=Thu, 01 Jan 1970" in c]
    assert {c.split("=")[0] for c in apagados} >= {"billing_access", "billing_refresh"}
    assert client.cookies.get("billing_access") is None

    # "Reabrir a página": nova requisição exige login
    assert client.get("/api/auth/sessao").status_code == 401
    # Mesmo quem tivesse guardado o token antigo não entra mais
    c = cliente_http()
    c.cookies.set("billing_access", acesso_antigo, domain="testserver")
    assert c.get("/api/auth/sessao").status_code == 401
    assert _sessao_de("lia").motivo_revogacao == "logout"
    assert logs(TipoAcao.LOGOUT, login="lia")


def test_logout_funciona_com_token_de_acesso_ja_expirado(client, novo_usuario):
    novo_usuario("ivo", Papel.GESTOR)
    entrar(client, "ivo")
    client.cookies.delete("billing_access")
    assert client.post("/api/auth/logout").status_code == 204
    assert _sessao_de("ivo").revogada_em is not None


# --- Critério 6: saúde do provedor de identidade -----------------------------
def test_saude_do_provedor_sem_login_de_usuario(client, ambiente):
    assert client.get("/api/saude/provedor-identidade").status_code == 401
    assert client.get("/api/saude/provedor-identidade", headers={"X-Ops-Token": "errado"}).status_code == 401
    r = client.get("/api/saude/provedor-identidade", headers={"X-Ops-Token": "token-ops-teste"})
    assert r.status_code == 200 and r.json()["saudavel"] is True
    ambiente.saudavel = False
    assert client.get("/api/saude/provedor-identidade", headers={"X-Ops-Token": "token-ops-teste"}).status_code == 503


# --- auxiliares ---------------------------------------------------------------
def _usuario(login):
    s = db_mod.nova_sessao()
    u = s.query(Usuario).filter_by(login=login).one()
    s.close()
    return u


def _sessao_de(login):
    s = db_mod.nova_sessao()
    sess = s.query(Sessao).join(Usuario).filter(Usuario.login == login).order_by(Sessao.criada_em.desc()).first()
    s.close()
    return sess
