"""Consultas de apoio ao cadastro: clientes e programas, sempre dentro do escopo de quem pede."""

from __future__ import annotations

from uuid import UUID

from src.application.access_guard import ResourceAccessGuard
from src.application.actor import Actor
from src.domain.entities.client import Client
from src.domain.entities.program import ClientProgram
from src.domain.exceptions import NotFoundError
from src.domain.ports.gateways.client_gateway import ClientGateway
from src.domain.ports.gateways.program_gateway import ProgramGateway


class ListRegistryClientsUseCase:
    def __init__(self, clients: ClientGateway, guard: ResourceAccessGuard) -> None:
        self._clients = clients
        self._guard = guard

    async def execute(
        self, actor: Actor, offset: int, limit: int, *, search: str | None = None
    ) -> tuple[list[Client], int]:
        # O filtro de escopo vai dentro da consulta: cliente de fora nem sai do Redis.
        allowed = await self._guard.allowed_clients(actor)
        return await self._clients.search_active(offset, limit, name=search, allowed=allowed)


class ListClientProgramsUseCase:
    def __init__(
        self, clients: ClientGateway, programs: ProgramGateway, guard: ResourceAccessGuard
    ) -> None:
        self._clients = clients
        self._programs = programs
        self._guard = guard

    async def execute(self, actor: Actor, client_uuid: UUID) -> list[ClientProgram]:
        await self._guard.ensure_client(
            actor,
            client_uuid,
            resource="cliente",
            resource_id=client_uuid,
            message="Cliente não encontrado",
            operation="listar_programas",
        )
        if await self._clients.get_by_uuid(client_uuid) is None:
            raise NotFoundError("Cliente não encontrado")
        return await self._programs.list_by_client(client_uuid)
