"""Porta de persistência do agregado Billing."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from src.domain.entities.billing import Billing, BillingHistory, BillingItem
from src.domain.entities.service_rule import ServiceRule


@dataclass(frozen=True)
class ServiceRowRecord:
    """Linha da visão serviço × lançamento (equivale ao LEFT JOIN do relacional).

    Sem lançamento, `item` e `billing` vêm vazios e o status exibido é `NoEntry`.
    """

    client_uuid: UUID
    rule: ServiceRule
    item: BillingItem | None
    billing: Billing | None


class BillingGateway(Protocol):
    async def get_by_uuid(self, uuid: UUID) -> Billing | None: ...

    async def get_by_uuids(self, uuids: list[UUID]) -> list[Billing]: ...

    async def get_by_client_and_period(
        self, client_uuid: UUID, year: int, month: int, service_rule_uuid: UUID
    ) -> Billing | None: ...

    async def create(self, entity: Billing, *, history: BillingHistory | None = None) -> Billing:
        """Cria o faturamento. Levanta `ConflictError` se o trio cliente×período×regra já existe."""
        ...

    async def delete(self, entity: Billing) -> None: ...

    async def recalculate_total(self, billing: Billing) -> Billing: ...

    async def list_services_with_items(
        self, client_uuids: list[UUID], year: int, month: int
    ) -> list[ServiceRowRecord]: ...

    async def get_status_summary(
        self,
        year: int,
        month: int,
        *,
        client_name: str | None = None,
        allowed: frozenset[str] | None = None,
    ) -> list[dict[str, Any]]: ...

    async def get_history(self, billing_uuid: UUID) -> list[BillingHistory]: ...


ZERO = Decimal("0")
