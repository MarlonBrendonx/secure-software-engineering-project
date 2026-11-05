"""Política central de acesso por recurso (RS03 / decisão D02).

A regra mora em um único lugar para nenhuma rota ou caso de uso reescrevê-la.
Na dúvida, nega: só libera quando cliente E período estão dentro do escopo.
"""

from __future__ import annotations

from uuid import UUID

from src.domain.entities.user import UserScope


class AccessPolicy:
    def __init__(self, scope: UserScope) -> None:
        self._scope = scope

    def can_access(self, client_uuid: UUID, year: int, month: int) -> bool:
        return self._scope.allows_client(client_uuid) and self._scope.allows_period(year, month)
