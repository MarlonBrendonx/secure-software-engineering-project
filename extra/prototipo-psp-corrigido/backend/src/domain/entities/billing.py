"""Faturamento (Billing), lançamento (BillingItem) e máquina de estados."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from src.domain.entities.base import AggregateRoot, Entity, utcnow
from src.domain.exceptions import BusinessValidationError, ForbiddenError
from src.domain.value_objects.billing_status import BillingStatus, HistoryAction
from src.domain.value_objects.user_role import UserRole

_S = BillingStatus

# Única fonte de verdade das transições permitidas (RF-PSP-29).
# A volta para `New` é a transição "reabrir" (RS01/D01): é a única forma de mudar um
# lançamento já enviado para aprovação, e ele precisa ser enviado e aprovado de novo.
TRANSITIONS: dict[BillingStatus, list[BillingStatus]] = {
    _S.NEW: [_S.MANAGEMENT_APPROVAL],
    _S.MANAGEMENT_APPROVAL: [_S.REJECTED, _S.CLIENT_APPROVAL, _S.FINANCIAL_REVIEW, _S.NEW],
    _S.CLIENT_APPROVAL: [_S.REJECTED, _S.FINANCIAL_REVIEW, _S.NEW],
    _S.FINANCIAL_REVIEW: [_S.APPROVED, _S.NEW],
    _S.REJECTED: [_S.MANAGEMENT_APPROVAL],
}

# Estados de rascunho: os únicos em que o lançamento aceita alteração ou exclusão direta (RS01).
_DRAFT_STATUSES = frozenset({_S.NEW, _S.REJECTED})

# Transições que aprovam o lançamento em alguma etapa do fluxo (R18).
APPROVAL_TARGETS = frozenset({_S.CLIENT_APPROVAL, _S.FINANCIAL_REVIEW, _S.APPROVED})

# Segregação de funções por perfil: quem envia não é quem aprova (RF-PSP-30 e 31).
_SEND_ROLES = frozenset({UserRole.ADMIN, UserRole.ANALYST})
_APPROVE_ROLES = frozenset({UserRole.ADMIN, UserRole.MANAGER})


@dataclass
class BillingItem(Entity):
    billing_uuid: UUID
    service_rule_uuid: UUID
    quantity: Decimal = Decimal("0")
    unit_value: Decimal = Decimal("0")
    total_value: Decimal = Decimal("0")
    base_value: Decimal | None = None
    po_number: str | None = None
    invoice_description: str | None = None
    notes: str | None = None
    billing_month: int | None = None
    billing_year: int | None = None
    competence_month: int | None = None
    competence_year: int | None = None
    status: BillingStatus = BillingStatus.NEW
    rejection_reason: str | None = None
    # Campos de leitura, preenchidos na montagem da resposta (não persistidos).
    rule_type: str | None = None
    requires_client_approval: bool = False
    service_rule_name: str | None = None
    programs: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            self.status = BillingStatus(self.status)

    @property
    def is_editable(self) -> bool:
        return self.status in _DRAFT_STATUSES

    def assert_editable(self) -> None:
        # RS01: depois do envio para aprovação, nada muda por PATCH ou DELETE diretos.
        if not self.is_editable:
            raise BusinessValidationError(
                f"Lançamento com status '{self.status}' não pode ser alterado nem excluído. "
                "Reabra o lançamento (status 'New') para alterá-lo.",
            )

    def validate_transition(self, target: BillingStatus) -> None:
        if target not in TRANSITIONS.get(self.status, []):
            raise BusinessValidationError(
                f"Transição de '{self.status}' para '{target}' não é permitida",
            )

    @staticmethod
    def validate_rejection(target: BillingStatus, rejection_reason: str | None) -> None:
        if target == _S.REJECTED and not (rejection_reason and rejection_reason.strip()):
            raise BusinessValidationError("Motivo da reprovação é obrigatório ao reprovar")

    @staticmethod
    def check_role_for_status(target: BillingStatus, role: str | None) -> None:
        if target == _S.NEW and role not in _SEND_ROLES:
            raise ForbiddenError("Apenas admin ou analista pode reabrir lançamento")
        if target == _S.MANAGEMENT_APPROVAL and role not in _SEND_ROLES:
            raise ForbiddenError("Apenas admin ou analista pode enviar para aprovação da gestão")
        if target in (_S.CLIENT_APPROVAL, _S.FINANCIAL_REVIEW, _S.APPROVED) and (
            role not in _APPROVE_ROLES
        ):
            raise ForbiddenError("Apenas admin ou gestor pode aprovar faturamento")
        if target == _S.REJECTED and role not in _APPROVE_ROLES:
            raise ForbiddenError("Apenas admin ou gestor pode reprovar faturamento")


def item_authors(history: list[BillingItemHistory]) -> set[str]:
    """Quem criou, alterou ou enviou o lançamento para aprovação, segundo a timeline."""
    authors: set[str] = set()
    for entry in history:
        authored = entry.action in (HistoryAction.ITEM_CREATED, HistoryAction.ITEM_UPDATED) or (
            entry.action == HistoryAction.STATUS_CHANGE
            and entry.new_status == _S.MANAGEMENT_APPROVAL
        )
        if authored and entry.changed_by:
            authors.add(entry.changed_by)
    return authors


def ensure_segregation_of_duties(
    target: BillingStatus, approver: str, history: list[BillingItemHistory]
) -> None:
    """R18: quem criou, enviou ou alterou o lançamento não o aprova, nem sendo admin."""
    if target in APPROVAL_TARGETS and approver in item_authors(history):
        raise ForbiddenError("Quem criou, enviou ou alterou o lançamento não pode aprová-lo")


@dataclass
class BillingItemHistory:
    billing_item_uuid: UUID
    new_status: BillingStatus
    action: HistoryAction = HistoryAction.STATUS_CHANGE
    previous_status: BillingStatus | None = None
    notes: str | None = None
    changes: dict[str, object] | None = None
    changed_by: str | None = None
    uuid: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class BillingHistory:
    billing_uuid: UUID
    new_status: str
    action: str = HistoryAction.STATUS_CHANGE
    previous_status: str | None = None
    notes: str | None = None
    changes: dict[str, object] | None = None
    changed_by: str | None = None
    uuid: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class Billing(AggregateRoot):
    """Agregado por cliente × período de referência × regra de serviço."""

    client_uuid: UUID
    service_rule_uuid: UUID
    reference_year: int
    reference_month: int
    total_value: Decimal = Decimal("0")

    @property
    def period(self) -> str:
        return f"{self.reference_year}-{self.reference_month:02d}"
