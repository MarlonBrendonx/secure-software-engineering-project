"""Testes contra Postgres e Redis reais.

Variáveis (com padrões para o ambiente local):
  NBB_TEST_OWNER_URL  usuário dono do schema (roda as migrations)
  NBB_TEST_APP_URL    usuário da aplicação (sem UPDATE/DELETE na auditoria)
  NBB_TEST_REDIS_URL
"""
import os
import uuid
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import pytest
import redis
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from nbb import db as dbmod
from nbb.api.deps import CSRF_COOKIE, CSRF_HEADER
from nbb.config import Settings
from nbb.core.audit import Actor, set_actor
from nbb.core.mailer import OutboxMailer
from nbb.core import totp
from nbb.core.crypto import DataCipher, generate_key
from nbb.core.oidc import OidcError, identity_from_claims
from nbb.core.security import hash_password
from nbb.main import build_container, create_app
from nbb.models import User, UserMfa, UserRole, UserSource

OWNER_URL = os.environ.get("NBB_TEST_OWNER_URL", "postgresql+psycopg://nbb_owner:owner@localhost:5432/nbb_test")
APP_URL = os.environ.get("NBB_TEST_APP_URL", "postgresql+psycopg://nbb_app:app@localhost:5432/nbb_test")
REDIS_URL = os.environ.get("NBB_TEST_REDIS_URL", "redis://localhost:6379/15")
BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))

KEY_A = "a" * 48
KEY_B = "b" * 48
DATA_KEY = generate_key()
STRONG_PASSWORD = "Faturamento#2026"
FRONT = "http://front.test"
DOMAIN = "empresa.test"

PROVIDERS = {
    # Google da empresa: domínio liberado e auto-cadastro (entra sem perfil).
    "google": {"name": "Google", "issuer": "https://accounts.google.com", "client_id": "g", "client_secret": "g",
               "allowed_domains": [DOMAIN], "auto_provision": True},
    # Microsoft de qualquer domínio: só entra quem o admin pré-cadastrou.
    "microsoft": {"name": "Microsoft", "issuer": "https://login.microsoftonline.com/common/v2.0",
                  "client_id": "m", "client_secret": "m"},
    # Provedor corporativo cujo MFA (amr) é aceito no lugar do TOTP.
    "corporativo": {"name": "Login corporativo", "issuer": "https://sso.empresa.test", "client_id": "c",
                    "client_secret": "c", "allowed_domains": [DOMAIN], "trust_idp_mfa": True},
}


# Isola os testes do ambiente do desenvolvedor: o pydantic-settings mescla dicionários
# vindos do .env/variáveis NBB_* com os passados aqui, o que mudaria os provedores de teste.
for _var in [v for v in os.environ if v.startswith("NBB_") and not v.startswith("NBB_TEST_")]:
    del os.environ[_var]


def make_settings(**overrides) -> Settings:
    base = dict(
        database_url=APP_URL, database_owner_url=OWNER_URL, redis_url=REDIS_URL,
        jwt_keys={"k1": KEY_A}, jwt_active_kid="k1", cookie_secure=False,
        frontend_url=FRONT, oidc_providers=PROVIDERS, data_encryption_keys=[DATA_KEY],
    )
    base.update(overrides)
    return Settings(_env_file=None, **base)


@pytest.fixture(scope="session", autouse=True)
def database():
    owner = create_engine(OWNER_URL)
    with owner.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    owner.dispose()
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "migrations"))
    cfg.attributes["url"] = OWNER_URL
    command.upgrade(cfg, "head")
    os.environ["NBB_DATABASE_URL"] = APP_URL
    dbmod.get_settings.cache_clear()
    dbmod.reset_engine()
    yield


@pytest.fixture(autouse=True)
def clean_redis():
    redis.Redis.from_url(REDIS_URL).flushdb()


class FakeOidcClient:
    """Provedor de identidade de mentira. O `code` traz a identidade: 'sub|email|verificado|amr'."""

    def __init__(self, provider_id: str, config):
        self.provider_id = provider_id
        self.config = config

    def authorization_url(self, state, nonce, code_challenge, redirect_uri):
        assert redirect_uri.endswith(f"/api/v1/auth/oidc/{self.provider_id}/callback")
        return f"https://idp.test/{self.provider_id}/authorize?state={state}"

    def exchange(self, code, code_verifier, nonce, redirect_uri):
        if code.startswith("bad"):
            raise OidcError("código inválido")
        sub, email, verified, amr = code.split("|")
        claims = {"sub": sub, "email": email or None, "email_verified": verified == "1",
                  "name": "Pessoa SSO", "amr": [amr] if amr else []}
        return identity_from_claims(self.provider_id, self.config, claims)


