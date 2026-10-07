"""Login por SSO com vários provedores (Google, Microsoft, corporativo)."""
from sqlalchemy import select

from nbb import db as dbmod
from nbb.models import AuditEvent, User, UserIdentity
from tests.conftest import (
    DOMAIN, STRONG_PASSWORD, create_user, enroll_totp, landing, sso_login, track, unique,
)

ME = "/api/v1/me"


def last_failure(db):
    return db.scalars(select(AuditEvent).where(AuditEvent.action == "auth.login_failed")
                      .order_by(AuditEvent.seq.desc())).first()


def test_login_screen_lists_configured_providers(new_api):
    providers = new_api().get("/api/v1/auth/providers").json()
    assert {p["id"]: p["name"] for p in providers} == {
        "google": "Google", "microsoft": "Microsoft", "corporativo": "Login corporativo"}
    assert providers[0]["login_url"].startswith("/api/v1/auth/oidc/")


def test_unknown_provider(new_api):
    assert new_api().get("/api/v1/auth/oidc/facebook/login", follow_redirects=False).status_code == 404


def test_start_redirects_to_provider_with_pkce_state_cookie(new_api):
    r = new_api().get("/api/v1/auth/oidc/google/login", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].startswith("https://idp.test/google/authorize")
    cookie = r.headers["set-cookie"]
    assert "nbb_oidc=" in cookie and "HttpOnly" in cookie and "Path=/api/v1/auth/oidc/google/callback" in cookie


def test_google_company_domain_is_auto_provisioned_without_profile(new_api):
    api = new_api()
    email = f"{unique('novo')}@{DOMAIN}"
    assert landing(sso_login(api, email)) == "/"
    me = api.get(ME).json()
    assert me["login"] == email and me["source"] == "sso"
    assert me["roles"] == ["none"] and me["permissions"] == ["access.request"]


def test_google_other_domain_is_rejected(new_api):
    r = sso_login(new_api(), f"{unique('x')}@gmail.com")
    assert landing(r) == "/login?erro=domain_not_allowed"
    db = track(dbmod.new_session())
    assert last_failure(db).after["reason"] == "domain_not_allowed"


def test_unverified_email_is_never_trusted(new_api):
    email = f"{unique('nv')}@{DOMAIN}"
    assert landing(sso_login(new_api(), email, verified=False)) == "/login?erro=email_not_verified"
    db = track(dbmod.new_session())
    assert db.scalar(select(User.id).where(User.email == email)) is None


def test_microsoft_links_preregistered_user_of_any_domain(new_api):
    user = create_user(unique("ms"), roles=("analyst",), email=f"{unique('pessoa')}@outlook.com")
    api = new_api()
    assert landing(sso_login(api, user.email, provider="microsoft", sub="ms-123")) == "/"
    assert api.get(ME).json()["id"] == str(user.id)
    db = track(dbmod.new_session())
    link = db.scalars(select(UserIdentity).where(UserIdentity.user_id == user.id)).one()
    assert (link.provider, link.subject) == ("microsoft", "ms-123")

    # Daí em diante vale o `sub`, mesmo que a pessoa troque o e-mail na conta Microsoft.
    api2 = new_api()
    assert landing(sso_login(api2, "novo-email@outlook.com", provider="microsoft", sub="ms-123")) == "/"
    assert api2.get(ME).json()["id"] == str(user.id)


def test_microsoft_without_preregistration_is_rejected(new_api):
    r = sso_login(new_api(), f"{unique('x')}@outlook.com", provider="microsoft")
    assert landing(r) == "/login?erro=not_registered"


def test_second_account_with_same_email_cannot_take_over_user(new_api):
    user = create_user(unique("alvo"), roles=("analyst",))
    assert landing(sso_login(new_api(), user.email, sub="conta-original")) == "/"
    # Outra conta do mesmo provedor alegando o mesmo e-mail não assume o usuário.
    r = sso_login(new_api(), user.email, sub="conta-intrusa")
    assert landing(r) == "/login?erro=identity_conflict"


def test_sso_never_links_to_local_account(new_api):
    local = create_user(unique("loc"), source="local", password=STRONG_PASSWORD, roles=("auditor",))
    r = sso_login(new_api(), local.email)
    assert landing(r) == "/login?erro=identity_conflict"


def test_one_user_can_sign_in_with_google_and_microsoft(login_as, new_api):
    admin, _ = login_as("admin")
    user = create_user(unique("dupla"), roles=("analyst",))
    assert landing(sso_login(new_api(), user.email, provider="google")) == "/"
    assert landing(sso_login(new_api(), user.email, provider="microsoft")) == "/"
    listed = next(u for u in admin.get("/api/v1/users", params={"q": user.login}).json() if u["id"] == str(user.id))
    assert listed["sso_providers"] == ["google", "microsoft"]


def test_callback_errors_redirect_to_login_page(new_api):
    api = new_api()
    api.get("/api/v1/auth/oidc/google/login", follow_redirects=False)
    bad_state = api.get("/api/v1/auth/oidc/google/callback", params={"code": "x|y|1|", "state": "forjado"},
                        follow_redirects=False)
    assert landing(bad_state) == "/login?erro=invalid_state"
    cancelled = api.get("/api/v1/auth/oidc/google/callback", params={"error": "access_denied"},
                        follow_redirects=False)
    assert landing(cancelled) == "/login?erro=cancelled"
    # Estado de um provedor não serve no callback de outro.
    start = api.get("/api/v1/auth/oidc/google/login", follow_redirects=False)
    state = start.headers["location"].split("state=")[1]
    cross = api.get("/api/v1/auth/oidc/microsoft/callback", params={"code": "a|b@c.d|1|", "state": state},
                    follow_redirects=False)
    assert landing(cross).startswith("/login?erro=")


def test_provider_error_is_audited(new_api):
    api = new_api()
    start = api.get("/api/v1/auth/oidc/google/login", follow_redirects=False)
    state = start.headers["location"].split("state=")[1]
    r = api.get("/api/v1/auth/oidc/google/callback", params={"code": "bad", "state": state}, follow_redirects=False)
    assert landing(r) == "/login?erro=provider_error"
    db = track(dbmod.new_session())
    assert last_failure(db).after["provider"] == "google"


def test_corporate_idp_mfa_is_accepted_in_place_of_totp(new_api):
    manager = create_user(unique("ger"), roles=("manager",))
    with_mfa = new_api()
    assert landing(sso_login(with_mfa, manager.email, provider="corporativo", amr="mfa")) == "/"
    me = with_mfa.get(ME).json()
    assert me["mfa"] is True and "entries.approve" in me["permissions"]

    without_mfa = new_api()
    assert landing(sso_login(without_mfa, manager.email, provider="corporativo")) == "/"
    assert "entries.approve" in without_mfa.get(ME).json()["permissions_requiring_mfa"]


def test_google_amr_is_ignored_when_provider_not_trusted(new_api):
    """Google não está com trust_idp_mfa: dizer amr=mfa não dispensa o código do autenticador."""
    manager = create_user(unique("ger"), roles=("manager",))
    enroll_totp(manager)
    assert landing(sso_login(new_api(), manager.email, amr="mfa")) == "/login/verificacao"
