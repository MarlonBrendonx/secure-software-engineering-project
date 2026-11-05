"""Caso de uso: alterar lançamento com bloqueio otimista."""

from __future__ import annotations

import dataclasses

from src.application.access_guard import ResourceAccessGuard
from src.application.use_cases.billing.commands import UpdateBillingItemCommand
from src.application.use_cases.billing.shared import (
    audit_item_event,
    build_changes,
    detect_value_divergences,
    diff_fields,
    enrich_item,
    load_item_for_actor,
)
from src.domain.entities.billing import BillingItem, BillingItemHistory
from src.domain.exceptions import BusinessValidationError, ConflictError
from src.domain.ports.gateways.billing_gateway import BillingGateway
from src.domain.ports.gateways.billing_item_gateway import BillingItemGateway
from src.domain.ports.gateways.security_gateway import AuditLogGateway
from src.domain.ports.gateways.service_rule_gateway import ServiceRuleGateway
from src.domain.value_objects.billing_status import HistoryAction

_NON_DATA_FIELDS = frozenset({"actor", "item_uuid", "version"})


class UpdateBillingItemUseCase:
    def __init__(
        self,
        billing_gateway: BillingGateway,
        item_gateway: BillingItemGateway,
        service_rule_gateway: ServiceRuleGateway,
        guard: ResourceAccessGuard,
        audit: AuditLogGateway,
    ) -> None:
        self._billings = billing_gateway
        self._items = item_gateway
        self._rules = service_rule_gateway
        self._guard = guard
        self._audit = audit

    async def execute(
        self, cmd: UpdateBillingItemCommand
    ) -> tuple[BillingItem, list[dict[str, str]]]:
        item, billing = await load_item_for_actor(
            self._items,
            self._billings,
            self._guard,
            cmd.actor,
            cmd.item_uuid,
            operation="atualizar_lancamento",
        )
        item.assert_editable()

        if item.version != cmd.version:
            raise ConflictError(
                "O registro foi modificado por outro usuário. "
                "Recarregue os dados e tente novamente.",
            )

        raw = {f.name: getattr(cmd, f.name) for f in dataclasses.fields(cmd)}
        update_data = {k: v for k, v in raw.items() if k not in _NON_DATA_FIELDS and v is not None}

        rule = await self._rules.get_by_uuid(item.service_rule_uuid)
        warnings: list[dict[str, str]] = []
        if rule is not None:
            quantity = update_data.get("quantity", item.quantity)
            sent_total = update_data.get("total_value", item.total_value)
            base_value = update_data.get("base_value", item.base_value)
            quantity, unit_value, total_value, effective_base = rule.calculate_value(
                quantity, sent_total, base_value
            )
            if total_value <= 0:
                raise BusinessValidationError("Valor total deve ser maior que zero")
            warnings = detect_value_divergences(
                update_data.get("unit_value", item.unit_value), sent_total, unit_value, total_value
            )
            update_data.update(
                quantity=quantity,
                unit_value=unit_value,
                total_value=total_value,
                base_value=effective_base,
            )
        elif "total_value" in update_data and update_data["total_value"] <= 0:
            raise BusinessValidationError("Valor total deve ser maior que zero")

        old_values = {k: getattr(item, k) for k in update_data}
        diff = diff_fields(old_values, update_data)
        history = BillingItemHistory(
            billing_item_uuid=item.uuid,
            previous_status=item.status,
            new_status=item.status,
            notes="Lançamento atualizado",
            action=HistoryAction.ITEM_UPDATED,
            changes=build_changes(item.uuid, rule.name if rule else None, diff) if diff else None,
            changed_by=cmd.actor.username,
        )
        updated = await self._items.update(
            item, update_data, expected_version=cmd.version, history=history
        )
        await self._billings.recalculate_total(billing)
        await audit_item_event(self._audit, "lancamento_atualizado", cmd.actor, item.uuid)
        return enrich_item(updated, rule), warnings
