"""DTOs de entrada dos casos de uso de billing."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from src.application.actor import Actor


@dataclass(frozen=True)
class CreateBillingItemCommand:
    actor: Actor
    client_uuid: UUID
    service_rule_uuid: UUID
    quantity: Decimal
    unit_value: Decimal
    total_value: Decimal
    reference_month: int
    reference_year: int
    base_value: Decimal | None = None
    po_number: str | None = None
    invoice_description: str | None = None
    notes: str | None = None
    billing_month: int | None = None
    billing_year: int | None = None
    competence_month: int | None = None
    competence_year: int | None = None


@dataclass(frozen=True)
class UpdateBillingItemCommand:
    actor: Actor
    item_uuid: UUID
    version: int
    quantity: Decimal | None = None
    unit_value: Decimal | None = None
    total_value: Decimal | None = None
    base_value: Decimal | None = None
    po_number: str | None = None
    invoice_description: str | None = None
    notes: str | None = None
    billing_month: int | None = None
    billing_year: int | None = None
    competence_month: int | None = None
    competence_year: int | None = None


@dataclass(frozen=True)
class DeleteBillingItemCommand:
    actor: Actor
    item_uuid: UUID


@dataclass(frozen=True)
class ChangeItemStatusCommand:
    actor: Actor
    new_status: str
    item_uuids: list[UUID] = field(default_factory=list)
    rejection_reason: str | None = None


@dataclass(frozen=True)
class ReplicateItemsCommand:
    actor: Actor
    client_uuid: UUID
    service_rule_uuid: UUID
    quantity: Decimal
    unit_value: Decimal
    total_value: Decimal
    reference_month: int
    reference_year: int
    subsequent_months: int
    base_value: Decimal | None = None
    po_number: str | None = None
    invoice_description: str | None = None
    notes: str | None = None
    billing_month: int | None = None
    billing_year: int | None = None
    competence_month: int | None = None
    competence_year: int | None = None
