"""Casos de uso do cadastro de regras de serviço.

Quem escreve é só o admin (a rota exige o perfil); aqui fica a conferência sobre o recurso:
o cliente precisa estar no escopo de quem pede, e cliente fora do escopo responde 404, igual
a cliente inexistente.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from uuid import UUID

from src.application.access_guard import ResourceAccessGuard
from src.application.actor import Actor
from src.application.use_cases.registry.commands import (
    CreateServiceRuleCommand,
    RangeInput,
    ServiceRuleView,
    UpdateServiceRuleCommand,
)
from src.domain.entities.audit import AuditEvent
from src.domain.entities.client import Client
from src.domain.entities.service_rule import (
    Program,
    ServiceRule,
    ServiceRuleRange,
    validate_rule_definition,
)
from src.domain.exceptions import BusinessValidationError, ConflictError, NotFoundError
from src.domain.ports.gateways.client_gateway import ClientGateway
from src.domain.ports.gateways.program_gateway import ProgramGateway
from src.domain.ports.gateways.security_gateway import AuditLogGateway
from src.domain.ports.gateways.service_rule_gateway import ServiceRuleGateway
from src.domain.value_objects.billing_status import RuleType

_CLIENT_NOT_FOUND = "Cliente não encontrado"
_RULE_NOT_FOUND = "Regra de serviço não encontrada"
_RESOURCE = "regra_servico"

# Com lançamentos, só o status pode mudar: alterar o cálculo reescreveria o passado.
_RESTRICTED_WITH_ITEMS = (
    "name",
    "rule_type",
    "percentage",
    "base_value",
    "requires_client_approval",
)


def _build_ranges(items: list[RangeInput]) -> list[ServiceRuleRange]:
    return [
        ServiceRuleRange(
            range_from=i.range_from,
            range_to=i.range_to,
            last_range=i.last_range,
            range_type=i.range_type,
            value=i.value,
        )
        for i in items
    ]


def _range_key(ranges: list[ServiceRuleRange]) -> list[tuple[int, int | None, bool, str, Decimal]]:
    """Forma comparável das faixas, sem o uuid que muda a cada gravação."""
    return sorted(
        (r.range_from, r.range_to, r.last_range, str(r.range_type), r.value) for r in ranges
    )


class _RuleSupport:
    """Carga e conferências comuns aos casos de uso de escrita e de leitura."""

    def __init__(
        self,
        rules: ServiceRuleGateway,
        clients: ClientGateway,
        guard: ResourceAccessGuard,
    ) -> None:
        self._rules = rules
        self._clients = clients
        self._guard = guard

    async def _load_client(self, actor: Actor, client_uuid: UUID, operation: str) -> Client:
        await self._guard.ensure_client(
            actor,
            client_uuid,
            resource="cliente",
            resource_id=client_uuid,
            message=_CLIENT_NOT_FOUND,
            operation=operation,
        )
        client = await self._clients.get_by_uuid(client_uuid)
        if client is None:
            raise NotFoundError(_CLIENT_NOT_FOUND)
        return client

    async def _load_rule(
        self, actor: Actor, client_uuid: UUID, rule_uuid: UUID, operation: str
    ) -> tuple[Client, ServiceRule]:
        client = await self._load_client(actor, client_uuid, operation)
        rule = await self._rules.get_by_uuid(rule_uuid)
        # Regra de outro cliente responde como inexistente, sem revelar que existe.
        if rule is None or rule.client_uuid != client_uuid:
            raise NotFoundError(_RULE_NOT_FOUND)
        return client, rule


class _ProgramResolver:
    def __init__(self, programs: ProgramGateway) -> None:
        self._programs = programs

    async def resolve(self, client_uuid: UUID, program_uuids: list[UUID]) -> list[Program]:
        """Resolve os ids no catálogo e confere que todos pertencem ao cliente da regra."""
        resolved: list[Program] = []
        for program_uuid in dict.fromkeys(program_uuids):  # sem repetidos, mantém a ordem
            program = await self._programs.get_by_uuid(program_uuid)
            if program is None:
                raise NotFoundError("Programa não encontrado")
            if program.client_uuid != client_uuid:
                raise BusinessValidationError(
                    f"Programa '{program.name}' não pertence ao cliente da regra"
                )
            resolved.append(Program(uuid=program.uuid, name=program.name))
        return resolved


class CreateServiceRuleUseCase(_RuleSupport):
    def __init__(
        self,
        rules: ServiceRuleGateway,
        clients: ClientGateway,
        programs: ProgramGateway,
        guard: ResourceAccessGuard,
        audit: AuditLogGateway,
    ) -> None:
        super().__init__(rules, clients, guard)
        self._resolver = _ProgramResolver(programs)
        self._audit = audit

    async def execute(self, cmd: CreateServiceRuleCommand) -> ServiceRuleView:
        client = await self._load_client(cmd.actor, cmd.client_uuid, "criar_regra_servico")
        ranges = _build_ranges(cmd.ranges) if cmd.rule_type == RuleType.RANGE else []
        validate_rule_definition(cmd.rule_type, cmd.percentage, cmd.base_value, ranges)
        programs = await self._resolver.resolve(cmd.client_uuid, cmd.program_uuids)

        rule = ServiceRule(
            client_uuid=cmd.client_uuid,
            name=cmd.name,
            code=0,  # o gateway atribui o próximo código
            rule_type=cmd.rule_type,
            status=cmd.status,
            percentage=cmd.percentage if cmd.rule_type == RuleType.PERCENTAGE else None,
            base_value=cmd.base_value
            if cmd.rule_type in (RuleType.MULTIPLICATION, RuleType.PERCENTAGE)
            else None,
            requires_client_approval=cmd.requires_client_approval,
            programs=programs,
            ranges=ranges,
        )
        saved = await self._rules.create(rule)
        await self._audit.record(
            AuditEvent(
                "regra_servico_criada",
                cmd.actor.username,
                resource=_RESOURCE,
                resource_id=str(saved.uuid),
                detail=f"cliente={cmd.client_uuid} codigo={saved.code} tipo={saved.rule_type}",
            )
        )
        return ServiceRuleView(saved, has_billing_items=False, client_name=client.name)


class UpdateServiceRuleUseCase(_RuleSupport):
    def __init__(
        self,
        rules: ServiceRuleGateway,
        clients: ClientGateway,
        programs: ProgramGateway,
        guard: ResourceAccessGuard,
        audit: AuditLogGateway,
    ) -> None:
        super().__init__(rules, clients, guard)
        self._resolver = _ProgramResolver(programs)
        self._audit = audit

    async def execute(self, cmd: UpdateServiceRuleCommand) -> ServiceRuleView:
        client, rule = await self._load_rule(
            cmd.actor, cmd.client_uuid, cmd.rule_uuid, "editar_regra_servico"
        )
        if rule.version != cmd.version:
            raise ConflictError(
                "O registro foi modificado por outro usuário. "
                "Recarregue os dados e tente novamente."
            )

        rule_type = cmd.rule_type or rule.rule_type
        if rule_type != RuleType.RANGE:
            ranges: list[ServiceRuleRange] = []
        elif cmd.ranges is not None:
            ranges = _build_ranges(cmd.ranges)
        else:
            ranges = list(rule.ranges)
        programs = (
            await self._resolver.resolve(cmd.client_uuid, cmd.program_uuids)
            if cmd.program_uuids is not None
            else rule.programs
        )
        # Ao trocar o tipo, o que não pertence ao novo tipo é limpo: senão um percentual
        # antigo ficaria guardado e voltaria a valer se a regra mudasse de tipo outra vez.
        percentage = cmd.percentage if cmd.percentage is not None else rule.percentage
        base_value = cmd.base_value if cmd.base_value is not None else rule.base_value
        if rule_type != RuleType.PERCENTAGE:
            percentage = None
        if rule_type not in (RuleType.MULTIPLICATION, RuleType.PERCENTAGE):
            base_value = None

        updated = dataclasses.replace(
            rule,
            name=cmd.name if cmd.name is not None else rule.name,
            rule_type=rule_type,
            status=cmd.status or rule.status,
            percentage=percentage,
            base_value=base_value,
            requires_client_approval=(
                cmd.requires_client_approval
                if cmd.requires_client_approval is not None
                else rule.requires_client_approval
            ),
            programs=programs,
            ranges=ranges,
        )
        validate_rule_definition(updated.rule_type, updated.percentage, updated.base_value, ranges)

        changed = [
            f
            for f in (
                "name",
                "rule_type",
                "status",
                "percentage",
                "base_value",
                "requires_client_approval",
            )
            if getattr(updated, f) != getattr(rule, f)
        ]
        if {p.uuid for p in updated.programs} != {p.uuid for p in rule.programs}:
            changed.append("programs")
        if _range_key(updated.ranges) != _range_key(rule.ranges):
            changed.append("ranges")

        has_items = await self._rules.has_billing_items(rule)
        if has_items:
            blocked = [f for f in changed if f in (*_RESTRICTED_WITH_ITEMS, "programs", "ranges")]
            if blocked:
                raise BusinessValidationError(
                    "Regra de serviço com lançamentos de faturamento: apenas o status pode ser "
                    f"alterado. Campo(s) bloqueado(s): {', '.join(blocked)}"
                )

        saved = await self._rules.update(updated, expected_version=cmd.version)
        await self._audit.record(
            AuditEvent(
                "regra_servico_atualizada",
                cmd.actor.username,
                resource=_RESOURCE,
                resource_id=str(saved.uuid),
                # Só os nomes dos campos: os valores ficam no próprio registro.
                detail=f"campos={','.join(changed) or 'nenhum'}",
            )
        )
        return ServiceRuleView(saved, has_billing_items=has_items, client_name=client.name)


class DeleteServiceRuleUseCase(_RuleSupport):
    def __init__(
        self,
        rules: ServiceRuleGateway,
        clients: ClientGateway,
        guard: ResourceAccessGuard,
        audit: AuditLogGateway,
    ) -> None:
        super().__init__(rules, clients, guard)
        self._audit = audit

    async def execute(self, actor: Actor, client_uuid: UUID, rule_uuid: UUID) -> None:
        _, rule = await self._load_rule(actor, client_uuid, rule_uuid, "excluir_regra_servico")
        if await self._rules.has_billing_items(rule):
            raise BusinessValidationError(
                "Não é possível excluir uma regra de serviço que possui lançamentos de faturamento"
            )
        await self._rules.delete(rule)
        await self._audit.record(
            AuditEvent(
                "regra_servico_excluida",
                actor.username,
                resource=_RESOURCE,
                resource_id=str(rule.uuid),
                detail=f"cliente={client_uuid} codigo={rule.code}",
            )
        )


class ListServiceRulesUseCase(_RuleSupport):
    async def execute(
        self,
        actor: Actor,
        client_uuid: UUID,
        offset: int,
        limit: int,
        *,
        program_name: str | None = None,
        service_name: str | None = None,
    ) -> tuple[list[ServiceRuleView], int]:
        client = await self._load_client(actor, client_uuid, "listar_regras_servico")
        rules, total = await self._rules.list_by_client(
            client_uuid, offset, limit, program_name=program_name, service_name=service_name
        )
        views = [
            ServiceRuleView(r, await self._rules.has_billing_items(r), client.name) for r in rules
        ]
        return views, total


class GetServiceRuleUseCase(_RuleSupport):
    async def execute(self, actor: Actor, client_uuid: UUID, rule_uuid: UUID) -> ServiceRuleView:
        client, rule = await self._load_rule(
            actor, client_uuid, rule_uuid, "consultar_regra_servico"
        )
        return ServiceRuleView(rule, await self._rules.has_billing_items(rule), client.name)
