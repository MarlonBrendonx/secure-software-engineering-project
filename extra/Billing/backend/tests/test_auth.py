"""Login, sessão, rate limit, CSRF, rotação de chaves, desligamento e troca de senha."""
from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from nbb import db as dbmod
from nbb.api.deps import ACCESS_COOKIE, REFRESH_COOKIE
from nbb.main import build_container, create_app
from nbb.models import AuditEvent, AuthSession, User
from tests.conftest import (
    KEY_A, KEY_B, STRONG_PASSWORD, Api, FakeOidc, create_user, landing, make_settings, sso_login, track, unique,
)

ME = "/api/v1/me"
LOCAL_LOGIN = "/api/v1/auth/local/login"


def local_user(**kw):
    return create_user(unique("aud"), source="local", password=STRONG_PASSWORD, **kw)


def test_local_login_sets_httponly_cookies_and_me_works(new_api):
    user = local_user(roles=("auditor",))
    api = new_api()
    r = api.post(LOCAL_LOGIN, json={"login": user.login, "password": STRONG_PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "authenticated"
    set_cookie = r.headers.get_list("set-cookie")
    access = next(c for c in set_cookie if c.startswith(ACCESS_COOKIE + "="))
    refresh = next(c for c in set_cookie if c.startswith(REFRESH_COOKIE + "="))
    assert "HttpOnly" in access and "SameSite=strict" in access
    assert "HttpOnly" in refresh and "Path=/api/v1/auth" in refresh
    assert "access_token" not in r.text  # token nunca vai no corpo, só no cookie
    me = api.get(ME).json()
    assert me["login"] == user.login
    assert "audit.read" in me["permissions"]


def test_password_stored_only_as_argon2_hash():
    user = local_user()
    db = track(dbmod.new_session())
    stored = db.get(User, user.id).password_hash
    assert stored.startswith("$argon2id$") and STRONG_PASSWORD not in stored


def test_wrong_password_is_rejected_and_audited(new_api):
    user = local_user()
    r = new_api().post(LOCAL_LOGIN, json={"login": user.login, "password": "errada"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "invalid_credentials"
    db = track(dbmod.new_session())
    ev = db.scalars(select(AuditEvent).where(AuditEvent.action == "auth.login_failed")
                    .order_by(AuditEvent.seq.desc())).first()
    assert ev.after["login"] == user.login


def test_corporate_user_cannot_use_local_login(new_api):
    user = create_user(unique("corp"), roles=("analyst",))
    r = new_api().post(LOCAL_LOGIN, json={"login": user.login, "password": "qualquer"})
    assert r.status_code == 401


def test_eleventh_login_attempt_in_same_minute_is_blocked(new_api):
    """Critério de aceite: a 11ª tentativa no mesmo minuto é bloqueada."""
    user = local_user()
    api = new_api()
    for i in range(10):
        r = api.post(LOCAL_LOGIN, json={"login": user.login, "password": "errada"})
        assert r.status_code == 401, f"tentativa {i + 1}"
    r = api.post(LOCAL_LOGIN, json={"login": user.login, "password": STRONG_PASSWORD})
    assert r.status_code == 429
    assert r.json()["detail"]["code"] == "rate_limited"
    assert r.json()["detail"]["retry_after"] >= 1


def test_rate_limit_falls_back_to_local_when_redis_is_down(mailer):
    settings = make_settings(redis_url="redis://localhost:1/0")
    api = Api(create_app(build_container(settings, oidc=FakeOidc(), mailer=mailer)))
    codes = [api.post(LOCAL_LOGIN, json={"login": "x", "password": "y"}).status_code for _ in range(11)]
    assert codes[:10] == [401] * 10 and codes[10] == 429


def test_rate_limit_is_per_address(new_api, app):
    api = new_api()
    for _ in range(11):
        api.post(LOCAL_LOGIN, json={"login": "x", "password": "y"})
    other = TestClient(app, client=("10.0.0.9", 5000))
    assert other.post(LOCAL_LOGIN, json={"login": "x", "password": "y"}).status_code == 401


def test_mutation_without_csrf_header_is_rejected(login_as):
    api, _ = login_as("admin")
    r = api.client.put("/api/v1/settings/approval.deviation_pct", json={"value": 25})
    assert r.status_code == 403 and r.json()["detail"]["code"] == "csrf"
    assert api.put("/api/v1/settings/approval.deviation_pct", json={"value": 25}).status_code == 200


def test_tampered_or_unknown_key_token_rejected(login_as):
    api, user = login_as("analyst")
    forged = jwt.encode({"sub": str(user.id), "sid": "x", "tv": 1}, "z" * 48, algorithm="HS256",
                        headers={"kid": "k1"})
    api.cookies.set(ACCESS_COOKIE, forged)
    assert api.get(ME).status_code == 401


def test_periodic_rotation_keeps_sessions_and_emergency_rotation_kills_them(login_as, mailer):
    api, _ = login_as("analyst")
    token = api.cookies.get(ACCESS_COOKIE)

    # Rotação periódica: nova chave ativa, antiga ainda valida.
    rotated = create_app(build_container(
        make_settings(jwt_keys={"k1": KEY_A, "k2": KEY_B}, jwt_active_kid="k2"), oidc=FakeOidc(), mailer=mailer))
    c = TestClient(rotated)
    c.cookies.set(ACCESS_COOKIE, token)
    assert c.get(ME).status_code == 200

    # Emergência: chave comprometida removida -> todos os tokens dela caem.
    emergency = create_app(build_container(
        make_settings(jwt_keys={"k2": KEY_B}, jwt_active_kid="k2"), oidc=FakeOidc(), mailer=mailer))
    c = TestClient(emergency)
    c.cookies.set(ACCESS_COOKIE, token)
    r = c.get(ME)
    assert r.status_code == 401 and r.json()["detail"]["code"] == "token_invalid"


def test_access_token_has_short_expiry(login_as):
    api, _ = login_as("analyst")
    claims = jwt.decode(api.cookies.get(ACCESS_COOKIE), KEY_A, algorithms=["HS256"], issuer="network-billing")
    assert claims["exp"] - claims["iat"] == 900


def test_refresh_rotates_and_reuse_revokes_session(login_as):
    api, user = login_as("analyst")
    old_refresh = api.cookies.get(REFRESH_COOKIE, path="/api/v1/auth")
    assert api.post("/api/v1/auth/refresh").status_code == 204
    new_refresh = api.cookies.get(REFRESH_COOKIE, path="/api/v1/auth")
    assert new_refresh != old_refresh
    assert api.get(ME).status_code == 200

    # Alguém reutiliza o refresh antigo (roubado): a sessão inteira é encerrada.
    thief = Api(api.client.app)
    thief.cookies.set(REFRESH_COOKIE, old_refresh, path="/api/v1/auth")
    thief.cookies.set("nbb_csrf", "t")
    assert thief.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": "t"}).status_code == 401
    assert api.get(ME).status_code == 401


def test_logout_revokes_session(login_as):
    api, _ = login_as("analyst")
    token = api.cookies.get(ACCESS_COOKIE)
    assert api.post("/api/v1/auth/logout").status_code == 204
    api.cookies.set(ACCESS_COOKIE, token)  # mesmo reaproveitando o token antigo
    assert api.get(ME).status_code == 401


def test_termination_kills_all_sessions_immediately(login_as, new_api):
    """Critério de aceite: após o desligamento, as sessões do usuário deixam de funcionar."""
    admin, _ = login_as("admin")
    victim = create_user(unique("desl"), roles=("analyst",))
    s1, s2 = new_api(), new_api()
    assert landing(sso_login(s1, victim.email)) == "/"
    assert landing(sso_login(s2, victim.email)) == "/"
    assert s1.get(ME).status_code == 200 and s2.get(ME).status_code == 200

    r = admin.post(f"/api/v1/users/{victim.id}/terminate", json={"reason": "Desligamento RH"})
    assert r.status_code == 200 and r.json()["status"] == "terminated"

    assert s1.get(ME).status_code == 401
    assert s2.get(ME).status_code == 401
    assert s1.post("/api/v1/auth/refresh").status_code == 401
    # Nem um novo login por SSO funciona.
    assert landing(sso_login(new_api(), victim.email)) == "/login?erro=user_blocked"
    db = track(dbmod.new_session())
    open_sessions = db.scalars(select(AuthSession).where(AuthSession.user_id == victim.id,
                                                         AuthSession.revoked_at.is_(None))).all()
    assert open_sessions == []


def test_password_reset_flow(new_api, mailer):
    user = local_user(roles=("auditor",))
    old = new_api()
    old.post(LOCAL_LOGIN, json={"login": user.login, "password": STRONG_PASSWORD})

    anon = new_api()
    r = anon.post("/api/v1/auth/password/reset-request", json={"login": user.login})
    assert r.status_code == 202
    # Mesma resposta para login inexistente (não revela quem existe).
    assert anon.post("/api/v1/auth/password/reset-request", json={"login": "naoexiste"}).json() == r.json()
    token = mailer.sent[-1][2].split("token=")[1].strip()

    weak = anon.post("/api/v1/auth/password/reset", json={"token": token, "new_password": "curta"})
    assert weak.status_code == 422
    new_password = "OutraSenha!2026x"
    assert anon.post("/api/v1/auth/password/reset", json={"token": token, "new_password": new_password}).status_code == 204
    # Link é de uso único.
    assert anon.post("/api/v1/auth/password/reset",
                     json={"token": token, "new_password": new_password}).status_code == 400
    # Sessões abertas com a senha antiga caem.
    assert old.get(ME).status_code == 401
    assert anon.post(LOCAL_LOGIN, json={"login": user.login, "password": STRONG_PASSWORD}).status_code == 401
    assert anon.post(LOCAL_LOGIN, json={"login": user.login, "password": new_password}).status_code == 200


def test_expired_reset_link_rejected(new_api, mailer):
    user = local_user()
    api = new_api()
    api.post("/api/v1/auth/password/reset-request", json={"login": user.login})
    token = mailer.sent[-1][2].split("token=")[1].strip()
    eng = dbmod.get_engine()
    with eng.begin() as conn:
        conn.execute(text("UPDATE password_reset SET expires_at = :t WHERE user_id = :u"),
                     {"t": datetime.now(UTC) - timedelta(minutes=1), "u": user.id})
    r = api.post("/api/v1/auth/password/reset", json={"token": token, "new_password": "OutraSenha!2026x"})
    assert r.status_code == 400
