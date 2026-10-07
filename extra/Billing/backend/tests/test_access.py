"""Perfis, substituições em férias e pedidos de acesso."""
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from nbb import db as dbmod
from nbb.models import AuditEvent
from tests.conftest import track, create_user, unique

ME = "/api/v1/me"


def iso(dt):
    return dt.isoformat()


def test_analyst_cannot_manage_users(login_as):
    api, _ = login_as("analyst")
    r = api.get("/api/v1/users")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "forbidden"


def test_admin_has_no_approval_or_audit_permissions(login_as):
    """Segregação: quem administra usuários não aprova lançamentos nem lê a auditoria."""
    api, _ = login_as("admin")
    perms = api.get(ME).json()["permissions"]
    assert "users.manage" in perms
    assert "entries.approve" not in perms and "audit.read" not in perms


def test_admin_cannot_change_own_roles(login_as):
    api, admin = login_as("admin")
    r = api.put(f"/api/v1/users/{admin.id}/roles", json={"roles": ["admin", "manager"]})
    assert r.status_code == 403


def test_role_change_is_effective_and_audited(login_as):
    api, admin = login_as("admin")
    target = create_user(unique("t"), roles=("analyst",))
    r = api.put(f"/api/v1/users/{target.id}/roles", json={"roles": ["manager"]})
    assert r.status_code == 200 and r.json()["roles"] == ["manager"]
    db = track(dbmod.new_session())
    events = db.scalars(select(AuditEvent).where(
        AuditEvent.entity == "user_role", AuditEvent.entity_id.like(f"{target.id}%"),
        AuditEvent.actor_id == admin.id)).all()
    actions = {(e.action, (e.after or e.before)["role_code"]) for e in events}
    assert ("delete", "analyst") in actions and ("create", "manager") in actions


def test_admin_preregisters_sso_user_by_email(login_as):
    api, _ = login_as("admin")
    r = api.post("/api/v1/users", json={"login": unique("ana"), "name": "Ana Lima",
                                         "email": "Ana.Lima@Gmail.com", "roles": ["analyst"]})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["source"] == "sso" and body["email"] == "ana.lima@gmail.com"
    assert body["mfa_enrolled"] is False and body["sso_providers"] == []
    # Dois usuários ativos com o mesmo e-mail tornariam o vínculo do SSO ambíguo.
    dup = api.post("/api/v1/users", json={"login": unique("ana"), "name": "Outra", "email": "ana.lima@gmail.com"})
    assert dup.status_code == 409 and dup.json()["detail"]["code"] == "email_taken"


def test_create_local_user_sends_password_link(login_as, mailer):
    api, _ = login_as("admin")
    login = unique("ext")
    r = api.post("/api/v1/users", json={"login": login, "name": "Auditor Externo",
                                         "email": "ext@auditoria-externa.com.br", "source": "local", "roles": ["auditor"]})
    assert r.status_code == 201, r.text
    assert mailer.sent[-1][0] == "ext@auditoria-externa.com.br" and "token=" in mailer.sent[-1][2]


def _delegate(admin_api, titular, substitute, role="manager", start=None, end=None):
    now = datetime.now(UTC)
    return admin_api.post("/api/v1/delegations", json={
        "titular_id": str(titular.id), "substitute_id": str(substitute.id), "role_code": role,
        "starts_at": iso(start or now - timedelta(minutes=1)),
        "ends_at": iso(end or now + timedelta(days=15)),
        "justification": "Férias do titular conforme memorando 12/2026",
    })


def test_vacation_substitute_gets_permissions_logged_in_own_name(login_as):
    admin, _ = login_as("admin")
    titular = create_user(unique("tit"), roles=("manager",))
    sub_api, substitute = login_as("analyst")
    assert "audit.read" not in sub_api.get(ME).json()["permissions"]

    r = _delegate(admin, titular, substitute)
    assert r.status_code == 201, r.text
    delegation_id = r.json()["id"]

    me = sub_api.get(ME).json()
    assert "audit.read" in me["permissions"] and me["delegations"][0]["id"] == delegation_id
    assert sub_api.get("/api/v1/audit-events").status_code == 200

    db = track(dbmod.new_session())
    ev = db.scalars(select(AuditEvent).where(AuditEvent.action == "audit.query",
                                             AuditEvent.actor_id == substitute.id)).one()
    assert ev.actor_login == substitute.login            # no nome do substituto
    assert str(ev.via_delegation_id) == delegation_id    # com referência à delegação

    # Encerrada a substituição, a permissão some na hora.
    assert admin.post(f"/api/v1/delegations/{delegation_id}/revoke").status_code == 200
    assert sub_api.get("/api/v1/audit-events").status_code == 403


def test_delegation_outside_window_grants_nothing(login_as):
    admin, _ = login_as("admin")
    titular = create_user(unique("tit"), roles=("manager",))
    sub_api, substitute = login_as("analyst")
    now = datetime.now(UTC)
    r = _delegate(admin, titular, substitute, start=now + timedelta(days=2), end=now + timedelta(days=10))
    assert r.status_code == 201
    assert "audit.read" not in sub_api.get(ME).json()["permissions"]


def test_delegation_rules(login_as):
    admin, admin_user = login_as("admin")
    titular = create_user(unique("tit"), roles=("manager",))
    substitute = create_user(unique("sub"), roles=("analyst",))
    now = datetime.now(UTC)
    # Titular precisa ter o perfil delegado.
    assert _delegate(admin, titular, substitute, role="admin").json()["detail"]["code"] == "role_not_held"
    # Prazo máximo configurável (60 dias por padrão).
    assert _delegate(admin, titular, substitute, end=now + timedelta(days=90)).json()["detail"]["code"] == "too_long"
    # Ninguém concede a si mesmo.
    assert _delegate(admin, titular, admin_user).status_code == 403
    # Data de término obrigatória e no futuro.
    r = _delegate(admin, titular, substitute, start=now - timedelta(days=5), end=now - timedelta(days=1))
    assert r.status_code == 422


def test_access_request_flow(login_as, new_api):
    admin, _ = login_as("admin")
    newcomer_api, newcomer = login_as()  # sem perfil
    assert newcomer_api.get(ME).json()["permissions"] == ["access.request"]

    r = newcomer_api.post("/api/v1/access-requests", json={"role_code": "analyst",
                                                           "justification": "Entrei na equipe de faturamento"})
    assert r.status_code == 201
    req_id = r.json()["id"]
    assert newcomer_api.post("/api/v1/access-requests", json={
        "role_code": "analyst", "justification": "de novo, mesmo pedido"}).status_code == 409

    assert any(a["id"] == req_id for a in admin.get("/api/v1/access-requests").json())
    r = admin.post(f"/api/v1/access-requests/{req_id}/decision", json={"approve": True, "comment": "ok"})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert "entries.write" in newcomer_api.get(ME).json()["permissions"]


def test_nobody_decides_own_access_request(login_as):
    admin, _ = login_as("admin")
    r = admin.post("/api/v1/access-requests", json={"role_code": "analyst", "justification": "quero lançar"})
    assert r.status_code == 201
    r = admin.post(f"/api/v1/access-requests/{r.json()['id']}/decision", json={"approve": True})
    assert r.status_code == 403
