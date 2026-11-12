"""Value objects do faturamento PSP."""

from __future__ import annotations

from enum import StrEnum


class BillingStatus(StrEnum):
    NEW = "New"
    MANAGEMENT_APPROVAL = "ManagementApproval"
    CLIENT_APPROVAL = "ClientApproval"
    FINANCIAL_REVIEW = "FinancialReview"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    # Virtual: serviço sem lançamento no período. Nunca é persistido.
    NO_ENTRY = "NoEntry"


class HistoryAction(StrEnum):
    STATUS_CHANGE = "mudanca_status"
    ITEM_CREATED = "lancamento_criado"
    ITEM_UPDATED = "lancamento_atualizado"
    ITEM_DELETED = "lancamento_excluido"


class RuleType(StrEnum):
    FIXED_VALUE = "fixed_value"
    PERCENTAGE = "percentage"
    MULTIPLICATION = "multiplication"
    RANGE = "range"
    VARIABLE_VALUE = "variable_value"


class RangeType(StrEnum):
    FIXED_VALUE = "fixed_value"
    PER_UNIT_VALUE = "per_unit_value"


class EntityStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
