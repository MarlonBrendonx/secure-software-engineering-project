"""Usuário e escopo de acesso (cliente × período) — base da autorização por recurso."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from src.domain.value_objects.user_role import UserRole

ALL = "*"


@dataclass(frozen=True)
class UserScope:
    """Clientes e períodos (`AAAA-MM`) que o usuário pode alcançar.

    O padrão é vazio: sem escopo registrado, nada é liberado (negar por padrão).
    """

    clients: frozenset[str] = field(default_factory=frozenset)
    periods: frozenset[str] = field(default_factory=frozenset)

    @property
    def all_clients(self) -> bool:
        return ALL in self.clients

    @property
    def all_periods(self) -> bool:
        return ALL in self.periods

    def allows_client(self, client_uuid: UUID) -> bool:
        return self.all_clients or str(client_uuid) in self.clients

    def allows_period(self, year: int, month: int) -> bool:
        return self.all_periods or f"{year}-{month:02d}" in self.periods


@dataclass
class User:
    username: str
    role: UserRole
    display_name: str
    email: str
    scope: UserScope = field(default_factory=UserScope)
