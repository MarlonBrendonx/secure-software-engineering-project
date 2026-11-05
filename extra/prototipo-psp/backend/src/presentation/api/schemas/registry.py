"""Schemas do cadastro: regras de serviço, clientes e programas.

O status trafega como "Ativo"/"Inativo" (contrato do front, igual ao original) e vira
`EntityStatus` na fronteira: o domínio e o seed continuam com `active`/`inactive`.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.application.use_cases.registry.commands import (
    CreateServiceRuleCommand,
    RangeInput,
    ServiceRuleView,
    UpdateServiceRuleCommand,
)
from src.domain.entities.client import Client
from src.domain.entities.program import ClientProgram
from src.domain.value_objects.billing_status import EntityStatus, RangeType, RuleType

ApiStatus = Literal["Ativo", "Inativo"]

_TO_DOMAIN = {"Ativo": EntityStatus.ACTIVE, "Inativo": EntityStatus.INACTIVE}
_TO_API = {EntityStatus.ACTIVE: "Ativo", EntityStatus.INACTIVE: "Inativo"}

_NAME_MAX = 100


def status_to_api(status: EntityStatus) -> str:
    return _TO_API[status]


def _clean_name(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("Nome do serviço é obrigatório")
    if len(value) > _NAME_MAX:
        raise ValueError(f"Nome do serviço deve ter no máximo {_NAME_MAX} caracteres")
    return value


# ── Entrada ──────────────────────────────────────────────────────────


class RuleRangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range_from: int = Field(..., ge=0)
    range_to: int | None = Field(default=None, ge=0)
    last_range: bool = False
    range_type: RangeType
    value: Decimal = Field(..., gt=0)

    def to_input(self) -> RangeInput:
        return RangeInput(
            self.range_from, self.range_to, self.last_range, self.range_type, self.value
        )


class RuleProgramIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program_uuid: UUID


class ServiceRuleCreate(BaseModel):
    # `forbid`: campo desconhecido é recusado em vez de ignorado, para não passar por
    # engano algo que o servidor não valida (mass assignment).
    model_config = ConfigDict(extra="forbid")

    name: str
    status: ApiStatus = "Ativo"
    rule_type: RuleType
    percentage: Decimal | None = None
    base_value: Decimal | None = Field(default=None, ge=0)
    requires_client_approval: bool = False
    ranges: list[RuleRangeIn] | None = None
    programs: list[RuleProgramIn] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, v: str) -> str | None:
        return _clean_name(v)

    def to_command(self, actor: Any, client_uuid: UUID) -> CreateServiceRuleCommand:
        return CreateServiceRuleCommand(
            actor=actor,
            client_uuid=client_uuid,
            name=self.name,
            rule_type=self.rule_type,
            status=_TO_DOMAIN[self.status],
            percentage=self.percentage,
            base_value=self.base_value,
            requires_client_approval=self.requires_client_approval,
            program_uuids=[p.program_uuid for p in self.programs],
            ranges=[r.to_input() for r in self.ranges or []],
        )


class ServiceRuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(..., ge=1, description="Versão atual, para o bloqueio otimista")
    name: str | None = None
    status: ApiStatus | None = None
    rule_type: RuleType | None = None
    percentage: Decimal | None = None
    base_value: Decimal | None = Field(default=None, ge=0)
    requires_client_approval: bool | None = None
    ranges: list[RuleRangeIn] | None = None
    programs: list[RuleProgramIn] | None = None

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, v: str | None) -> str | None:
        return _clean_name(v)

    def to_command(
        self, actor: Any, client_uuid: UUID, rule_uuid: UUID
    ) -> UpdateServiceRuleCommand:
        return UpdateServiceRuleCommand(
            actor=actor,
            client_uuid=client_uuid,
            rule_uuid=rule_uuid,
            version=self.version,
            name=self.name,
            rule_type=self.rule_type,
            status=_TO_DOMAIN[self.status] if self.status else None,
            percentage=self.percentage,
            base_value=self.base_value,
            requires_client_approval=self.requires_client_approval,
            program_uuids=(
                [p.program_uuid for p in self.programs] if self.programs is not None else None
            ),
            ranges=[r.to_input() for r in self.ranges] if self.ranges is not None else None,
        )


# ── Saída ────────────────────────────────────────────────────────────


def rule_response(view: ServiceRuleView) -> dict[str, Any]:
    rule = view.rule
    return {
        "uuid": rule.uuid,
        "client_uuid": rule.client_uuid,
        "client_name": view.client_name,
        "code": rule.code,
        "name": rule.name,
        "status": status_to_api(rule.status),
        "rule_type": rule.rule_type,
        "percentage": rule.percentage,
        "base_value": rule.base_value,
        "requires_client_approval": rule.requires_client_approval,
        "ranges": [
            {
                "uuid": r.uuid,
                "range_from": r.range_from,
                "range_to": r.range_to,
                "last_range": r.last_range,
                "range_type": r.range_type,
                "value": r.value,
            }
            for r in sorted(rule.ranges, key=lambda r: r.range_from)
        ],
        "programs": [
            {"uuid": p.uuid, "program_uuid": p.uuid, "program_name": p.name} for p in rule.programs
        ],
        "has_billing_items": view.has_billing_items,
        "version": rule.version,
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat(),
    }


def client_response(client: Client) -> dict[str, Any]:
    return {
        "uuid": client.uuid,
        "client_code": client.code,
        "name": client.name,
        "cnpj": client.cnpj,
        "status": status_to_api(client.status),
    }


def client_summary_response(client: Client) -> dict[str, Any]:
    return {"uuid": client.uuid, "client_code": client.code, "name": client.name}


def program_response(program: ClientProgram) -> dict[str, Any]:
    return {
        "uuid": program.uuid,
        "client_uuid": program.client_uuid,
        "name": program.name,
        "status": status_to_api(program.status),
    }
