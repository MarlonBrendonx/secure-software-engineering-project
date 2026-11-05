"""DTOs de entrada dos casos de uso de cadastro (regras de serviço)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from src.application.actor import Actor
from src.domain.entities.service_rule import ServiceRule
from src.domain.value_objects.billing_status import EntityStatus, RangeType, RuleType


@dataclass(frozen=True)
class RangeInput:
    range_from: int
    range_to: int | None
    last_range: bool
    range_type: RangeType
    value: Decimal


@dataclass(frozen=True)
class CreateServiceRuleCommand:
    actor: Actor
    client_uuid: UUID
    name: str
    rule_type: RuleType
    status: EntityStatus = EntityStatus.ACTIVE
    percentage: Decimal | None = None
    base_value: Decimal | None = None
    requires_client_approval: bool = False
    program_uuids: list[UUID] = field(default_factory=list)
    ranges: list[RangeInput] = field(default_factory=list)


@dataclass(frozen=True)
class UpdateServiceRuleCommand:
    """Campo `None` significa "não enviado": a atualização é parcial, como no original."""

    actor: Actor
    client_uuid: UUID
    rule_uuid: UUID
    version: int
    name: str | None = None
    rule_type: RuleType | None = None
    status: EntityStatus | None = None
    percentage: Decimal | None = None
    base_value: Decimal | None = None
    requires_client_approval: bool | None = None
    program_uuids: list[UUID] | None = None
    ranges: list[RangeInput] | None = None


@dataclass(frozen=True)
class ServiceRuleView:
    """A regra e o que a tela precisa saber dela e que não faz parte da entidade."""

    rule: ServiceRule
    has_billing_items: bool
    client_name: str
