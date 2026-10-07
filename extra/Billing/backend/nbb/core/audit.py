"""Registro automático na trilha de auditoria.

Um listener `before_flush` captura toda inserção, alteração e exclusão de
modelos marcados com ``__audited__`` e grava um AuditEvent na mesma
transação: se a alteração for gravada, o registro também é; se for
desfeita, nenhum dos dois fica.

O responsável vem de ``session.info["actor"]``, preenchido pela camada de
autenticação a cada requisição.
"""
import enum
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from nbb.models.audit import AuditEvent
from nbb.models.base import Base

REDACTED = "[redacted]"


@dataclass
class Actor:
    user_id: uuid.UUID | None
    login: str | None
    ip: str | None = None
    request_id: str | None = None
    via_delegation_id: uuid.UUID | None = None


SYSTEM_ACTOR = Actor(user_id=None, login="system")


def set_actor(db: Session, actor: Actor) -> None:
    db.info["actor"] = actor


def get_actor(db: Session) -> Actor:
    return db.info.get("actor") or SYSTEM_ACTOR


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return str(value)


def _fill_pk_defaults(obj: Base) -> None:
    """Gera já no flush as chaves com default Python (uuid4), para que o
    evento de criação aponte para o id real do registro."""
    for col in inspect(obj).mapper.primary_key:
        key = inspect(obj).mapper.get_property_by_column(col).key
        if getattr(obj, key) is None and col.default is not None and col.default.is_callable:
            setattr(obj, key, col.default.arg(None))


def _entity_id(obj: Base) -> str:
    identity = inspect(obj).identity
    if identity is None:
        mapper = inspect(obj).mapper
        identity = tuple(getattr(obj, col.key) for col in mapper.primary_key)
    return ",".join(str(v) for v in identity)


def _columns(obj: Base):
    return inspect(obj).mapper.column_attrs


def _snapshot(obj: Base) -> dict:
    redact = obj.__audit_redact__
    out = {}
    for attr in _columns(obj):
        value = getattr(obj, attr.key)
        out[attr.key] = REDACTED if (attr.key in redact and value is not None) else _jsonable(value)
    return out


def _diff(obj: Base) -> tuple[dict, dict]:
    state = inspect(obj)
    redact = obj.__audit_redact__
    before, after = {}, {}
    for attr in _columns(obj):
        hist = state.attrs[attr.key].history
        if not hist.has_changes():
            continue
        old = hist.deleted[0] if hist.deleted else None
        new = hist.added[0] if hist.added else None
        if old == new:
            continue
        if attr.key in redact:
            before[attr.key] = REDACTED if old is not None else None
            after[attr.key] = REDACTED if new is not None else None
        else:
            before[attr.key] = _jsonable(old)
            after[attr.key] = _jsonable(new)
    return before, after


def _event(db: Session, action: str, entity: str | None, entity_id: str | None,
           before: dict | None, after: dict | None) -> AuditEvent:
    actor = get_actor(db)
    return AuditEvent(
        actor_id=actor.user_id,
        actor_login=actor.login,
        via_delegation_id=actor.via_delegation_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        before=before,
        after=after,
        ip=actor.ip,
        request_id=actor.request_id,
    )


def record(db: Session, action: str, *, entity: str | None = None, entity_id: Any = None,
           detail: dict | None = None) -> None:
    """Registra um evento que não é alteração de linha (login, download, consulta…)."""
    db.add(_event(db, action, entity, None if entity_id is None else str(entity_id), None,
                  _jsonable(detail) if detail else None))


@event.listens_for(Session, "before_flush")
def _audit_before_flush(db: Session, flush_context, instances) -> None:
    events: list[AuditEvent] = []
    for obj in list(db.new):
        if isinstance(obj, Base) and obj.__audited__:
            _fill_pk_defaults(obj)
            events.append(_event(db, "create", obj.__tablename__, _entity_id(obj), None, _snapshot(obj)))
    for obj in list(db.dirty):
        if isinstance(obj, Base) and obj.__audited__ and db.is_modified(obj, include_collections=False):
            before, after = _diff(obj)
            if after or before:
                events.append(_event(db, "update", obj.__tablename__, _entity_id(obj), before, after))
    for obj in list(db.deleted):
        if isinstance(obj, Base) and obj.__audited__:
            events.append(_event(db, "delete", obj.__tablename__, _entity_id(obj), _snapshot(obj), None))
    for ev in events:
        db.add(ev)
