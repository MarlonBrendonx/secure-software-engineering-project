"""Helpers compartilhados entre os casos de uso de billing."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from src.application.access_guard import ResourceAccessGuard
from src.application.actor import Actor
from src.domain.entities.audit import AuditEvent
from src.domain.entities.billing import Billing, BillingHistory, BillingItem
from src.domain.entities.service_rule import ServiceRule
from src.domain.exceptions import BusinessValidationError, ConflictError, NotFoundError
from src.domain.ports.gateways.billing_gateway import BillingGateway, ServiceRowRecord
from src.domain.ports.gateways.billing_item_gateway import BillingItemGateway
from src.domain.ports.gateways.client_gateway import ClientGateway
from src.domain.ports.gateways.service_rule_gateway import ServiceRuleGateway
from src.domain.value_objects.billing_status import BillingStatus, EntityStatus, RuleType

_FIELD_LABELS: dict[str, str] = {
    "quantity": "quantidade",
    "unit_value": "valor_unitario",
    "total_value": "valor_total",
    "po_number": "numero_po",
    "invoice_description": "descricao_fatura",
    "billing_month": "mes_faturamento",
    "billing_year": "ano_faturamento",
    "competence_month": "mes_competencia",
    "competence_year": "ano_competencia",
    "notes": "observacoes",
}


# ── Timeline: diffs e snapshots ──────────────────────────────────────


def build_changes(
    item_uuid: UUID, item_label: str | None, fields: list[dict[str, str | None]]
) -> dict[str, object]:
    return {"item_uuid": str(item_uuid), "item_label": item_label, "fields": fields}


def diff_fields(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, str | None]]:
    fields: list[dict[str, str | None]] = []
    for key, new_val in new.items():
        old_val = old.get(key)
        if old_val != new_val:
            fields.append(
                {
                    "field": _FIELD_LABELS.get(key, key),
                    "old": str(old_val) if old_val is not None else None,
                    "new": str(new_val) if new_val is not None else None,
                }
            )
    return fields


def snapshot_fields(values: dict[str, Any], *, as_old: bool = False) -> list[dict[str, str | None]]:
    fields: list[dict[str, str | None]] = []
    for key, val in values.items():
        text = str(val) if val is not None else None
        fields.append(
            {
                "field": _FIELD_LABELS.get(key, key),
                "old": text if as_old else None,
                "new": None if as_old else text,
            }
        )
    return fields


# ── Cálculo e descrição ──────────────────────────────────────────────


def detect_value_divergences(
    sent_unit: Decimal, sent_total: Decimal, calc_unit: Decimal, calc_total: Decimal
) -> list[dict[str, str]]:
    """Avisa quando o servidor corrigiu o valor enviado pelo cliente (RF-PSP-20)."""
    warnings: list[dict[str, str]] = []
    if sent_unit and sent_unit != calc_unit:
        warnings.append(
            {
                "code": "VALUE_RECALCULATED",
                "message": (
                    f"Valor unitário recalculado: enviado {sent_unit}, calculado {calc_unit}"
                ),
                "field": "unit_value",
            }
        )
    if sent_total and sent_total != calc_total:
        warnings.append(
            {
                "code": "VALUE_RECALCULATED",
                "message": f"Valor total recalculado: enviado {sent_total}, calculado {calc_total}",
                "field": "total_value",
            }
        )
    return warnings


def build_invoice_description(
    po_number: str | None,
    program_name: str | None,
    service_name: str,
    reference_month: int,
    reference_year: int,
) -> str:
    parts: list[str] = []
    if po_number:
        parts.append(f"PO: {po_number}")
    if program_name:
        parts.append(program_name)
    parts.append(service_name)
    parts.append(f"{reference_month:02d}/{reference_year}")
    return " - ".join(parts)


def validate_service_rule_input(
    rule: ServiceRule, client_uuid: UUID, quantity: Decimal, total_value: Decimal
) -> None:
    if rule.client_uuid != client_uuid:
        raise BusinessValidationError("Regra de serviço não pertence ao cliente")
    if rule.status != EntityStatus.ACTIVE:
        raise BusinessValidationError("Regra de serviço está inativa")

    match rule.rule_type:
        case RuleType.MULTIPLICATION | RuleType.RANGE:
            if quantity <= 0:
                raise BusinessValidationError(
                    f"Quantidade deve ser maior que zero para regra do tipo '{rule.rule_type}'",
                )
        case RuleType.FIXED_VALUE | RuleType.VARIABLE_VALUE:
            if total_value <= 0:
                raise BusinessValidationError(
                    f"Valor total deve ser maior que zero para regra do tipo '{rule.rule_type}'",
                )

    if rule.rule_type == RuleType.RANGE and not rule.ranges:
        raise BusinessValidationError("Regra do tipo 'range' não possui faixas cadastradas")


# ── Montagem de respostas ────────────────────────────────────────────


def enrich_item(item: BillingItem, rule: ServiceRule | None) -> BillingItem:
    """Anexa ao item os dados da regra que a resposta exibe (sem nova consulta)."""
    if rule is not None:
        item.rule_type = str(rule.rule_type)
        item.service_rule_name = rule.name
        item.requires_client_approval = rule.requires_client_approval
        item.programs = [{"uuid": p.uuid, "name": p.name} for p in rule.programs]
    return item


def build_service_row(rec: ServiceRowRecord) -> dict[str, Any]:
    rule, item, billing = rec.rule, rec.item, rec.billing
    base_value = (item.base_value or rule.base_value) if item else rule.base_value
    return {
        "service_rule_uuid": rule.uuid,
        "service_rule_name": rule.name,
        "service_rule_code": rule.code,
        "rule_type": rule.rule_type,
        "percentage": rule.percentage,
        "base_value": base_value,
        "item_base_value": item.base_value if item else None,
        "programs": [{"uuid": p.uuid, "name": p.name} for p in rule.programs],
        "item_uuid": item.uuid if item else None,
        "quantity": item.quantity if item else None,
        "unit_value": item.unit_value if item else None,
        "total_value": item.total_value if item else None,
        "po_number": item.po_number if item else None,
        "invoice_description": item.invoice_description if item else None,
        "notes": item.notes if item else None,
        "billing_month": item.billing_month if item else None,
        "billing_year": item.billing_year if item else None,
        "competence_month": item.competence_month if item else None,
        "competence_year": item.competence_year if item else None,
        "item_version": item.version if item else None,
        "ranges": [
            {
                "uuid": r.uuid,
                "range_from": r.range_from,
                "range_to": r.range_to,
                "last_range": r.last_range,
                "range_type": r.range_type,
                "value": r.value,
            }
            for r in (rule.ranges if rule.rule_type == RuleType.RANGE else [])
        ],
        "status": item.status if item else BillingStatus.NO_ENTRY,
        "billing_uuid": billing.uuid if billing else None,
        "rejection_reason": item.rejection_reason if item else None,
        "billing_version": billing.version if billing else None,
        "billing_total_value": billing.total_value if billing else None,
        "requires_client_approval": rule.requires_client_approval,
    }


# ── Carga de recursos com autorização ────────────────────────────────


async def load_item_for_actor(
    item_gateway: BillingItemGateway,
    billing_gateway: BillingGateway,
    guard: ResourceAccessGuard,
    actor: Actor,
    item_uuid: UUID,
    *,
    operation: str,
) -> tuple[BillingItem, Billing]:
    """Carrega o lançamento só se estiver no escopo do usuário (404 caso contrário)."""
    message = "Lançamento não encontrado"
    item = await item_gateway.get_by_uuid(item_uuid)
    billing = await billing_gateway.get_by_uuid(item.billing_uuid) if item else None
    if item is None or billing is None:
        raise NotFoundError(message)
    await guard.ensure(
        actor,
        billing.client_uuid,
        billing.reference_year,
        billing.reference_month,
        resource="lancamento",
        resource_id=item_uuid,
        message=message,
        operation=operation,
    )
    return item, billing


async def require_client(client_gateway: ClientGateway, client_uuid: UUID) -> None:
    if await client_gateway.get_by_uuid(client_uuid) is None:
        raise NotFoundError("Cliente não encontrado")


async def require_rule(rule_gateway: ServiceRuleGateway, rule_uuid: UUID) -> ServiceRule:
    rule = await rule_gateway.get_by_uuid(rule_uuid)
    if rule is None:
        raise NotFoundError("Regra de serviço não encontrada")
    return rule


async def find_or_create_billing(
    billing_gateway: BillingGateway,
    client_uuid: UUID,
    year: int,
    month: int,
    service_rule_uuid: UUID,
    *,
    changed_by: str | None = None,
) -> Billing:
    existing = await billing_gateway.get_by_client_and_period(
        client_uuid, year, month, service_rule_uuid
    )
    if existing:
        return existing

    billing = Billing(
        client_uuid=client_uuid,
        reference_year=year,
        reference_month=month,
        service_rule_uuid=service_rule_uuid,
    )
    history = BillingHistory(
        billing_uuid=billing.uuid,
        previous_status=None,
        new_status=BillingStatus.NEW,
        notes="Faturamento criado automaticamente",
        changed_by=changed_by,
    )
    try:
        return await billing_gateway.create(billing, history=history)
    except ConflictError:
        # Outra requisição criou o mesmo faturamento no intervalo entre a consulta e a gravação.
        found = await billing_gateway.get_by_client_and_period(
            client_uuid, year, month, service_rule_uuid
        )
        if found is None:
            raise
        return found


def item_audit_event(
    event_type: str,
    actor: Actor,
    item_uuid: UUID,
    detail: str | None = None,
) -> AuditEvent:
    """Evento de auditoria de um lançamento.

    Não é gravado aqui: vai para o gateway do item, que o grava na mesma transação da
    operação (RS05). Assim não existe alteração efetivada sem registro.
    """
    return AuditEvent(
        event_type,
        actor.username,
        resource="lancamento",
        resource_id=str(item_uuid),
        detail=detail,
    )
