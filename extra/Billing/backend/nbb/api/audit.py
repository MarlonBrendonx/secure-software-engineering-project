"""Consulta da trilha de auditoria (gerência, controladoria e auditoria externa)."""
import csv
import io
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from nbb.api.deps import Current, require
from nbb.core import audit
from nbb.core.permissions import P
from nbb.db import get_db, new_session
from nbb.models import AuditEvent

router = APIRouter(prefix="/audit-events", tags=["auditoria"])


class AuditEventOut(BaseModel):
    seq: int
    occurred_at: datetime
    actor_id: uuid.UUID | None
    actor_login: str | None
    via_delegation_id: uuid.UUID | None
    action: str
    entity: str | None
    entity_id: str | None
    before: dict | None
    after: dict | None
    ip: str | None
    request_id: str | None
    hash: str


class AuditPage(BaseModel):
    items: list[AuditEventOut]
    next_before_seq: int | None


class ChainStatus(BaseModel):
    intact: bool
    events_checked: int
    broken_seq: int | None = None
    reason: str | None = None


def _query(entity, entity_id, actor_id, action, date_from, date_to):
    stmt = select(AuditEvent)
    if entity:
        stmt = stmt.where(AuditEvent.entity == entity)
    if entity_id:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if action:
        stmt = stmt.where(AuditEvent.action.like(action.replace("*", "%")))
    if date_from:
        stmt = stmt.where(AuditEvent.occurred_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditEvent.occurred_at < date_to)
    return stmt


@router.get("", response_model=AuditPage, summary="Consulta eventos (mais recentes primeiro)")
def list_events(
    entity: str | None = None, entity_id: str | None = None, actor_id: uuid.UUID | None = None,
    action: str | None = Query(default=None, description="Aceita * como curinga, ex.: auth.*"),
    date_from: datetime | None = None, date_to: datetime | None = None,
    before_seq: int | None = None, limit: int = Query(default=100, ge=1, le=500),
    current: Current = Depends(require(P.AUDIT_READ)), db: Session = Depends(get_db),
):
    stmt = _query(entity, entity_id, actor_id, action, date_from, date_to)
    if before_seq:
        stmt = stmt.where(AuditEvent.seq < before_seq)
    rows = list(db.scalars(stmt.order_by(AuditEvent.seq.desc()).limit(limit)))
    # A própria consulta à auditoria também fica registrada.
    audit.record(db, "audit.query", detail={"entity": entity, "entity_id": entity_id,
                                            "actor_id": actor_id, "action": action})
    db.commit()
    return AuditPage(
        items=[AuditEventOut.model_validate(r, from_attributes=True) for r in rows],
        next_before_seq=rows[-1].seq if len(rows) == limit else None,
    )


@router.get("/verify", response_model=ChainStatus, summary="Confere a integridade da cadeia de hashes")
def verify_chain(current: Current = Depends(require(P.AUDIT_READ)), db: Session = Depends(get_db)):
    broken = db.execute(text("SELECT broken_seq, reason FROM audit_verify_chain(1)")).first()
    total = db.execute(text("SELECT count(*) FROM audit_event")).scalar_one()
    audit.record(db, "audit.verify", detail={"intact": broken is None})
    db.commit()
    if broken:
        return ChainStatus(intact=False, events_checked=total, broken_seq=broken[0], reason=broken[1])
    return ChainStatus(intact=True, events_checked=total)


@router.get("/export", summary="Exporta eventos filtrados em CSV")
def export_csv(
    entity: str | None = None, entity_id: str | None = None, actor_id: uuid.UUID | None = None,
    action: str | None = None, date_from: datetime | None = None, date_to: datetime | None = None,
    current: Current = Depends(require(P.AUDIT_READ)), db: Session = Depends(get_db),
):
    stmt = _query(entity, entity_id, actor_id, action, date_from, date_to).order_by(AuditEvent.seq)
    audit.record(db, "audit.export", detail={"entity": entity, "entity_id": entity_id,
                                             "actor_id": actor_id, "action": action})
    db.commit()
    cols = ["seq", "occurred_at", "actor_login", "actor_id", "via_delegation_id", "action",
            "entity", "entity_id", "before", "after", "ip", "request_id", "prev_hash", "hash"]

    def cell(v):
        if isinstance(v, dict):
            return json.dumps(v, ensure_ascii=False)
        if isinstance(v, datetime):
            return v.isoformat()
        return "" if v is None else v

    def rows():
        # Sessão própria: a da requisição já foi encerrada quando o stream é lido.
        stream_db = new_session()
        buf = io.StringIO()
        w = csv.writer(buf)
        try:
            w.writerow(cols)
            yield buf.getvalue()
            for ev in stream_db.scalars(stmt.execution_options(yield_per=1000)):
                buf.seek(0)
                buf.truncate()
                w.writerow([cell(getattr(ev, c)) for c in cols])
                yield buf.getvalue()
        finally:
            stream_db.close()

    return StreamingResponse(rows(), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": 'attachment; filename="auditoria.csv"'})
