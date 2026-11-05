"""Sessão no servidor e claims do token."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base import utcnow


@dataclass
class AuthSession:
    """Sessão registrada no servidor; é o que permite revogar um token já emitido."""

    sid: str
    username: str
    # Métodos de autenticação (RFC 8176). "mfa" só aparece após o segundo fator.
    amr: list[str]
    created_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class TokenClaims:
    sub: str
    sid: str
    amr: tuple[str, ...]
    exp: int
    jti: str
    token_type: str = "access"

    @property
    def mfa_completed(self) -> bool:
        return "mfa" in self.amr