def FakeOidc(settings=None):  # noqa: N802 - fábrica com cara de classe, usada nos testes
    s = settings or make_settings()
    return {pid: FakeOidcClient(pid, cfg) for pid, cfg in s.oidc_providers.items()}


@pytest.fixture
def mailer():
    return OutboxMailer()


@pytest.fixture
def settings():
    return make_settings()


@pytest.fixture
def app(settings, mailer):
    return create_app(build_container(settings, oidc=FakeOidc(settings), mailer=mailer))


class Api:
    """TestClient que envia o cabeçalho CSRF automaticamente, como o frontend."""

    def __init__(self, app):
        self.client = TestClient(app, base_url="http://testserver")

    def _headers(self, headers):
        h = dict(headers or {})
        csrf = self.client.cookies.get(CSRF_COOKIE)
        if csrf:
            h.setdefault(CSRF_HEADER, csrf)
        return h

    def get(self, url, **kw):
        return self.client.get(url, **kw)

    def post(self, url, headers=None, **kw):
        return self.client.post(url, headers=self._headers(headers), **kw)

    def put(self, url, headers=None, **kw):
        return self.client.put(url, headers=self._headers(headers), **kw)

    @property
    def cookies(self):
        return self.client.cookies


@pytest.fixture
def new_api(app):
    def factory():
        return Api(app)
    return factory


def unique(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def create_user(login: str | None = None, *, roles=(), source=UserSource.SSO,
                password: str | None = None, email: str | None = None) -> User:
    db = dbmod.new_session()
    set_actor(db, Actor(user_id=None, login="test-setup"))
    login = login or unique("u")
    user = User(
        login=login, name="Pessoa Teste", source=source,
        email=(email or f"{login}@{DOMAIN}").lower(),
        password_hash=hash_password(password) if password else None,
    )
    db.add(user)
    db.flush()
    for r in roles:
        db.add(UserRole(user_id=user.id, role_code=r))
    db.commit()
    db.close()
    return user


def sso_login(api: Api, email: str, *, provider: str = "google", sub: str | None = None,
              verified: bool = True, amr: str = ""):
    """Faz o vaivém completo com o provedor e devolve a resposta do callback (302 para o frontend)."""
    start = api.get(f"/api/v1/auth/oidc/{provider}/login", follow_redirects=False)
    assert start.status_code == 302, start.text
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    code = f"{sub or 'sub-' + email}|{email}|{'1' if verified else '0'}|{amr}"
    return api.get(f"/api/v1/auth/oidc/{provider}/callback",
                   params={"code": code, "state": state}, follow_redirects=False)


def landing(resp) -> str:
    """Para onde o callback mandou o navegador: '/', '/login/verificacao' ou '/login?erro=...'."""
    assert resp.status_code == 302, resp.text
    loc = resp.headers["location"]
    assert loc.startswith(FRONT), loc
    return loc[len(FRONT):]


def enroll_totp(user: User) -> str:
    """Ativa o autenticador direto no banco (atalho para testes) e devolve o segredo."""
    secret = totp.new_secret()
    db = dbmod.new_session()
    set_actor(db, Actor(user_id=None, login="test-setup"))
    db.add(UserMfa(user_id=user.id, totp_secret_enc=DataCipher([DATA_KEY]).encrypt(secret),
                   confirmed_at=datetime.now(UTC)))
    db.commit()
    db.close()
    return secret


def code_for(secret: str, offset: int = 0) -> str:
    return totp.code_at(secret, totp.current_step() + offset)


@pytest.fixture
def login_as(new_api):
    """Cria um usuário SSO com os perfis dados e devolve um cliente logado.

    mfa=True: o usuário tem autenticador e o login passa pelas duas etapas.
    O segredo TOTP fica em `user.totp_secret`.
    """
    def factory(*roles, mfa=True, login=None):
        user = create_user(login or unique("u"), roles=roles)
        api = new_api()
        user.totp_secret = enroll_totp(user) if mfa else None
        where = landing(sso_login(api, user.email))
        if mfa:
            assert where == "/login/verificacao", where
            user.totp_used_code = code_for(user.totp_secret)
            r = api.post("/api/v1/auth/mfa/verify", json={"code": user.totp_used_code})
            assert r.status_code == 200 and r.json()["status"] == "authenticated", r.text
        else:
            assert where == "/", where
        return api, user
    return factory


def owner_engine():
    return create_engine(OWNER_URL)


def app_engine():
    return create_engine(APP_URL)


_open_sessions = []


def track(session):
    """Sessões abertas pelos testes são fechadas ao fim de cada teste."""
    _open_sessions.append(session)
    return session


@pytest.fixture(autouse=True)
def close_test_sessions():
    yield
    while _open_sessions:
        s = _open_sessions.pop()
        s.rollback()
        s.close()
