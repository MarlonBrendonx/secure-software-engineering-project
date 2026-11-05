"""Portas de segurança: usuários, sessões, auditoria, contadores e alertas."""

from __future__ import annotations

from typing import Protocol

from src.domain.entities.audit import AuditEvent
from src.domain.entities.session import AuthSession
from src.domain.entities.user import User, UserScope


class UserGateway(Protocol):
    async def get_by_username(self, username: str) -> User | None: ...

    async def get_scope(self, username: str) -> UserScope:
        """Escopo do usuário. Usuário sem escopo registrado recebe escopo vazio."""
        ...


class SessionGateway(Protocol):
    async def create(self, session: AuthSession, ttl_seconds: int) -> None: ...

    async def get(self, sid: str) -> AuthSession | None:
        """Sessão ativa, ou `None` se inexistente, expirada ou revogada."""
        ...

    async def revoke(self, sid: str) -> None: ...


class AuditLogGateway(Protocol):
    async def record(self, event: AuditEvent) -> None: ...

    async def list_recent(self, limit: int = 50) -> list[AuditEvent]: ...


class CounterGateway(Protocol):
    async def increment(self, key: str, window_seconds: int) -> int:
        """Incrementa o contador e devolve o total dentro da janela deslizante simples."""
        ...


class AlertGateway(Protocol):
    async def fire(self, name: str, **context: object) -> None: ...
