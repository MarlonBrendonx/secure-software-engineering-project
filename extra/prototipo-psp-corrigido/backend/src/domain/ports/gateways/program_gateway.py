"""Porta de leitura do catálogo de programas dos clientes."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.entities.program import ClientProgram


class ProgramGateway(Protocol):
    async def get_by_uuid(self, uuid: UUID) -> ClientProgram | None: ...

    async def list_by_client(self, client_uuid: UUID) -> list[ClientProgram]:
        """Programas do cliente em ordem de nome."""
        ...
