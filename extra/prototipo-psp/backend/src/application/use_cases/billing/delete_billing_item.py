"""Caso de uso: excluir lançamento."""

from __future__ import annotations

from src.application.access_guard import ResourceAccessGuard
from src.application.use_cases.billing.commands import DeleteBillingItemCommand
from src.application.use_cases.billing.shared import (
    audit_item_event,
    build_changes,
    load_item_for_actor,
    snapshot_fields,
)
from src.domain.entities.billing import BillingItemHistory
from src.domain.ports.gateways.billing_gateway import BillingGateway
from src.domain.ports.gateways.billing_item_gateway import BillingItemGateway
from src.domain.ports.gateways.security_gateway import AuditLogGateway
from src.domain.ports.gateways.service_rule_gateway import ServiceRuleGateway
from src.domain.ports.services.billing_events import BillingEventPublisher
from src.domain.value_objects.billing_status import HistoryAction


class DeleteBillingItemUseCase:
    def __init__(
        self,
        billing_gateway: BillingGateway,
        item_gateway: BillingItemGateway,
        service_rule_gateway: ServiceRuleGateway,
        guard: ResourceAccessGuard,
        audit: AuditLogGateway,
        events: BillingEventPublisher,
    ) -> None:
        self._billings = billing_gateway
        self._items = item_gateway
        self._rules = service_rule_gateway
        self._guard = guard
        self._audit = audit
        self._events = events

    async def execute(self, cmd: DeleteBillingItemCommand) -> None:
        item, billing = await load_item_for_actor(
            self._items,
            self._billings,
            self._guard,
            cmd.actor,
            cmd.item_uuid,
            operation="excluir_lancamento",
        )
        item.assert_editable()

        rule = await self._rules.get_by_uuid(item.service_rule_uuid)
        # Guarda os valores anteriores: depois da exclusão só a timeline conta o que existia.
        snapshot = snapshot_fields(
            {
                "quantity": item.quantity,
                "unit_value": item.unit_value,
                "total_value": item.total_value,
                "po_number": item.po_number,
                "invoice_description": item.invoice_description,
                "billing_month": item.billing_month,
                "billing_year": item.billing_year,
            },
            as_old=True,
        )
        history = BillingItemHistory(
            billing_item_uuid=item.uuid,
            previous_status=item.status,
            new_status=item.status,
            notes="Lançamento excluído",
            action=HistoryAction.ITEM_DELETED,
            changes=build_changes(item.uuid, rule.name if rule else None, snapshot),
            changed_by=cmd.actor.username,
        )
        await self._items.delete(item, history=history)

        # Último lançamento do faturamento: o faturamento pai também sai (RF-PSP-26).
        if not await self._items.list_by_billing(billing.uuid):
            await self._billings.delete(billing)
        else:
            await self._billings.recalculate_total(billing)
        await audit_item_event(self._audit, "lancamento_excluido", cmd.actor, item.uuid)
        await self._events.billing_changed(
            billing.client_uuid, billing.reference_year, billing.reference_month
        )
