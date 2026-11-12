"""Schemas de entrada e saída do faturamento PSP."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.domain.value_objects.billing_status import BillingStatus, HistoryAction

_VALID_STATUSES = frozenset(s for s in BillingStatus if s != BillingStatus.NO_ENTRY)
_MIN_YEAR = 2026


def _check_status(value: str) -> str:
    if value not in _VALID_STATUSES:
        raise ValueError(f"Status deve ser um de: {', '.join(sorted(_VALID_STATUSES))}")
    return value


# ── Entrada ──────────────────────────────────────────────────────────


class BillingItemCreate(BaseModel):
    client_uuid: UUID
    reference_year: int = Field(..., ge=_MIN_YEAR)
    reference_month: int = Field(..., ge=1, le=12)
    service_rule_uuid: UUID
    quantity: Decimal = Field(default=Decimal("0"), ge=0)
    unit_value: Decimal = Field(default=Decimal("0"), ge=0)
    total_value: Decimal = Field(default=Decimal("0"), ge=0)
    base_value: Decimal | None = Field(default=None, ge=0)
    po_number: str | None = Field(default=None, max_length=100)
    invoice_description: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    billing_month: int = Field(..., ge=1, le=12)
    billing_year: int = Field(..., ge=_MIN_YEAR)
    competence_month: int | None = Field(default=None, ge=1, le=12)
    competence_year: int | None = Field(default=None, ge=_MIN_YEAR)


class BillingItemUpdate(BaseModel):
    quantity: Decimal | None = Field(default=None, ge=0)
    unit_value: Decimal | None = Field(default=None, ge=0)
    total_value: Decimal | None = Field(default=None, ge=0)
    base_value: Decimal | None = Field(default=None, ge=0)
    po_number: str | None = Field(default=None, max_length=100)
    invoice_description: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    billing_month: int | None = Field(default=None, ge=1, le=12)
    billing_year: int | None = Field(default=None, ge=_MIN_YEAR)
    competence_month: int | None = Field(default=None, ge=1, le=12)
    competence_year: int | None = Field(default=None, ge=_MIN_YEAR)
    version: int = Field(..., ge=1, description="Versão atual, para o bloqueio otimista")


class BillingStatusUpdate(BaseModel):
    new_status: str = Field(..., max_length=30)
    rejection_reason: str | None = None

    @field_validator("new_status")
    @classmethod
    def _valid_status(cls, v: str) -> str:
        return _check_status(v)


class BillingBatchStatusUpdate(BaseModel):
    item_uuids: list[UUID] = Field(..., min_length=1, max_length=200)
    new_status: str = Field(..., max_length=30)
    rejection_reason: str | None = None

    @field_validator("new_status")
    @classmethod
    def _valid_status(cls, v: str) -> str:
        return _check_status(v)


class BillingItemReplicateRequest(BaseModel):
    client_uuid: UUID
    reference_year: int = Field(..., ge=_MIN_YEAR)
    reference_month: int = Field(..., ge=1, le=12)
    service_rule_uuid: UUID
    quantity: Decimal = Field(default=Decimal("0"), ge=0)
    unit_value: Decimal = Field(default=Decimal("0"), ge=0)
    total_value: Decimal = Field(default=Decimal("0"), ge=0)
    base_value: Decimal | None = Field(default=None, ge=0)
    po_number: str | None = Field(default=None, max_length=100)
    invoice_description: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    billing_month: int = Field(..., ge=1, le=12)
    billing_year: int = Field(..., ge=_MIN_YEAR)
    competence_month: int | None = Field(default=None, ge=1, le=12)
    competence_year: int | None = Field(default=None, ge=_MIN_YEAR)
    subsequent_months: int = Field(..., ge=1, le=12)


# ── Saída ────────────────────────────────────────────────────────────


class ProgramInfo(BaseModel):
    uuid: UUID
    name: str


class BillingItemResponse(BaseModel):
    uuid: UUID
    billing_uuid: UUID
    service_rule_uuid: UUID
    service_rule_name: str | None = None
    programs: list[ProgramInfo] = Field(default_factory=list)
    quantity: Decimal
    unit_value: Decimal
    total_value: Decimal
    base_value: Decimal | None = None
    po_number: str | None = None
    invoice_description: str | None = None
    notes: str | None = None
    billing_month: int | None = None
    billing_year: int | None = None
    competence_month: int | None = None
    competence_year: int | None = None
    rule_type: str | None = None
    status: str = BillingStatus.NEW
    rejection_reason: str | None = None
    requires_client_approval: bool = False
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FieldChange(BaseModel):
    field: str
    old: str | None = None
    new: str | None = None


class ChangeDetail(BaseModel):
    item_uuid: UUID | None = None
    item_label: str | None = None
    fields: list[FieldChange] = Field(default_factory=list)


class BillingHistoryResponse(BaseModel):
    uuid: UUID
    action: str = HistoryAction.STATUS_CHANGE
    previous_status: str | None = None
    new_status: str
    notes: str | None = None
    changes: ChangeDetail | None = None
    changed_by: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingItemHistoryResponse(BillingHistoryResponse):
    billing_item_uuid: UUID
