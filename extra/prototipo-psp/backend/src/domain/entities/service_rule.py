"""Regra de serviço contratada e o cálculo autoritativo do valor."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from src.domain.entities.base import AggregateRoot
from src.domain.exceptions import BusinessValidationError
from src.domain.value_objects.billing_status import EntityStatus, RangeType, RuleType


@dataclass
class ServiceRuleRange:
    range_from: int
    range_to: int | None
    last_range: bool
    range_type: RangeType
    value: Decimal
    uuid: UUID | None = None

    def __post_init__(self) -> None:
        if isinstance(self.range_type, str):
            self.range_type = RangeType(self.range_type)


@dataclass
class Program:
    uuid: UUID
    name: str


@dataclass
class ServiceRule(AggregateRoot):
    client_uuid: UUID
    name: str
    code: int
    rule_type: RuleType
    status: EntityStatus = EntityStatus.ACTIVE
    percentage: Decimal | None = None
    base_value: Decimal | None = None
    # Quando verdadeiro, o lançamento só pode passar pela aprovação do cliente (RF-PSP-34).
    requires_client_approval: bool = False
    programs: list[Program] = field(default_factory=list)
    ranges: list[ServiceRuleRange] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.rule_type, str):
            self.rule_type = RuleType(self.rule_type)
        if isinstance(self.status, str):
            self.status = EntityStatus(self.status)

    def calculate_value(
        self,
        quantity: Decimal,
        total_value: Decimal,
        base_value: Decimal | None = None,
    ) -> tuple[Decimal, Decimal, Decimal, Decimal | None]:
        """Devolve (quantidade, unitário, total, base efetiva).

        O servidor é a autoridade sobre o valor (RF-PSP-15): o que o cliente HTTP
        envia só é usado onde a regra realmente aceita valor informado.
        """
        match self.rule_type:
            case RuleType.FIXED_VALUE | RuleType.VARIABLE_VALUE:
                return quantity, total_value, total_value, base_value
            case RuleType.MULTIPLICATION:
                bv = base_value or self.base_value or Decimal("0")
                unit = bv if quantity else Decimal("0")
                return quantity, unit, quantity * bv, None
            case RuleType.PERCENTAGE:
                pct = self.percentage or Decimal("0")
                bv = base_value or self.base_value or Decimal("0")
                calculated = (bv * pct) / Decimal("100")
                return quantity, calculated, calculated, bv
            case RuleType.RANGE:
                unit_value, total = self.calculate_range(quantity)
                return quantity, unit_value, total, None
            case _:
                return quantity, total_value, total_value, base_value

    def calculate_range(self, quantity: Decimal) -> tuple[Decimal, Decimal]:
        """Aplica a faixa de maior `range_from` menor ou igual à quantidade."""
        matched: ServiceRuleRange | None = None
        for r in sorted(self.ranges, key=lambda r: r.range_from):
            if quantity >= r.range_from:
                matched = r
        if not matched or not matched.value:
            return Decimal("0"), Decimal("0")
        if matched.range_type == RangeType.PER_UNIT_VALUE:
            return matched.value, quantity * matched.value
        return matched.value, matched.value


def validate_rule_definition(
    rule_type: RuleType,
    percentage: Decimal | None,
    base_value: Decimal | None,
    ranges: list[ServiceRuleRange],
) -> None:
    """Confere que a regra traz os campos que o seu tipo exige (mesmas regras do original)."""
    match rule_type:
        case RuleType.PERCENTAGE:
            if percentage is None:
                raise BusinessValidationError(
                    "Percentual é obrigatório para regra do tipo 'percentage'"
                )
            if not Decimal("0.01") <= percentage <= Decimal("100"):
                raise BusinessValidationError("Percentual da regra deve estar entre 0.01 e 100.00")
        case RuleType.MULTIPLICATION:
            if base_value is None:
                raise BusinessValidationError(
                    "Valor base é obrigatório para regra do tipo 'multiplication'"
                )
        case RuleType.RANGE:
            if not ranges:
                raise BusinessValidationError(
                    "Pelo menos uma faixa é obrigatória para regra do tipo 'range'"
                )
            validate_ranges(ranges)


def validate_ranges(ranges: list[ServiceRuleRange]) -> None:
    """Faixas começam em 0, não se sobrepõem e só a última fica em aberto."""
    for r in ranges:
        if r.last_range and r.range_to is not None:
            raise BusinessValidationError("range_to deve ser vazio na última faixa")
        if not r.last_range and r.range_to is None:
            raise BusinessValidationError("range_to é obrigatório fora da última faixa")
        if r.range_to is not None and r.range_from >= r.range_to:
            raise BusinessValidationError(
                f"range_from ({r.range_from}) deve ser menor que range_to ({r.range_to})"
            )

    ordered = sorted(ranges, key=lambda r: r.range_from)
    if ordered[0].range_from != 0:
        raise BusinessValidationError("A primeira faixa deve começar em 0")
    last_ranges = [r for r in ordered if r.last_range]
    if len(last_ranges) != 1 or ordered[-1] is not last_ranges[0]:
        raise BusinessValidationError("Só a última faixa (maior início) pode ser a faixa em aberto")
    for prev, curr in zip(ordered, ordered[1:], strict=False):
        # `prev.range_to` nunca é None aqui: só a última faixa fica em aberto.
        if prev.range_to is not None and curr.range_from <= prev.range_to:
            raise BusinessValidationError(
                f"Faixas sobrepostas: [{prev.range_from}-{prev.range_to}] "
                f"e [{curr.range_from}-{curr.range_to}]"
            )
