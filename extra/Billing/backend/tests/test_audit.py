"""Trilha de auditoria: registro automático, imutabilidade e detecção de adulteração."""
import json
import threading

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from nbb import db as dbmod
from nbb.core.audit import Actor, record, set_actor
from nbb.models import AuditEvent, User
from tests.conftest import app_engine, create_user, owner_engine, track, unique


def latest(db, **filters):
    stmt = select(AuditEvent)
    for k, v in filters.items():
        stmt = stmt.where(getattr(AuditEvent, k) == v)
    return db.scalars(stmt.order_by(AuditEvent.seq.desc())).first()


def test_changes_are_recorded_automatically_with_before_and_after(login_as):
    api, admin = login_as("admin")
    assert api.put("/api/v1/settings/approval.double_threshold", json={"value": "75000.00"}).status_code == 200
    db = track(dbmod.new_session())
    ev = latest(db, entity="setting", entity_id="approval.double_threshold")
    assert ev.action == "update" and ev.actor_id == admin.id
    assert ev.before["value"] == "50000.00" and ev.after["value"] == "75000.00"
    assert ev.ip and ev.request_id
    api.put("/api/v1/settings/approval.double_threshold", json={"value": "50000.00"})


def test_invalid_setting_value_rejected(login_as):
    api, _ = login_as("admin")
    r = api.put("/api/v1/settings/approval.double_threshold", json={"value": "-1"})
    assert r.status_code == 422


def test_password_hash_never_appears_in_audit():
    user = create_user(unique("loc"), source="local", password="Faturamento#2026")
    db = track(dbmod.new_session())
    ev = latest(db, entity="app_user", entity_id=str(user.id))
    assert ev.after["password_hash"] == "[redacted]"


def test_app_database_user_cannot_update_delete_or_truncate_audit():
    eng = app_engine()
    for sql in ("UPDATE audit_event SET action = 'x'", "DELETE FROM audit_event", "TRUNCATE audit_event"):
        with eng.connect() as conn, pytest.raises(ProgrammingError, match="permission denied"):
            conn.execute(text(sql))
    eng.dispose()


def test_even_schema_owner_is_blocked_by_trigger():
    """Nem administradores apagam a auditoria: o trigger barra até o dono do schema."""
    eng = owner_engine()
    for sql in ("UPDATE audit_event SET action = 'x' WHERE seq = 1",
                "DELETE FROM audit_event WHERE seq = 1", "TRUNCATE audit_event"):
        with eng.connect() as conn, pytest.raises(DBAPIError) as exc:
            conn.execute(text("SET lock_timeout = '5s'"))
            conn.execute(text(sql))
        assert exc.value.orig.sqlstate == "NB001"
    eng.dispose()


def test_rolled_back_change_leaves_no_audit_record():
    db = track(dbmod.new_session())
    set_actor(db, Actor(user_id=None, login="t"))
    login = unique("rb")
    db.add(User(login=login, name="X", source="sso"))
    db.flush()
    db.rollback()
    found = db.scalar(select(AuditEvent.seq).where(AuditEvent.after["login"].astext == login))
    assert found is None


def test_chain_is_linear_under_concurrent_writes(login_as):
    errors = []

    def writer():
        try:
            db = track(dbmod.new_session())
            set_actor(db, Actor(user_id=None, login="concorrencia"))
            for _ in range(15):
                record(db, "test.concurrent")
                db.commit()
            db.close()
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=writer) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    api, _ = login_as("auditor")
    status = api.get("/api/v1/audit-events/verify").json()
    assert status["intact"] is True, status


def test_tampering_by_dba_is_detected(login_as):
    api, _ = login_as("auditor")
    assert api.get("/api/v1/audit-events/verify").json()["intact"] is True

    eng = owner_engine()
    with eng.begin() as conn:
        seq, original = conn.execute(text(
            "SELECT seq, action FROM audit_event WHERE action = 'auth.login' ORDER BY seq LIMIT 1")).one()
        # Um DBA desliga o trigger e adultera um registro…
        conn.execute(text("ALTER TABLE audit_event DISABLE TRIGGER audit_event_no_update_delete"))
        conn.execute(text("UPDATE audit_event SET action = 'auth.logout' WHERE seq = :s"), {"s": seq})
        conn.execute(text("ALTER TABLE audit_event ENABLE TRIGGER audit_event_no_update_delete"))
    try:
        status = api.get("/api/v1/audit-events/verify").json()
        assert status == {**status, "intact": False, "broken_seq": seq, "reason": "content_altered"}
    finally:
        with eng.begin() as conn:
            conn.execute(text("ALTER TABLE audit_event DISABLE TRIGGER audit_event_no_update_delete"))
            conn.execute(text("UPDATE audit_event SET action = :a WHERE seq = :s"), {"a": original, "s": seq})
            conn.execute(text("ALTER TABLE audit_event ENABLE TRIGGER audit_event_no_update_delete"))
        eng.dispose()
    assert api.get("/api/v1/audit-events/verify").json()["intact"] is True


def test_deleted_event_is_detected(login_as):
    api, _ = login_as("auditor")
    eng = owner_engine()
    with eng.begin() as conn:
        row = conn.execute(text("SELECT * FROM audit_event ORDER BY seq DESC OFFSET 3 LIMIT 1")).mappings().one()
        conn.execute(text("ALTER TABLE audit_event DISABLE TRIGGER audit_event_no_update_delete"))
        conn.execute(text("DELETE FROM audit_event WHERE seq = :s"), {"s": row["seq"]})
    try:
        status = api.get("/api/v1/audit-events/verify").json()
        assert status["intact"] is False and status["broken_seq"] == row["seq"]
    finally:
        with eng.begin() as conn:
            conn.execute(text("ALTER TABLE audit_event DISABLE TRIGGER audit_event_chain"))
            values = {k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in row.items()}
            placeholders = ", ".join(f"CAST(:{k} AS jsonb)" if k in ("before", "after") else f":{k}" for k in row.keys())
            conn.execute(text(f"INSERT INTO audit_event ({', '.join(row.keys())}) VALUES ({placeholders})"), values)
            conn.execute(text("ALTER TABLE audit_event ENABLE TRIGGER audit_event_chain"))
            conn.execute(text("ALTER TABLE audit_event ENABLE TRIGGER audit_event_no_update_delete"))
        eng.dispose()


def test_audit_query_requires_permission_and_is_itself_audited(login_as):
    analyst, _ = login_as("analyst")
    assert analyst.get("/api/v1/audit-events").status_code == 403
    auditor, who = login_as("auditor")
    page = auditor.get("/api/v1/audit-events", params={"action": "auth.*", "limit": 5}).json()
    assert len(page["items"]) <= 5 and all(i["action"].startswith("auth.") for i in page["items"])
    db = track(dbmod.new_session())
    assert latest(db, action="audit.query", actor_id=who.id) is not None


def test_audit_csv_export(login_as):
    api, who = login_as("auditor")
    r = api.get("/api/v1/audit-events/export", params={"actor_id": str(who.id)})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("seq,occurred_at,actor_login") and len(lines) >= 2
