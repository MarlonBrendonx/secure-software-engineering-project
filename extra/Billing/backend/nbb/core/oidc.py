"""Clientes OIDC (Authorization Code + PKCE) para login via Google, Microsoft
ou o provedor corporativo. Um cliente por provedor configurado.

O cliente só autentica a pessoa no provedor e devolve uma identidade
verificada (assinatura, issuer, audience, nonce). Quem decide se essa
identidade pode entrar, e com qual usuário, é `nbb.services.sso`.
"""
import base64
import hashlib
import secrets
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode

import httpx
import jwt

from nbb.config import OidcProviderConfig

MS_TENANT_PLACEHOLDER = "{tenantid}"


@dataclass(frozen=True)
class OidcIdentity:
    provider: str
    subject: str            # identificador estável e único da pessoa no provedor
    email: str | None
    email_verified: bool
    name: str
    idp_mfa: bool           # o provedor declarou que houve segundo fator (amr/acr)


class OidcError(Exception):
    pass


class OidcClient(Protocol):
    provider_id: str
    config: OidcProviderConfig

    def authorization_url(self, state: str, nonce: str, code_challenge: str, redirect_uri: str) -> str: ...
    def exchange(self, code: str, code_verifier: str, nonce: str, redirect_uri: str) -> OidcIdentity: ...


def new_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def _as_bool(v) -> bool:
    return v is True or (isinstance(v, str) and v.lower() == "true")


def identity_from_claims(provider_id: str, cfg: OidcProviderConfig, claims: dict) -> OidcIdentity:
    sub = claims.get("sub")
    if not sub:
        raise OidcError("claim 'sub' ausente")
    email = claims.get("email")
    if not email and provider_id.startswith("microsoft"):
        # Contas Microsoft corporativas nem sempre trazem `email`.
        email = claims.get("preferred_username") if "@" in str(claims.get("preferred_username", "")) else None
    amr = claims.get("amr") or []
    if isinstance(amr, str):
        amr = [amr]
    # Na Microsoft (multi-tenant) `sub` é único por aplicação, e `tid` + `oid`
    # identifica a pessoa; prefixar com tid evita colisão entre tenants.
    if claims.get("tid"):
        sub = f"{claims['tid']}:{sub}"
    return OidcIdentity(
        provider=provider_id,
        subject=str(sub),
        email=email.strip().lower() if email else None,
        email_verified=_as_bool(claims.get("email_verified")),
        name=claims.get("name") or (email or str(sub)),
        idp_mfa=any(v in cfg.mfa_amr_values for v in amr),
    )


class HttpOidcClient:
    def __init__(self, provider_id: str, config: OidcProviderConfig):
        self.provider_id = provider_id
        self.config = config
        self._discovery: dict | None = None
        self._jwks: jwt.PyJWKClient | None = None

    def _meta(self) -> dict:
        if self._discovery is None:
            url = self.config.issuer.rstrip("/") + "/.well-known/openid-configuration"
            try:
                resp = httpx.get(url, timeout=5)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise OidcError(f"provedor {self.provider_id} indisponível") from exc
            self._discovery = resp.json()
            self._jwks = jwt.PyJWKClient(self._discovery["jwks_uri"], cache_keys=True)
        return self._discovery

    def authorization_url(self, state: str, nonce: str, code_challenge: str, redirect_uri: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": redirect_uri,
            "scope": self.config.scopes,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        return self._meta()["authorization_endpoint"] + "?" + urlencode(params)

    def _check_issuer(self, meta_issuer: str, claims: dict) -> None:
        expected = meta_issuer
        if MS_TENANT_PLACEHOLDER in expected:
            # Endpoint "common"/"organizations" da Microsoft: o issuer real traz o tenant.
            expected = expected.replace(MS_TENANT_PLACEHOLDER, str(claims.get("tid", "")))
        if claims.get("iss") != expected:
            raise OidcError("issuer inválido")

    def exchange(self, code: str, code_verifier: str, nonce: str, redirect_uri: str) -> OidcIdentity:
        meta = self._meta()
        try:
            resp = httpx.post(
                meta["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                },
                timeout=10,
            )
            resp.raise_for_status()
            id_token = resp.json()["id_token"]
            assert self._jwks is not None
            key = self._jwks.get_signing_key_from_jwt(id_token)
            claims = jwt.decode(
                id_token, key.key, algorithms=["RS256", "ES256", "PS256"],
                audience=self.config.client_id, options={"verify_iss": False, "require": ["exp", "iat", "sub"]},
            )
        except (httpx.HTTPError, jwt.PyJWTError, KeyError) as exc:
            raise OidcError(f"falha na troca do código: {exc}") from exc
        self._check_issuer(meta["issuer"], claims)
        if not secrets.compare_digest(str(claims.get("nonce", "")), nonce):
            raise OidcError("nonce inválido")
        return identity_from_claims(self.provider_id, self.config, claims)


def build_clients(providers: dict[str, OidcProviderConfig]) -> dict[str, OidcClient]:
    return {pid: HttpOidcClient(pid, cfg) for pid, cfg in providers.items()}
