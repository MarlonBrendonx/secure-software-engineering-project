"""Porta de persistência de lançamentos (BillingItem)."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from src.domain.entities.audit import AuditEvent
from src.domain.entities.billing import BillingItem, BillingItemHistory


class BillingItemGateway(Protocol):
    async def get_by_uuid(self, uuid: UUID) -> BillingItem | None: ...

    async def get_by_uuids(self, uuids: list[UUID]) -> list[BillingItem]: ...

    async def list_by_billing(self, billing_uuid: UUID) -> list[BillingItem]: ...

    async def create(
        self,
        entity: BillingItem,
        *,
        history: BillingItemHistory | None = None,
        audit: AuditEvent | None = None,
    ) -> BillingItem:
        """Grava o item e, na mesma transação, a timeline e o evento de auditoria (RS05)."""
        ...

    async def update(
        self,
        entity: BillingItem,
        data: dict[str, object],
        *,
        expected_version: int,
        history: BillingItemHistory | None = None,
        audit: AuditEvent | None = None,
    ) -> BillingItem:
        """Grava só se a versão persistida ainda for `expected_version` (bloqueio otimista).

        Levanta `ConflictError` caso outra gravação tenha chegado antes. A timeline é
        e a auditoria são gravadas na mesma transação, para não existir mudança sem rastro.
        """
        ...

    async def update_many(
        self,
        updates: list[tuple[BillingItem, dict[str, object], BillingItemHistory | None]],
        *,
        audits: list[AuditEvent] | None = None,
    ) -> list[BillingItem]:
        """Grava todos os itens (com timelines e auditoria) ou nenhum (RF-PSP-36 e RS05)."""
        ...

    async def delete(
        self,
        entity: BillingItem,
        *,
        history: BillingItemHistory | None = None,
        audit: AuditEvent | None = None,
    ) -> None: ...

    async def get_average_by_service(
        self, client_uuid: UUID, year: int, month: int, n_months: int = 3
    ) -> dict[UUID, Decimal]: ...

    async def get_history(
        self, billing_item_uuid: UUID, *, status: str | None = None
    ) -> list[BillingItemHistory]: ...
