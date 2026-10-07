"""Verificação em duas etapas com aplicativo autenticador (TOTP)."""
import pytest
from sqlalchemy import select

from nbb import db as dbmod
from nbb.api.deps import ACCESS_COOKIE
from nbb.core import totp
from nbb.core.crypto import DataCipher, generate_key
from nbb.models import AuditEvent, AuthSession, UserMfa
from tests.conftest import (
    DATA_KEY, STRONG_PASSWORD, code_for, create_user, enroll_totp, landing, sso_login, track, unique,
)

ME = "/api/v1/me"
VERIFY = "/api/v1/auth/mfa/verify"
LOCAL_LOGIN = "/api/v1/auth/local/login"


def start_login(new_api, user):
    api = new_api()
    assert landing(sso_login(api, user.email)) == "/login/verificacao"
    return api


def events(db, action, user_id):
    return db.scalars(select(AuditEvent).where(AuditEvent.action == action,
                                               AuditEvent.entity_id == str(user_id))).all()


# ------------------------------------------------------------------ unidades
def test_totp_accepts_one_step_of_clock_drift_only():
    secret = totp.new_secret()
    now = totp.current_step()
    for offset in (-1, 0, 1):
        assert totp.match_step(secret, totp.code_at(secret, now + offset)) == now + offset
    for offset in (-3, -2, 2, 3):
        assert totp.match_step(secret, totp.code_at(secret, now + offset)) is None
    assert totp.match_step(secret, "12345") is None and totp.match_step(secret, "abcdef") is None


def test_secret_encryption_supports_key_rotation():
    old = DataCipher([DATA_KEY])
    token = old.encrypt("SEGREDO")
    rotated = DataCipher([generate_key(), DATA_KEY])  # chave nova na frente, antiga ainda decifra
    assert rotated.decrypt(token) == "SEGREDO"
    # Depois de recifrar com a chave nova, a antiga pode ser removida.
    new_only = DataCipher([rotated_key := generate_key()])
    assert DataCipher([rotated_key, DATA_KEY]).rotate(token) != token
    assert new_only.decrypt(DataCipher([rotated_key, DATA_KEY]).rotate(token)) == "SEGREDO"
    with pytest.raises(ValueError):
        DataCipher([generate_key()]).decrypt(token)


# ------------------------------------------------------------------ cadastro
def test_enrollment_with_qr_code(login_as):
    api, user = login_as("analyst", mfa=False)
    assert api.get("/api/v1/auth/mfa").json() == {
        "enrolled": False, "required": False, "session_verified": False, "recovery_codes_left": 0}

    setup = api.post("/api/v1/auth/mfa/totp/setup").json()
    assert setup["otpauth_uri"].startswith("otpauth://totp/Network%20Billing:")
    assert "issuer=Network%20Billing" in setup["otpauth_uri"]
    assert setup["qr_svg"].startswith("data:image/svg+xml")
    secret = setup["secret"]

    # Segredo guardado cifrado; na auditoria aparece mascarado.
    db = track(dbmod.new_session())
    stored = db.get(UserMfa, user.id).totp_secret_enc
    assert secret not in stored and DataCipher([DATA_KEY]).decrypt(stored) == secret
    created = events(db, "create", user.id)
    assert any(e.entity == "user_mfa" and e.after["totp_secret_enc"] == "[redacted]" for e in created)

    # Ainda não vale: nada muda no login até confirmar.
    assert api.get("/api/v1/auth/mfa").json()["enrolled"] is False

    wrong = api.post("/api/v1/auth/mfa/totp/confirm", json={"code": "000000"})
    assert wrong.status_code == 422 and wrong.json()["detail"]["code"] == "invalid_code"

    old_token = api.cookies.get(ACCESS_COOKIE)
    r = api.post("/api/v1/auth/mfa/totp/confirm", json={"code": code_for(secret)})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["recovery_codes"]) == 10 and len(set(body["recovery_codes"])) == 10
    assert body["me"]["mfa"] is True and body["me"]["mfa_enrolled"] is True

    # A sessão foi trocada por uma nova; o token antigo não vale mais.
    assert api.get(ME).json()["mfa"] is True
    api.cookies.set(ACCESS_COOKIE, old_token)
    assert api.get(ME).status_code == 401


def test_setup_twice_is_rejected_once_enrolled(login_as):
    api, _ = login_as("analyst")
    r = api.post("/api/v1/auth/mfa/totp/setup")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "already_enrolled"


