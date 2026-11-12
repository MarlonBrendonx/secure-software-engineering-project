"""Porta de persistência de regras de serviço."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.entities.service_rule import ServiceRule


class ServiceRuleGateway(Protocol):
    async def get_by_uuid(self, uuid: UUID) -> ServiceRule | None: ...

    async def list_by_clients(self, client_uuids: list[UUID]) -> list[ServiceRule]: ...

    async def get_names_by_uuids(self, uuids: set[UUID]) -> dict[UUID, str]: ...

    async def list_by_client(
        self,
        client_uuid: UUID,
        offset: int,
        limit: int,
        *,
        program_name: str | None = None,
        service_name: str | None = None,
    ) -> tuple[list[ServiceRule], int]:
        """Regras de um cliente em ordem de código, com filtro por nome de serviço e programa."""
        ...

    async def create(self, rule: ServiceRule) -> ServiceRule:
        """Atribui o próximo `code` e grava. Levanta `ConflictError` se já existir regra do
        mesmo cliente com o mesmo nome e o mesmo conjunto de programas."""
        ...

    async def update(self, rule: ServiceRule, *, expected_version: int) -> ServiceRule:
        """Grava só se a versão persistida ainda for `expected_version` (bloqueio otimista).

        Levanta `ConflictError` na corrida de versão e na duplicidade de nome + programas.
        """
        ...

    async def delete(self, rule: ServiceRule) -> None: ...

    async def has_billing_items(self, rule: ServiceRule) -> bool:
        """Indica se a regra já tem algum lançamento, em qualquer período."""
        ...
