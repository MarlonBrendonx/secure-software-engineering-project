"""Configuração da aplicação, lida de variáveis de ambiente com prefixo NBB_.

Nenhum segredo tem valor padrão utilizável em produção: as chaves JWT
precisam vir do ambiente ou de um cofre (Vault, Secrets Manager etc.).
"""
from functools import lru_cache

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OidcProviderConfig(BaseModel):
    """Um provedor de login social/corporativo (Google, Microsoft, Keycloak...)."""

    name: str                                   # rótulo exibido no botão de login
    issuer: str                                 # ex.: https://accounts.google.com
    client_id: str
    client_secret: str
    scopes: str = "openid email profile"
    # Domínios de e-mail aceitos (ex.: ["empresa.com.br"]). Vazio = qualquer domínio,
    # mas então só entra quem foi pré-cadastrado pelo administrador.
    allowed_domains: list[str] = Field(default_factory=list)
    # Cria automaticamente, sem perfil, quem vier de um domínio permitido.
    auto_provision: bool = False
    # Vincula ao usuário pré-cadastrado com o mesmo e-mail (só e-mail verificado).
    link_by_email: bool = True
    # Exige o claim email_verified = true. Desligue apenas para provedores que
    # não o enviam e cujo e-mail é controlado pela empresa (tenant único).
    require_email_verified: bool = True
    # Aceita o MFA feito no provedor (claim amr/acr) no lugar do código TOTP.
    trust_idp_mfa: bool = False
    mfa_amr_values: list[str] = Field(default_factory=lambda: ["mfa", "otp", "hwk", "swk"])

    @field_validator("allowed_domains")
    @classmethod
    def _lower(cls, v: list[str]) -> list[str]:
        return [d.strip().lower().lstrip("@") for d in v if d.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NBB_", env_file=".env", extra="ignore")

    environment: str = "development"

    # Banco principal. A aplicação conecta com um usuário SEM permissão de
    # UPDATE/DELETE nas tabelas imutáveis; as migrations usam o usuário dono.
    database_url: str = "postgresql+psycopg://nbb_app:app@localhost:5432/nbb"
    database_owner_url: str = "postgresql+psycopg://nbb_owner:owner@localhost:5432/nbb"
    database_app_role: str = "nbb_app"

    redis_url: str = "redis://localhost:6379/0"

    # --- Sessão / JWT -----------------------------------------------------
    # Mapa kid -> segredo (JSON). A chave ativa assina; as demais só validam,
    # o que permite rotação sem derrubar quem está logado.
    jwt_keys: dict[str, str] = Field(default_factory=dict)
    jwt_active_kid: str = ""
    jwt_issuer: str = "network-billing"
    access_token_ttl_seconds: int = 900
    refresh_idle_minutes: int = 30
    refresh_absolute_hours: int = 10
    cookie_secure: bool = True
    cookie_domain: str | None = None

    # --- Rate limit de login ---------------------------------------------
    login_rate_limit: int = 10
    login_rate_window_seconds: int = 60
    # Proxies confiáveis cujo X-Forwarded-For é aceito para obter o IP real.
    trusted_proxies: list[str] = Field(default_factory=list)

    # --- SSO (OIDC) ---------------------------------------------------------
    # Mapa id -> provedor. Ex.: {"google": {...}, "microsoft": {...}, "corporativo": {...}}.
    # Ver README para os modelos de Google e Microsoft.
    oidc_providers: dict[str, OidcProviderConfig] = Field(default_factory=dict)
    # URL pública da API, usada para montar o redirect_uri de cada provedor:
    # {public_base_url}/api/v1/auth/oidc/{provedor}/callback
    public_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    # --- 2FA (TOTP) ---------------------------------------------------------
    # Chaves Fernet que cifram os segredos TOTP no banco. A primeira cifra;
    # todas decifram (rotação). Gere com `nbb generate-data-key`.
    data_encryption_keys: list[str] = Field(default_factory=list)
    totp_issuer: str = "Network Billing"
    mfa_challenge_ttl_seconds: int = 300
    mfa_max_attempts: int = 5
    recovery_codes_count: int = 10

    # --- Contas locais ----------------------------------------------------
    password_min_length: int = 12
    password_reset_ttl_minutes: int = 30

    @field_validator("data_encryption_keys")
    @classmethod
    def _fernet_keys(cls, keys: list[str]) -> list[str]:
        import base64
        import binascii
        for i, k in enumerate(keys, 1):
            try:
                ok = len(base64.urlsafe_b64decode(k.encode())) == 32
            except (binascii.Error, ValueError):
                ok = False
            if not ok:
                hint = (" Parece o texto de exemplo do .env.example." if "cole-aqui" in k else
                        " Atenção: `nbb generate-key` é a chave do JWT; aqui vai a saída de `nbb generate-data-key`.")
                raise ValueError(
                    f"NBB_DATA_ENCRYPTION_KEYS: a chave nº {i} não é uma chave válida (esperado 44 caracteres "
                    f"terminando em '=', gerada por `nbb generate-data-key`).{hint} "
                    'Formato no .env: NBB_DATA_ENCRYPTION_KEYS=["a-chave-gerada"]')
        return keys

    @field_validator("jwt_active_kid")
    @classmethod
    def _kid_present(cls, v: str, info):
        keys = info.data.get("jwt_keys") or {}
        if keys and v not in keys:
            raise ValueError("NBB_JWT_ACTIVE_KID deve existir em NBB_JWT_KEYS")
        return v

    def validate_for_runtime(self) -> None:
        if not self.data_encryption_keys:
            raise RuntimeError("Configure NBB_DATA_ENCRYPTION_KEYS (cifra os segredos do 2FA).")
        if not self.jwt_keys or not self.jwt_active_kid:
            raise RuntimeError("Configure NBB_JWT_KEYS e NBB_JWT_ACTIVE_KID (segredo fora do código).")
        for kid, secret in self.jwt_keys.items():
            if len(secret.encode()) < 32:
                raise RuntimeError(f"Chave JWT '{kid}' curta demais (mínimo 32 bytes).")


@lru_cache
def get_settings() -> Settings:
    return Settings()
