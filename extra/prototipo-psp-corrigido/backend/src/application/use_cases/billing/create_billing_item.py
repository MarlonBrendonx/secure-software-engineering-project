"""Caso de uso: criar lançamento (cria o faturamento do período se necessário)."""

from __future__ import annotations

from datetime import datetime

from src.application.access_guard import ResourceAccessGuard
from src.application.use_cases.billing.commands import CreateBillingItemCommand
from src.application.use_cases.billing.shared import (
    build_changes,
    build_invoice_description,
    detect_value_divergences,
    enrich_item,
    find_or_create_billing,
    item_audit_event,
    require_client,
    require_rule,
    snapshot_fields,
    validate_service_rule_input,
)
from src.domain.entities.billing import BillingItem, BillingItemHistory
from src.domain.exceptions import BusinessValidationError
from src.domain.ports.gateways.billing_gateway import BillingGateway
from src.domain.ports.gateways.billing_item_gateway import BillingItemGateway
from src.domain.ports.gateways.client_gateway import ClientGateway
from src.domain.ports.gateways.security_gateway import AuditLogGateway
from src.domain.ports.gateways.service_rule_gateway import ServiceRuleGateway
from src.domain.ports.services.billing_events import BillingEventPublisher
from src.domain.value_objects.billing_status import BillingStatus, HistoryAction


def resolve_competence(month: int | None, year: int | None) -> tuple[int, int]:
    """Sem competência informada, assume o mês e o ano correntes (RF-PSP-10)."""
    now = datetime.now()
    return (month if month is not None else now.month, year if year is not None else now.year)


class CreateBillingItemUseCase:
    def __init__(
        self,
        billing_gateway: BillingGateway,
        item_gateway: BillingItemGateway,
        client_gateway: ClientGateway,
        service_rule_gateway: ServiceRuleGateway,
        guard: ResourceAccessGuard,
        audit: AuditLogGateway,
        events: BillingEventPublisher,
    ) -> None:
        self._billings = billing_gateway
        self._items = item_gateway
        self._clients = client_gateway
        self._rules = service_rule_gateway
        self._guard = guard
        self._audit = audit
        self._events = events

    async def execute(
        self, cmd: CreateBillingItemCommand
    ) -> tuple[BillingItem, list[dict[str, str]]]:
        # Escopo primeiro: cliente fora do escopo responde igual a cliente inexistente.
        await self._guard.ensure(
            cmd.actor,
            cmd.client_uuid,
            cmd.reference_year,
            cmd.reference_month,
            resource="cliente",
            resource_id=cmd.client_uuid,
            message="Cliente não encontrado",
            operation="criar_lancamento",
        )
        await require_client(self._clients, cmd.client_uuid)
        rule = await require_rule(self._rules, cmd.service_rule_uuid)
        validate_service_rule_input(rule, cmd.client_uuid, cmd.quantity, cmd.total_value)

        quantity, unit_value, total_value, effective_base = rule.calculate_value(
            cmd.quantity, cmd.total_value, cmd.base_value
        )
        if total_value <= 0:
            raise BusinessValidationError("Valor total deve ser maior que zero")

        warnings = detect_value_divergences(
            cmd.unit_value, cmd.total_value, unit_value, total_value
        )
        competence_month, competence_year = resolve_competence(
            cmd.competence_month, cmd.competence_year
        )
        invoice_description = cmd.invoice_description or build_invoice_description(
            cmd.po_number, None, rule.name, competence_month, competence_year
        )

        billing = await find_or_create_billing(
            self._billings,
            cmd.client_uuid,
            cmd.reference_year,
            cmd.reference_month,
            cmd.service_rule_uuid,
            changed_by=cmd.actor.username,
        )
        item = BillingItem(
            billing_uuid=billing.uuid,
            service_rule_uuid=cmd.service_rule_uuid,
            quantity=quantity,
            unit_value=unit_value,
            total_value=total_value,
            base_value=effective_base,
            po_number=cmd.po_number,
            invoice_description=invoice_description,
            notes=cmd.notes,
            billing_month=cmd.billing_month,
            billing_year=cmd.billing_year,
            competence_month=competence_month,
            competence_year=competence_year,
        )
        changes = build_changes(
            item.uuid,
            rule.name,
            snapshot_fields(
                {
                    "quantity": quantity,
                    "unit_value": unit_value,
                    "total_value": total_value,
                    "po_number": cmd.po_number,
                    "invoice_description": invoice_description,
                    "billing_month": cmd.billing_month,
                    "billing_year": cmd.billing_year,
                    "competence_month": competence_month,
                    "competence_year": competence_year,
                }
            ),
        )
        history = BillingItemHistory(
            billing_item_uuid=item.uuid,
            previous_status=None,
            new_status=BillingStatus.NEW,
            notes="Lançamento criado",
            action=HistoryAction.ITEM_CREATED,
            changes=changes,
            changed_by=cmd.actor.username,
        )
        item = await self._items.create(
            item,
            history=history,
            audit=item_audit_event("lancamento_criado", cmd.actor, item.uuid),
        )
        await self._billings.recalculate_total(billing)
        await self._events.billing_changed(cmd.client_uuid, cmd.reference_year, cmd.reference_month)
        return enrich_item(item, rule), warnings
