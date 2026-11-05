"""Caso de uso: replicar lançamento para meses subsequentes."""

from __future__ import annotations

from src.application.access_guard import ResourceAccessGuard
from src.application.use_cases.billing.commands import ReplicateItemsCommand
from src.application.use_cases.billing.create_billing_item import resolve_competence
from src.application.use_cases.billing.shared import (
    audit_item_event,
    build_changes,
    build_invoice_description,
    detect_value_divergences,
    enrich_item,
    find_or_create_billing,
    require_client,
    require_rule,
    snapshot_fields,
    validate_service_rule_input,
)
from src.domain.entities.billing import BillingItem, BillingItemHistory
from src.domain.ports.gateways.billing_gateway import BillingGateway
from src.domain.ports.gateways.billing_item_gateway import BillingItemGateway
from src.domain.ports.gateways.client_gateway import ClientGateway
from src.domain.ports.gateways.security_gateway import AuditLogGateway
from src.domain.ports.gateways.service_rule_gateway import ServiceRuleGateway
from src.domain.value_objects.billing_status import BillingStatus, HistoryAction


def _periods(year: int, month: int, count: int) -> list[tuple[int, int]]:
    periods: list[tuple[int, int]] = []
    for _ in range(count):
        periods.append((year, month))
        month += 1
        if month > 12:
            month, year = 1, year + 1
    return periods


class ReplicateItemsUseCase:
    def __init__(
        self,
        billing_gateway: BillingGateway,
        item_gateway: BillingItemGateway,
        client_gateway: ClientGateway,
        service_rule_gateway: ServiceRuleGateway,
        guard: ResourceAccessGuard,
        audit: AuditLogGateway,
    ) -> None:
        self._billings = billing_gateway
        self._items = item_gateway
        self._clients = client_gateway
        self._rules = service_rule_gateway
        self._guard = guard
        self._audit = audit

    async def execute(
        self, cmd: ReplicateItemsCommand
    ) -> tuple[list[BillingItem], list[dict[str, str]]]:
        periods = _periods(cmd.reference_year, cmd.reference_month, cmd.subsequent_months)

        # Todos os períodos precisam estar no escopo antes de gravar o primeiro lançamento.
        for year, month in periods:
            await self._guard.ensure(
                cmd.actor,
                cmd.client_uuid,
                year,
                month,
                resource="cliente",
                resource_id=cmd.client_uuid,
                message="Cliente não encontrado",
                operation="replicar_lancamento",
            )
        await require_client(self._clients, cmd.client_uuid)
        rule = await require_rule(self._rules, cmd.service_rule_uuid)
        validate_service_rule_input(rule, cmd.client_uuid, cmd.quantity, cmd.total_value)

        quantity, unit_value, total_value, effective_base = rule.calculate_value(
            cmd.quantity, cmd.total_value, cmd.base_value
        )
        warnings = detect_value_divergences(
            cmd.unit_value, cmd.total_value, unit_value, total_value
        )
        competence_month, competence_year = resolve_competence(
            cmd.competence_month, cmd.competence_year
        )
        invoice_description = cmd.invoice_description or build_invoice_description(
            cmd.po_number, None, rule.name, competence_month, competence_year
        )

        created: list[BillingItem] = []
        for year, month in periods:
            billing = await find_or_create_billing(
                self._billings,
                cmd.client_uuid,
                year,
                month,
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
                billing_month=cmd.billing_month if cmd.billing_month is not None else month,
                billing_year=cmd.billing_year if cmd.billing_year is not None else year,
                competence_month=competence_month,
                competence_year=competence_year,
            )
            history = BillingItemHistory(
                billing_item_uuid=item.uuid,
                previous_status=None,
                new_status=BillingStatus.NEW,
                notes="Lançamento replicado",
                action=HistoryAction.ITEM_CREATED,
                changes=build_changes(
                    item.uuid,
                    rule.name,
                    snapshot_fields(
                        {
                            "quantity": quantity,
                            "unit_value": unit_value,
                            "total_value": total_value,
                            "po_number": cmd.po_number,
                            "invoice_description": invoice_description,
                            "billing_month": item.billing_month,
                            "billing_year": item.billing_year,
                            "competence_month": competence_month,
                            "competence_year": competence_year,
                        }
                    ),
                ),
                changed_by=cmd.actor.username,
            )
            item = await self._items.create(item, history=history)
            await self._billings.recalculate_total(billing)
            await audit_item_event(
                self._audit, "lancamento_criado", cmd.actor, item.uuid, detail="replicação"
            )
            created.append(enrich_item(item, rule))
        return created, warnings
