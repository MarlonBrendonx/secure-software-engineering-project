"""Caso de uso: mudar status de lançamento(s) pela máquina de estados."""

from __future__ import annotations

from uuid import UUID

from src.application.access_guard import ResourceAccessGuard
from src.application.use_cases.billing.commands import ChangeItemStatusCommand
from src.application.use_cases.billing.shared import (
    enrich_item,
    item_audit_event,
    load_item_for_actor,
)
from src.domain.entities.audit import AuditEvent
from src.domain.entities.billing import (
    APPROVAL_TARGETS,
    TRANSITIONS,
    Billing,
    BillingItem,
    BillingItemHistory,
    ensure_segregation_of_duties,
)
from src.domain.exceptions import BusinessValidationError, ForbiddenError, NotFoundError
from src.domain.ports.gateways.billing_gateway import BillingGateway
from src.domain.ports.gateways.billing_item_gateway import BillingItemGateway
from src.domain.ports.gateways.client_gateway import ClientGateway
from src.domain.ports.gateways.security_gateway import AuditLogGateway
from src.domain.ports.gateways.service_rule_gateway import ServiceRuleGateway
from src.domain.ports.services.billing_events import BillingEventPublisher
from src.domain.value_objects.billing_status import BillingStatus, HistoryAction


class ChangeItemStatusUseCase:
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

    async def execute(self, cmd: ChangeItemStatusCommand) -> BillingItem:
        item_uuid = cmd.item_uuids[0]
        item, billing = await load_item_for_actor(
            self._items,
            self._billings,
            self._guard,
            cmd.actor,
            item_uuid,
            operation="mudar_status",
        )
        target = BillingStatus(cmd.new_status)

        # Perfil antes das regras de negócio: quem não pode agir não descobre o estado do item.
        BillingItem.check_role_for_status(target, cmd.actor.role)
        item.validate_transition(target)
        await self._ensure_segregation(item, target, cmd)
        BillingItem.validate_rejection(target, cmd.rejection_reason)
        errors = await self._check_client_approval_rules([item], {billing.uuid: billing}, target)
        if errors:
            raise BusinessValidationError(errors[0])

        previous = item.status
        updated = await self._items.update(
            item,
            self._changes(target, cmd.rejection_reason),
            expected_version=item.version,
            history=self._history(item, previous, target, cmd),
            audit=item_audit_event(
                "mudanca_status", cmd.actor, item.uuid, detail=f"{previous} → {target}"
            ),
        )
        await self._events.billing_changed(
            billing.client_uuid, billing.reference_year, billing.reference_month
        )
        rule = await self._rules.get_by_uuid(updated.service_rule_uuid)
        return enrich_item(updated, rule)

    async def execute_batch(self, cmd: ChangeItemStatusCommand) -> list[BillingItem]:
        target = BillingStatus(cmd.new_status)
        BillingItem.check_role_for_status(target, cmd.actor.role)

        items = await self._items.get_by_uuids(cmd.item_uuids)
        billing_map = {
            b.uuid: b for b in await self._billings.get_by_uuids([i.billing_uuid for i in items])
        }

        # Item de outro escopo é tratado como inexistente: a lista de "não encontrados" não
        # revela quais ids existem (RS03).
        visible: list[BillingItem] = []
        for item in items:
            billing = billing_map.get(item.billing_uuid)
            if billing is None:
                continue
            try:
                await self._guard.ensure(
                    cmd.actor,
                    billing.client_uuid,
                    billing.reference_year,
                    billing.reference_month,
                    resource="lancamento",
                    resource_id=item.uuid,
                    message="Lançamento não encontrado",
                    operation="mudar_status_lote",
                )
            except NotFoundError:
                continue
            visible.append(item)

        found = {i.uuid for i in visible}
        missing = [u for u in cmd.item_uuids if u not in found]
        if missing:
            raise NotFoundError(
                f"Lançamentos não encontrados: {', '.join(str(u) for u in missing)}"
            )

        # Todas as validações antes de qualquer gravação: um erro e nenhum item muda (RF-PSP-36).
        errors = [
            f"Lançamento {i.uuid}: transição de '{i.status}' para '{target}' não permitida"
            for i in visible
            if target not in TRANSITIONS.get(i.status, [])
        ]
        if target == BillingStatus.REJECTED and not (
            cmd.rejection_reason and cmd.rejection_reason.strip()
        ):
            errors.append("Motivo da reprovação é obrigatório ao reprovar")
        if errors:
            raise BusinessValidationError(errors)

        for i in visible:
            await self._ensure_segregation(i, target, cmd)

        errors = await self._check_client_approval_rules(visible, billing_map, target)
        if errors:
            raise BusinessValidationError(errors)

        updates: list[tuple[BillingItem, dict[str, object], BillingItemHistory | None]] = [
            (
                i,
                self._changes(target, cmd.rejection_reason),
                self._history(i, i.status, target, cmd),
            )
            for i in visible
        ]
        previous = {i.uuid: i.status for i in visible}
        updated = await self._items.update_many(
            updates,
            audits=[
                item_audit_event(
                    "mudanca_status", cmd.actor, i.uuid, detail=f"{previous[i.uuid]} → {target}"
                )
                for i in visible
            ],
        )
        affected = {
            (b.client_uuid, b.reference_year, b.reference_month)
            for b in (billing_map[i.billing_uuid] for i in updated)
        }
        for client_uuid, year, month in affected:
            await self._events.billing_changed(client_uuid, year, month)
        rules = {
            r.uuid: r
            for r in await self._rules.list_by_clients(
                list({billing_map[i.billing_uuid].client_uuid for i in updated})
            )
        }
        return [enrich_item(i, rules.get(i.service_rule_uuid)) for i in updated]

    async def _ensure_segregation(
        self, item: BillingItem, target: BillingStatus, cmd: ChangeItemStatusCommand
    ) -> None:
        """R18: nega a autoaprovação e deixa a tentativa registrada na auditoria."""
        if target not in APPROVAL_TARGETS:
            return
        history = await self._items.get_history(item.uuid)
        try:
            ensure_segregation_of_duties(target, cmd.actor.username, history)
        except ForbiddenError:
            await self._audit.record(
                AuditEvent(
                    "autoaprovacao_negada",
                    cmd.actor.username,
                    resource="lancamento",
                    resource_id=str(item.uuid),
                    detail=f"{item.status} → {target}",
                )
            )
            raise

    async def _check_client_approval_rules(
        self,
        items: list[BillingItem],
        billing_map: dict[UUID, Billing],
        target: BillingStatus,
    ) -> list[str]:
        """Regras de aprovação do cliente (RF-PSP-33 e 34). Devolve as mensagens de erro."""
        errors: list[str] = []
        if target == BillingStatus.CLIENT_APPROVAL:
            client_uuids = {billing_map[i.billing_uuid].client_uuid for i in items}
            names = await self._clients.get_names_by_uuids(client_uuids)
            for client_uuid in client_uuids:
                client = await self._clients.get_by_uuid(client_uuid)
                if client is None or not client.has_client_approval_contract:
                    errors.append(
                        f"Cliente '{names.get(client_uuid, client_uuid)}': "
                        "não possui contrato com aprovação de cliente habilitada"
                    )

        if target == BillingStatus.FINANCIAL_REVIEW:
            for i in items:
                if i.status != BillingStatus.MANAGEMENT_APPROVAL:
                    continue
                rule = await self._rules.get_by_uuid(i.service_rule_uuid)
                if rule is not None and rule.requires_client_approval:
                    client_uuid = billing_map[i.billing_uuid].client_uuid
                    names = await self._clients.get_names_by_uuids({client_uuid})
                    errors.append(
                        f"'{names.get(client_uuid, client_uuid)}' / '{rule.name}': requer "
                        "aprovação de cliente antes da revisão financeira"
                    )
        return errors

    @staticmethod
    def _changes(target: BillingStatus, rejection_reason: str | None) -> dict[str, object]:
        # O motivo só é mantido enquanto o status for Rejected (RF-PSP-32).
        return {
            "status": target,
            "rejection_reason": rejection_reason if target == BillingStatus.REJECTED else None,
        }

    @staticmethod
    def _history(
        item: BillingItem,
        previous: BillingStatus,
        target: BillingStatus,
        cmd: ChangeItemStatusCommand,
    ) -> BillingItemHistory:
        return BillingItemHistory(
            billing_item_uuid=item.uuid,
            previous_status=previous,
            new_status=target,
            notes=cmd.rejection_reason,
            action=HistoryAction.STATUS_CHANGE,
            changed_by=cmd.actor.username,
        )
