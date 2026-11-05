"""Serialização das entidades em JSON.

Decimal e UUID viram texto: assim o valor monetário não passa por float e não perde precisão.
"""

from __future__ import annotations

import json
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from src.domain.entities.audit import AuditEvent
from src.domain.entities.billing import Billing, BillingHistory, BillingItem, BillingItemHistory
from src.domain.entities.client import Client
from src.domain.entities.program import ClientProgram
from src.domain.entities.service_rule import Program, ServiceRule, ServiceRuleRange
from src.domain.entities.session import AuthSession
from src.domain.entities.user import User, UserScope
from src.domain.value_objects.billing_status import BillingStatus, EntityStatus, RangeType, RuleType
from src.domain.value_objects.user_role import UserRole

# Campos de leitura do item, montados na resposta e nunca persistidos.
_ITEM_TRANSIENT = {"rule_type", "requires_client_approval", "service_rule_name", "programs"}


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (set, frozenset)):
        return sorted(_jsonable(v) for v in value)
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def dumps(value: Any) -> str:
    return json.dumps(_jsonable(value), ensure_ascii=False)


def _dec(v: Any) -> Decimal | None:
    return None if v is None else Decimal(v)


def _dt(v: str) -> datetime:
    return datetime.fromisoformat(v)


# ── Cliente e regra ──────────────────────────────────────────────────


def client_from_json(raw: str | bytes) -> Client:
    d = json.loads(raw)
    return Client(
        uuid=UUID(d["uuid"]),
        version=d["version"],
        created_at=_dt(d["created_at"]),
        updated_at=_dt(d["updated_at"]),
        name=d["name"],
        cnpj=d["cnpj"],
        status=EntityStatus(d["status"]),
        has_client_approval_contract=d["has_client_approval_contract"],
        code=d.get("code", ""),
    )


def program_from_json(raw: str | bytes) -> ClientProgram:
    d = json.loads(raw)
    return ClientProgram(
        uuid=UUID(d["uuid"]),
        version=d["version"],
        created_at=_dt(d["created_at"]),
        updated_at=_dt(d["updated_at"]),
        client_uuid=UUID(d["client_uuid"]),
        name=d["name"],
        status=EntityStatus(d["status"]),
    )


def rule_from_json(raw: str | bytes) -> ServiceRule:
    d = json.loads(raw)
    return ServiceRule(
        uuid=UUID(d["uuid"]),
        version=d["version"],
        created_at=_dt(d["created_at"]),
        updated_at=_dt(d["updated_at"]),
        client_uuid=UUID(d["client_uuid"]),
        name=d["name"],
        code=d["code"],
        rule_type=RuleType(d["rule_type"]),
        status=EntityStatus(d["status"]),
        percentage=_dec(d["percentage"]),
        base_value=_dec(d["base_value"]),
        requires_client_approval=d["requires_client_approval"],
        programs=[Program(uuid=UUID(p["uuid"]), name=p["name"]) for p in d["programs"]],
        ranges=[
            ServiceRuleRange(
                range_from=r["range_from"],
                range_to=r["range_to"],
                last_range=r["last_range"],
                range_type=RangeType(r["range_type"]),
                value=Decimal(r["value"]),
                uuid=UUID(r["uuid"]) if r.get("uuid") else None,
            )
            for r in d["ranges"]
        ],
    )


# ── Faturamento e lançamento ─────────────────────────────────────────


def billing_from_json(raw: str | bytes) -> Billing:
    d = json.loads(raw)
    return Billing(
        uuid=UUID(d["uuid"]),
        version=d["version"],
        created_at=_dt(d["created_at"]),
        updated_at=_dt(d["updated_at"]),
        client_uuid=UUID(d["client_uuid"]),
        service_rule_uuid=UUID(d["service_rule_uuid"]),
        reference_year=d["reference_year"],
        reference_month=d["reference_month"],
        total_value=Decimal(d["total_value"]),
    )


def item_to_json(item: BillingItem) -> str:
    data = {f.name: getattr(item, f.name) for f in fields(item) if f.name not in _ITEM_TRANSIENT}
    return dumps(data)


def item_from_json(raw: str | bytes) -> BillingItem:
    d = json.loads(raw)
    return BillingItem(
        uuid=UUID(d["uuid"]),
        version=d["version"],
        created_at=_dt(d["created_at"]),
        updated_at=_dt(d["updated_at"]),
        billing_uuid=UUID(d["billing_uuid"]),
        service_rule_uuid=UUID(d["service_rule_uuid"]),
        quantity=Decimal(d["quantity"]),
        unit_value=Decimal(d["unit_value"]),
        total_value=Decimal(d["total_value"]),
        base_value=_dec(d["base_value"]),
        po_number=d["po_number"],
        invoice_description=d["invoice_description"],
        notes=d["notes"],
        billing_month=d["billing_month"],
        billing_year=d["billing_year"],
        competence_month=d["competence_month"],
        competence_year=d["competence_year"],
        status=BillingStatus(d["status"]),
        rejection_reason=d["rejection_reason"],
    )


def item_history_from_json(raw: str | bytes) -> BillingItemHistory:
    d = json.loads(raw)
    return BillingItemHistory(
        uuid=UUID(d["uuid"]),
        billing_item_uuid=UUID(d["billing_item_uuid"]),
        action=d["action"],
        previous_status=BillingStatus(d["previous_status"]) if d["previous_status"] else None,
        new_status=BillingStatus(d["new_status"]),
        notes=d["notes"],
        changes=d["changes"],
        changed_by=d["changed_by"],
        created_at=_dt(d["created_at"]),
    )


def billing_history_from_json(raw: str | bytes) -> BillingHistory:
    d = json.loads(raw)
    return BillingHistory(
        uuid=UUID(d["uuid"]),
        billing_uuid=UUID(d["billing_uuid"]),
        action=d["action"],
        previous_status=d["previous_status"],
        new_status=d["new_status"],
        notes=d["notes"],
        changes=d["changes"],
        changed_by=d["changed_by"],
        created_at=_dt(d["created_at"]),
    )


# ── Segurança ────────────────────────────────────────────────────────


def user_from_json(raw: str | bytes) -> User:
    d = json.loads(raw)
    return User(
        username=d["username"],
        role=UserRole(d["role"]),
        display_name=d["display_name"],
        email=d["email"],
        scope=UserScope(
            clients=frozenset(d["scope"]["clients"]),
            periods=frozenset(d["scope"]["periods"]),
        ),
    )


def session_from_json(raw: str | bytes) -> AuthSession:
    d = json.loads(raw)
    return AuthSession(
        sid=d["sid"], username=d["username"], amr=d["amr"], created_at=_dt(d["created_at"])
    )


def audit_from_json(raw: str | bytes) -> AuditEvent:
    d = json.loads(raw)
    d["created_at"] = _dt(d["created_at"])
    return AuditEvent(**d)
