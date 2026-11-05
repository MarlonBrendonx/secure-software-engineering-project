"""Porta de leitura de clientes."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.entities.client import Client


class ClientGateway(Protocol):
    async def get_by_uuid(self, uuid: UUID) -> Client | None: ...

    async def list_active(
        self,
        offset: int,
        limit: int,
        *,
        name: str | None = None,
        allowed: frozenset[str] | None = None,
    ) -> tuple[list[Client], int]:
        """Clientes ativos com regras, em ordem de nome.

        `allowed` restringe a consulta aos clientes do escopo do usuário (`None` = todos).
        O filtro é aplicado na própria consulta, para dados de outros clientes não chegarem
        à aplicação.
        """
        ...

    async def search_active(
        self,
        offset: int,
        limit: int,
        *,
        name: str | None = None,
        allowed: frozenset[str] | None = None,
    ) -> tuple[list[Client], int]:
        """Clientes ativos para o cadastro, em ordem de nome, com ou sem regras.

        Ao contrário de `list_active`, não esconde cliente sem regra: é por aqui que a
        primeira regra de um cliente novo é cadastrada.
        """
        ...

    async def get_names_by_uuids(self, uuids: set[UUID]) -> dict[UUID, str]: ...
