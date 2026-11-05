"""Autorização por recurso na camada de casos de uso (RS03 / decisão D02).

O guard de perfil fica na rota; a conferência sobre o recurso fica aqui, para qualquer
endpoint novo que reutilize um caso de uso herdar a checagem.
"""

from __future__ import annotations

from uuid import UUID

from src.application.actor import Actor
from src.application.security_monitor import SecurityMonitor
from src.domain.entities.user import UserScope
from src.domain.exceptions import NotFoundError
from src.domain.ports.gateways.security_gateway import UserGateway
from src.domain.services.access_policy import AccessPolicy


class ResourceAccessGuard:
    def __init__(self, users: UserGateway, monitor: SecurityMonitor) -> None:
        self._users = users
        self._monitor = monitor

    async def scope_of(self, actor: Actor) -> UserScope:
        return await self._users.get_scope(actor.username)

    async def allowed_clients(self, actor: Actor) -> frozenset[str] | None:
        """Filtro de clientes para listagens; `None` significa sem restrição."""
        scope = await self.scope_of(actor)
        return None if scope.all_clients else scope.clients

    async def ensure_client(
        self,
        actor: Actor,
        client_uuid: UUID,
        *,
        resource: str,
        resource_id: UUID | str,
        message: str,
        operation: str,
    ) -> None:
        """Como `ensure`, para recurso sem período (cadastros: regra de serviço, programa).

        Não inventa ano e mês: só o escopo de clientes vale. Negar responde 404.
        """
        if (await self.scope_of(actor)).allows_client(client_uuid):
            return
        await self._monitor.access_denied(
            actor.username,
            resource=resource,
            resource_id=str(resource_id),
            operation=operation,
        )
        raise NotFoundError(message)

    async def ensure(
        self,
        actor: Actor,
        client_uuid: UUID,
        year: int,
        month: int,
        *,
        resource: str,
        resource_id: UUID | str,
        message: str,
        operation: str,
    ) -> None:
        """Libera ou levanta `NotFoundError`, a mesma resposta de um id inexistente.

        Assim ninguém descobre se um registro de outro cliente existe (IDOR).
        """
        policy = AccessPolicy(await self.scope_of(actor))
        if policy.can_access(client_uuid, year, month):
            return
        await self._monitor.access_denied(
            actor.username,
            resource=resource,
            resource_id=str(resource_id),
            operation=operation,
        )
        raise NotFoundError(message)