def test_manager_must_enroll_and_gets_permissions_right_after(login_as):
    api, _ = login_as("manager", mfa=False)
    me = api.get(ME).json()
    assert me["mfa_enrollment_required"] is True
    assert me["roles_pending_mfa"] == ["manager"] and "manager" not in me["roles"]
    assert "entries.approve" in me["permissions_requiring_mfa"]
    r = api.get("/api/v1/audit-events")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "mfa_required"

    secret = api.post("/api/v1/auth/mfa/totp/setup").json()["secret"]
    assert api.post("/api/v1/auth/mfa/totp/confirm", json={"code": code_for(secret)}).status_code == 200
    me = api.get(ME).json()
    assert me["mfa_enrollment_required"] is False and "entries.approve" in me["permissions"]
    assert me["roles_pending_mfa"] == [] and "manager" in me["roles"]
    assert api.get("/api/v1/audit-events").status_code == 200


# ------------------------------------------------------------------ login em duas etapas
def test_sso_login_requires_code_before_any_session_exists(new_api):
    user = create_user(unique("u"), roles=("analyst",))
    secret = enroll_totp(user)
    api = new_api()
    r = sso_login(api, user.email)
    assert landing(r) == "/login/verificacao"
    cookies = r.headers.get_list("set-cookie")
    assert not any(c.startswith(ACCESS_COOKIE + "=") for c in cookies)
    ticket = next(c for c in cookies if c.startswith("nbb_mfa="))
    assert "HttpOnly" in ticket and "Path=/api/v1/auth/mfa" in ticket and "SameSite=strict" in ticket
    assert api.get(ME).status_code == 401

    bad = api.post(VERIFY, json={"code": "000000"})
    assert bad.status_code == 401 and bad.json()["detail"]["attempts_left"] == 4
    ok = api.post(VERIFY, json={"code": code_for(secret)})
    assert ok.status_code == 200 and ok.json()["status"] == "authenticated"
    assert ok.json()["me"]["mfa"] is True
    # Ticket é de uso único.
    assert api.post(VERIFY, json={"code": code_for(secret, 1)}).json()["detail"]["code"] == "mfa_challenge_expired"


def test_same_code_cannot_be_used_twice(login_as, new_api):
    _, user = login_as("analyst")
    api = start_login(new_api, user)
    replay = api.post(VERIFY, json={"code": user.totp_used_code})
    assert replay.status_code == 401 and replay.json()["detail"]["code"] == "invalid_code"
    assert api.post(VERIFY, json={"code": code_for(user.totp_secret, 1)}).status_code == 200


def test_wrong_codes_burn_the_ticket_and_lock_the_user(new_api):
    user = create_user(unique("u"), roles=("analyst",))
    secret = enroll_totp(user)
    api = start_login(new_api, user)
    for _ in range(4):
        assert api.post(VERIFY, json={"code": "000000"}).json()["detail"]["code"] == "invalid_code"
    last = api.post(VERIFY, json={"code": "000000"})
    assert last.json()["detail"]["code"] == "mfa_challenge_expired"
    assert api.post(VERIFY, json={"code": code_for(secret)}).status_code == 401

    # Fazer login de novo não reinicia a contagem: o bloqueio é por usuário.
    again = start_login(new_api, user)
    r = again.post(VERIFY, json={"code": code_for(secret)})
    assert r.status_code == 429 and r.json()["detail"]["code"] == "mfa_locked"
    db = track(dbmod.new_session())
    assert db.scalars(select(AuditEvent).where(AuditEvent.action == "auth.mfa_failed")).first() is not None


def test_pending_session_cannot_be_used_or_refreshed(new_api):
    user = create_user(unique("u"), roles=("analyst",))
    enroll_totp(user)
    start_login(new_api, user)
    db = track(dbmod.new_session())
    pending = db.scalars(select(AuthSession).where(AuthSession.user_id == user.id)).one()
    assert pending.stage == "pending_mfa" and pending.mfa is False


def test_recovery_code_works_once(login_as, new_api):
    api, user = login_as("analyst")
    codes = api.post("/api/v1/auth/mfa/recovery-codes", json={"code": code_for(user.totp_secret, 1)}).json()[
        "recovery_codes"]
    assert len(codes) == 10

    first = start_login(new_api, user)
    r = first.post(VERIFY, json={"code": codes[0].lower()})  # aceita minúsculas e sem hífen
    assert r.status_code == 200
    assert first.get("/api/v1/auth/mfa").json()["recovery_codes_left"] == 9

    second = start_login(new_api, user)
    assert second.post(VERIFY, json={"code": codes[0]}).status_code == 401
    db = track(dbmod.new_session())
    assert events(db, "mfa.recovery_code_used", user.id)


