"""Cliente OIDC real (HttpOidcClient) contra um provedor OIDC local de teste.

Cobre o que o provedor falso dos outros testes não cobre: assinatura do
id_token (JWKS), audience, nonce, issuer e o issuer multi-tenant da Microsoft.
"""
import os
import socket
import threading
import time

import jwt
import pytest
import uvicorn
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Form

from nbb.config import OidcProviderConfig
from nbb.core.oidc import HttpOidcClient, OidcError

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ["NO_PROXY"] += ",127.0.0.1,localhost"

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
CLIENT_ID = "app-faturamento"
REDIRECT = "http://localhost:8000/api/v1/auth/oidc/x/callback"


class Idp:
    """Estado do provedor local: o teste define o issuer anunciado e os claims do próximo token."""
    issuer_template = ""
    claims: dict = {}
    sign_with = KEY


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORT = _free_port()
BASE = f"http://127.0.0.1:{PORT}"
idp_app = FastAPI()


@idp_app.get("/.well-known/openid-configuration")
def discovery():
    return {"issuer": Idp.issuer_template or BASE, "authorization_endpoint": f"{BASE}/authorize",
            "token_endpoint": f"{BASE}/token", "jwks_uri": f"{BASE}/jwks"}


@idp_app.get("/jwks")
def jwks():
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key(), as_dict=True)
    return {"keys": [{**jwk, "kid": "k1", "use": "sig", "alg": "RS256"}]}


@idp_app.post("/token")
def token(code: str = Form(), code_verifier: str = Form(), client_id: str = Form()):
    assert code == "codigo-ok" and code_verifier and client_id == CLIENT_ID
    now = int(time.time())
    claims = {"iss": BASE, "aud": CLIENT_ID, "iat": now, "exp": now + 300, **Idp.claims}
    return {"id_token": jwt.encode(claims, Idp.sign_with, algorithm="RS256", headers={"kid": "k1"}),
            "token_type": "Bearer"}


@pytest.fixture(scope="module", autouse=True)
def idp_server():
    server = uvicorn.Server(uvicorn.Config(idp_app, host="127.0.0.1", port=PORT, log_level="error"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    while not server.started:
        time.sleep(0.05)
    yield
    server.should_exit = True
    t.join(timeout=5)


@pytest.fixture(autouse=True)
def reset_idp():
    Idp.issuer_template, Idp.claims, Idp.sign_with = "", {}, KEY


def client(provider_id="google", **cfg) -> HttpOidcClient:
    return HttpOidcClient(provider_id, OidcProviderConfig(
        name="Teste", issuer=BASE, client_id=CLIENT_ID, client_secret="s", **cfg))


def exchange(c: HttpOidcClient, nonce="n-1"):
    return c.exchange("codigo-ok", "verificador", nonce, REDIRECT)


def test_authorization_url_uses_pkce_and_state():
    url = client().authorization_url("st", "n-1", "desafio", REDIRECT)
    assert url.startswith(f"{BASE}/authorize?")
    for part in ("code_challenge=desafio", "code_challenge_method=S256", "state=st", "nonce=n-1",
                 f"client_id={CLIENT_ID}", "response_type=code"):
        assert part in url


def test_valid_id_token_yields_identity():
    Idp.claims = {"sub": "1098", "nonce": "n-1", "email": "Ana@Empresa.com.br", "email_verified": True,
                  "name": "Ana", "amr": ["pwd", "mfa"]}
    ident = exchange(client())
    assert (ident.provider, ident.subject, ident.email, ident.email_verified) == (
        "google", "1098", "ana@empresa.com.br", True)
    assert ident.idp_mfa is True


def test_wrong_nonce_is_rejected():
    Idp.claims = {"sub": "1", "nonce": "outro", "email": "a@b.c", "email_verified": True}
    with pytest.raises(OidcError, match="nonce"):
        exchange(client())


def test_token_signed_with_unknown_key_is_rejected():
    Idp.claims = {"sub": "1", "nonce": "n-1"}
    Idp.sign_with = OTHER_KEY
    with pytest.raises(OidcError):
        exchange(client())


def test_token_for_another_application_is_rejected():
    Idp.claims = {"sub": "1", "nonce": "n-1", "aud": "outra-aplicacao"}
    with pytest.raises(OidcError):
        exchange(client())


def test_microsoft_multitenant_issuer():
    Idp.issuer_template = BASE + "/{tenantid}/v2.0"
    tenant = "72f988bf-86f1-41af-91ab-2d7cd011db47"
    Idp.claims = {"sub": "abc", "nonce": "n-1", "tid": tenant, "iss": f"{BASE}/{tenant}/v2.0",
                  "preferred_username": "joao@contoso.com"}
    ident = exchange(client("microsoft", require_email_verified=False))
    # Sem claim `email`, usa preferred_username; o sub é prefixado com o tenant.
    assert ident.email == "joao@contoso.com" and ident.subject == f"{tenant}:abc"
    assert ident.email_verified is False

    # Token emitido por outro tenant que não o declarado em `tid` é recusado.
    Idp.claims = {**Idp.claims, "iss": f"{BASE}/outro-tenant/v2.0"}
    with pytest.raises(OidcError, match="issuer"):
        exchange(client("microsoft"))
