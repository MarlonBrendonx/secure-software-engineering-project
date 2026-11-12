"""Configuração por variáveis de ambiente.

Segredos (`JWT_SECRET`, senha e OTP do mock) não têm valor padrão: em produção viriam do
cofre corporativo. A aplicação não sobe sem eles.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    REDIS_URL: str = "redis://localhost:6379/0"

    # Token de sessão (HS256 no protótipo; a etapa 3 prevê chave assimétrica com cofre).
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "psp-prototype"
    JWT_AUDIENCE: str = "psp-api"
    # Token de acesso curto: se for roubado, vale por pouco tempo.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 8 * 60

    # Login mock: substitui o SSO. Não use em ambiente real.
    MOCK_LOGIN_PASSWORD: str
    MOCK_OTP_CODE: str

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "strict"
    AUTH_COOKIE_DOMAIN: str | None = None

    RATE_LIMIT_ENABLED: bool = True
    SEED_ON_STARTUP: bool = True

    @field_validator("JWT_SECRET")
    @classmethod
    def _secret_not_weak(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET deve ter ao menos 32 caracteres")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
