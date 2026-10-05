import os

os.environ.update({
    "BILLING_AMBIENTE": "teste",
    "BILLING_DATABASE_URL": "sqlite://",
    "BILLING_OPS_TOKEN": "token-ops-teste",
    "BILLING_JWT_CHAVE_ATUAL": "chave-de-teste-com-tamanho-suficiente-0123456789",
    "BILLING_MFA_CHAVE_CIFRAGEM": "chave-de-cifragem-de-teste",
})

import pyotp  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import db as db_mod  # noqa: E402
from app.idp import ProvedorFake, definir_provedor  # noqa: E402
from app.main import app  # noqa: E402
from app.models import LogAuditoria, Papel, Usuario  # noqa: E402
from app.ratelimit import LimitadorMemoria, definir_limitador  # noqa: E402
from app.seguranca import decifrar_segredo  # noqa: E402

SENHA = "Senha-Corporativa-1"


@pytest.fixture(autouse=True)
def ambiente():
    engine = db_mod.configurar_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    db_mod.Base.metadata.create_all(engine)
    provedor = ProvedorFake({})
    definir_provedor(provedor)
    definir_limitador(LimitadorMemoria(10))
    yield provedor
    db_mod.Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    s = db_mod.nova_sessao()
    yield s
    s.close()


@pytest.fixture
def novo_usuario(ambiente, db):
    def criar(login: str, papel: Papel, senha: str = SENHA, ativo: bool = True) -> Usuario:
        ambiente.usuarios[login] = senha
        u = Usuario(login=login, nome=login.title(), papel=papel, ativo=ativo)
        db.add(u)
        db.commit()
        return u
    return criar


def cliente_http() -> TestClient:
    # HTTPS: os cookies são "Secure" e só trafegam em conexão criptografada
    return TestClient(app, base_url="https://testserver")


@pytest.fixture
def client():
    return cliente_http()


def entrar(client: TestClient, login: str, senha: str = SENHA) -> str:
    """Faz o fluxo completo (usuário/senha + segundo fator) e devolve o segredo TOTP."""
    r = client.post("/api/auth/login", json={"login": login, "senha": senha})
    assert r.status_code == 200, r.text
    if r.json()["etapa"] == "mfa_cadastro":
        segredo = client.post("/api/auth/mfa/cadastro").json()["segredo"]
    else:
        s = db_mod.nova_sessao()
        u = s.query(Usuario).filter_by(login=login).one()
        segredo = decifrar_segredo(u.mfa_segredo_cifrado)
        s.close()
    r = client.post("/api/auth/mfa/verificar", json={"codigo": pyotp.TOTP(segredo).now()})
    assert r.status_code == 200, r.text
    return segredo


@pytest.fixture
def logado(novo_usuario):
    """Cria um usuário com o papel pedido e devolve um cliente HTTP já autenticado."""
    def criar(papel: Papel, login: str | None = None) -> TestClient:
        login = login or papel.value.lower()
        novo_usuario(login, papel)
        c = cliente_http()
        entrar(c, login)
        return c
    return criar


def logs(tipo=None, **filtros):
    s = db_mod.nova_sessao()
    q = s.query(LogAuditoria)
    if tipo:
        q = q.filter(LogAuditoria.tipo_acao == tipo)
    for k, v in filtros.items():
        q = q.filter(getattr(LogAuditoria, k) == v)
    itens = q.all()
    s.close()
    return itens
