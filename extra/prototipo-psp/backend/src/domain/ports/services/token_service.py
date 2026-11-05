"""Porta do emissor/validador de tokens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.domain.entities.session import TokenClaims


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int


class TokenService(Protocol):
    def issue(
        self,
        *,
        username: str,
        sid: str,
        amr: list[str],
        role: str,
        display_name: str,
        email: str,
    ) -> IssuedTokens: ...

    def decode_access(self, token: str) -> TokenClaims:
        """Valida assinatura, algoritmo, emissor, audience e prazo. Qualquer falha → 401."""
        ...

    def decode_refresh(self, token: str) -> TokenClaims: ...
