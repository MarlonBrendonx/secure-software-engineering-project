"""Casos de uso de leitura de billing (todos filtrados pelo escopo do usuário)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from src.application.access_guard import ResourceAccessGuard
from src.application.actor import Actor
from src.application.use_cases.billing.shared import (
    build_service_row,
    enrich_item,
    load_item_for_actor,
    require_client,
)
from src.domain.entities.audit import AuditEvent
from src.domain.entities.billing import BillingHistory, BillingItem, BillingItemHistory
from src.domain.exceptions import NotFoundError
from src.domain.ports.gateways.billing_gateway import BillingGateway
from src.domain.ports.gateways.billing_item_gateway import BillingItemGateway
from src.domain.ports.gateways.client_gateway import ClientGateway
from src.domain.ports.gateways.security_gateway import AuditLogGateway
from src.domain.ports.gateways.service_rule_gateway import ServiceRuleGateway

ZERO = Decimal("0")


def _aggregate_total(services: list[dict[str, Any]]) -> Decimal:
    """Soma o total de cada faturamento uma única vez, mesmo com vários lançamentos nele."""
    seen: set[UUID] = set()
    total = ZERO
    for s in services:
        billing_uuid = s["billing_uuid"]
        if billing_uuid and billing_uuid not in seen:
            seen.add(billing_uuid)
            total += s["billing_total_value"] or ZERO
    return total


class ListBillingsByPeriodUseCase:
    def __init__(
        self,
        billing_gateway: BillingGateway,
        client_gateway: ClientGateway,
        guard: ResourceAccessGuard,
        audit: AuditLogGateway,
    ) -> None:
        self._billings = billing_gateway
        self._clients = client_gateway
        self._guard = guard
        self._audit = audit

    async def execute(
        self,
        actor: Actor,
        year: int,
        month: int,
        offset: int = 0,
        limit: int = 20,
        *,
        client_name: str | None = None,
    ) -> tuple[list[dict[str, Any]], int, list[dict[str, Any]]]:
        scope = await self._guard.scope_of(actor)
        # O filtro de escopo vai dentro das consultas: dados de outros clientes e
        # períodos nem chegam à aplicação (seção 3.3 da prática 1).
        allowed = None if scope.all_clients else scope.clients
        if not scope.allows_period(year, month):
            await self._audit.record(
                AuditEvent(
                    "acesso_negado",
                    actor.username,
                    resource="periodo",
                    resource_id=f"{year}-{month:02d}",
                    detail="listar_lancamentos",
                )
            )
            allowed = frozenset()

        clients, total = await self._clients.list_active(
            offset, limit, name=client_name, allowed=allowed
        )
        summary = await self._billings.get_status_summary(
            year, month, client_name=client_name, allowed=allowed
        )

        rows = await self._billings.list_services_with_items([c.uuid for c in clients], year, month)
        by_client: dict[UUID, list[dict[str, Any]]] = {}
        for rec in rows:
            by_client.setdefault(rec.client_uuid, []).append(build_service_row(rec))

        data = [
            {
                "client_uuid": c.uuid,
                "client_name": c.name,
                "total_value": _aggregate_total(by_client.get(c.uuid, [])),
                "services": by_client.get(c.uuid, []),
            }
            for c in clients
        ]
        return data, total, summary


class ListServicesWithItemsUseCase:
    def __init__(
        self,
        billing_gateway: BillingGateway,
        client_gateway: ClientGateway,
        guard: ResourceAccessGuard,
    ) -> None:
        self._billings = billing_gateway
        self._clients = client_gateway
        self._guard = guard

    async def execute(
        self, actor: Actor, client_uuid: UUID, year: int, month: int
    ) -> list[dict[str, Any]]:
        await self._guard.ensure(
            actor,
            client_uuid,
            year,
            month,
            resource="cliente",
            resource_id=client_uuid,
            message="Cliente não encontrado",
            operation="listar_servicos",
        )
        await require_client(self._clients, client_uuid)
        rows = await self._billings.list_services_with_items([client_uuid], year, month)
        return [build_service_row(r) for r in rows]


class GetBillingItemUseCase:
    """Consulta de um lançamento por id — a rota que TS01 e TS02 exercitam."""

    def __init__(
        self,
        billing_gateway: BillingGateway,
        item_gateway: BillingItemGateway,
        service_rule_gateway: ServiceRuleGateway,
        guard: ResourceAccessGuard,
    ) -> None:
        self._billings = billing_gateway
        self._items = item_gateway
        self._rules = service_rule_gateway
        self._guard = guard

    async def execute(self, actor: Actor, item_uuid: UUID) -> BillingItem:
        item, _ = await load_item_for_actor(
            self._items,
            self._billings,
            self._guard,
            actor,
            item_uuid,
            operation="consultar_lancamento",
        )
        return enrich_item(item, await self._rules.get_by_uuid(item.service_rule_uuid))


class GetBillingHistoryUseCase:
    def __init__(self, billing_gateway: BillingGateway, guard: ResourceAccessGuard) -> None:
        self._billings = billing_gateway
        self._guard = guard

    async def execute(self, actor: Actor, billing_uuid: UUID) -> list[BillingHistory]:
        message = "Faturamento não encontrado"
        billing = await self._billings.get_by_uuid(billing_uuid)
        if billing is None:
            raise NotFoundError(message)
        await self._guard.ensure(
            actor,
            billing.client_uuid,
            billing.reference_year,
            billing.reference_month,
            resource="faturamento",
            resource_id=billing_uuid,
            message=message,
            operation="consultar_historico",
        )
        return await self._billings.get_history(billing_uuid)


class GetItemHistoryUseCase:
    def __init__(
        self,
        billing_gateway: BillingGateway,
        item_gateway: BillingItemGateway,
        guard: ResourceAccessGuard,
    ) -> None:
        self._billings = billing_gateway
        self._items = item_gateway
        self._guard = guard

    async def execute(
        self, actor: Actor, item_uuid: UUID, *, status: str | None = None
    ) -> list[BillingItemHistory]:
        await load_item_for_actor(
            self._items,
            self._billings,
            self._guard,
            actor,
            item_uuid,
            operation="consultar_historico",
        )
        return await self._items.get_history(item_uuid, status=status)


class GetBillingAverageUseCase:
    def __init__(
        self,
        item_gateway: BillingItemGateway,
        client_gateway: ClientGateway,
        guard: ResourceAccessGuard,
    ) -> None:
        self._items = item_gateway
        self._clients = client_gateway
        self._guard = guard

    async def execute(
        self, actor: Actor, client_uuid: UUID, year: int, month: int
    ) -> dict[UUID, Decimal]:
        await self._guard.ensure(
            actor,
            client_uuid,
            year,
            month,
            resource="cliente",
            resource_id=client_uuid,
            message="Cliente não encontrado",
            operation="consultar_media",
        )
        await require_client(self._clients, client_uuid)
        return await self._items.get_average_by_service(client_uuid, year, month)