def test_regenerating_recovery_codes_needs_authenticator_code(login_as):
    api, user = login_as("analyst")
    r = api.post("/api/v1/auth/mfa/recovery-codes", json={"code": "000000"})
    assert r.status_code == 422


def test_local_account_with_totp(login_as, new_api):
    admin, _ = login_as("admin")
    login = unique("ext")
    # Conta local agora pode receber perfil que exige 2FA: o TOTP cobre o segundo fator.
    r = admin.post("/api/v1/users", json={"login": login, "name": "Auditor Externo", "source": "local",
                                           "email": f"{login}@auditoria.com.br", "roles": ["manager"]})
    assert r.status_code == 201, r.text
    user = create_user(unique("loc"), source="local", password=STRONG_PASSWORD, roles=("auditor",))
    secret = enroll_totp(user)
    api = new_api()
    step1 = api.post(LOCAL_LOGIN, json={"login": user.login, "password": STRONG_PASSWORD})
    assert step1.status_code == 200 and step1.json() == {"status": "mfa_required", "me": None}
    assert not any(c.startswith(ACCESS_COOKIE) for c in step1.headers.get_list("set-cookie"))
    step2 = api.post(VERIFY, json={"code": code_for(secret)})
    assert step2.json()["status"] == "authenticated" and "audit.read" in step2.json()["me"]["permissions"]


# ------------------------------------------------------------------ desativar e resetar
def test_manager_cannot_disable_mfa(login_as):
    api, user = login_as("manager")
    r = api.post("/api/v1/auth/mfa/disable", json={"code": code_for(user.totp_secret, 1)})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "mfa_mandatory"


def test_analyst_disable_flow(login_as, new_api):
    api, user = login_as("analyst", mfa=False)
    secret = api.post("/api/v1/auth/mfa/totp/setup").json()["secret"]
    codes = api.post("/api/v1/auth/mfa/totp/confirm", json={"code": code_for(secret)}).json()["recovery_codes"]
    other = start_login(new_api, user)
    other.post(VERIFY, json={"code": codes[0]})
    assert other.get(ME).status_code == 200

    assert api.post("/api/v1/auth/mfa/disable", json={"code": codes[1]}).status_code == 204
    assert api.get(ME).status_code == 200            # a sessão atual continua
    assert other.get(ME).status_code == 401          # as outras caem
    assert landing(sso_login(new_api(), user.email)) == "/"  # e o login não pede mais código


def test_admin_resets_lost_authenticator(login_as, new_api):
    admin, admin_user = login_as("admin")
    victim_api, victim = login_as("manager")
    assert admin.post(f"/api/v1/users/{admin_user.id}/mfa/reset", json={"reason": "teste"}).status_code == 403

    r = admin.post(f"/api/v1/users/{victim.id}/mfa/reset", json={"reason": "Perdeu o celular, chamado 4521"})
    assert r.status_code == 200 and r.json()["mfa_enrolled"] is False
    assert victim_api.get(ME).status_code == 401      # sessões encerradas

    # Próximo login entra sem código, mas sem as permissões de gerente até cadastrar de novo.
    api = new_api()
    assert landing(sso_login(api, victim.email)) == "/"
    assert api.get(ME).json()["mfa_enrollment_required"] is True
    db = track(dbmod.new_session())
    ev = events(db, "mfa.reset_by_admin", victim.id)[0]
    assert ev.actor_id == admin_user.id and ev.after["reason"].startswith("Perdeu")


def test_required_for_all_setting(login_as):
    admin, _ = login_as("admin")
    analyst, _ = login_as("analyst", mfa=False)
    newcomer, _ = login_as(mfa=False)
    assert "entries.write" in analyst.get(ME).json()["permissions"]
    assert admin.put("/api/v1/settings/mfa.required_for_all", json={"value": True}).status_code == 200
    try:
        me = analyst.get(ME).json()
        assert "entries.write" not in me["permissions"] and me["mfa_enrollment_required"] is True
        # Quem ainda não tem perfil continua podendo pedir acesso.
        assert newcomer.get(ME).json()["permissions"] == ["access.request"]
    finally:
        admin.put("/api/v1/settings/mfa.required_for_all", json={"value": False})
