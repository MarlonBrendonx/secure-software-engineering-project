"""Login em duas etapas.

Etapa 1 (primeiro fator), por um destes caminhos:
  - SSO: GET /auth/oidc/{provedor}/login -> provedor -> GET .../callback
  - Conta local: POST /auth/local/login (usuário e senha)

Etapa 2 (segundo fator), quando o usuário tem o autenticador ativo:
  - o sistema guarda uma sessão "pendente" e entrega ao navegador um ticket
    (cookie HttpOnly, 5 minutos, uso único);
  - POST /auth/mfa/verify com o código de 6 dígitos (ou um código de
    recuperação) transforma a sessão pendente em sessão válida.
"""
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nbb.api.deps import (
    ACCESS_COOKIE, CSRF_COOKIE, REFRESH_COOKIE, REFRESH_PATH, Container, Current, _check_csrf,
    error, get_container, get_current, request_actor,
)
from nbb.core import audit
from nbb.core.audit import set_actor
from nbb.core.oidc import OidcError, OidcIdentity, new_pkce_pair
from nbb.core.security import (
    TokenError, hash_password, new_opaque_token, sha256_hex, validate_password_policy, verify_password,
)
from nbb.db import get_db
from nbb.models import AuthSession, PasswordReset, User, UserSource, UserStatus
from nbb.services import mfa as mfa_svc
from nbb.services import sessions
from nbb.services.access import effective_access
from nbb.services.settings import get_value
from nbb.services.sso import SsoRejected, resolve_user

router = APIRouter(prefix="/auth", tags=["auth"])
OIDC_COOKIE = "nbb_oidc"
MFA_COOKIE = "nbb_mfa"
MFA_PATH = f"{REFRESH_PATH}/mfa"


# ---------------------------------------------------------------- schemas
class LocalLoginIn(BaseModel):
    login: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=512)


class CodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=20,
                      description="Código de 6 dígitos do autenticador ou um código de recuperação")


class ResetRequestIn(BaseModel):
    login: str = Field(min_length=1, max_length=120)


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: str = Field(min_length=1, max_length=512)


class ProviderOut(BaseModel):
    id: str
    name: str
    login_url: str


class MeOut(BaseModel):
    id: str
    login: str
    name: str
    email: str | None
    source: str
    mfa: bool = Field(description="Esta sessão passou pela verificação em duas etapas")
    mfa_enrolled: bool = Field(description="O usuário tem o autenticador ativo")
    mfa_enrollment_required: bool = Field(
        description="O perfil exige 2FA e o usuário ainda não ativou: a tela deve levar ao cadastro")
    roles: list[str]
    roles_pending_mfa: list[str] = Field(description="Perfis suspensos até o usuário passar pelo 2FA")
    permissions: list[str]
    permissions_requiring_mfa: list[str]
    delegations: list[dict]


class LoginOut(BaseModel):
    status: Literal["authenticated", "mfa_required"]
    me: MeOut | None = None


def me_out(db: Session, current: Current) -> MeOut:
    enrolled = mfa_svc.is_enrolled(db, current.user.id)
    return MeOut(
        id=str(current.user.id),
        login=current.user.login,
        name=current.user.name,
        email=current.user.email,
        source=current.user.source,
        mfa=current.session.mfa,
        mfa_enrolled=enrolled,
        mfa_enrollment_required=current.access.mfa_required and not enrolled,
        roles=sorted(current.access.roles),
        roles_pending_mfa=sorted(current.access.roles_pending_mfa),
        permissions=sorted(current.access.permissions),
        permissions_requiring_mfa=sorted(current.access.blocked_by_mfa),
        delegations=[
            {"id": str(d.id), "role": d.role_code, "titular_id": str(d.titular_id), "ends_at": d.ends_at.isoformat()}
            for d in current.access.delegations
        ],
    )


def _current_for(db: Session, user: User, sess: AuthSession) -> Current:
    return Current(user, sess, effective_access(
        db, user, sess.mfa, datetime.now(UTC), mfa_for_all=bool(get_value(db, "mfa.required_for_all"))))


# ---------------------------------------------------------------- helpers
def _rate_limit(request: Request, c: Container) -> None:
    ip = request_actor(request, c.settings).ip or "unknown"
    allowed, retry = c.limiter.hit(ip)
    if not allowed:
        raise error(429, "rate_limited", "Muitas tentativas de login. Aguarde e tente novamente.",
                    retry_after=retry)


def _common_cookie(c: Container) -> dict:
    return {"secure": c.settings.cookie_secure, "samesite": "strict", "domain": c.settings.cookie_domain}


def set_session_cookies(response: Response, c: Container, user: User, sess: AuthSession, refresh: str) -> None:
    s = c.settings
    access, _ = c.keyring.issue(user.id, sess.id, user.token_version)
    common = _common_cookie(c)
    response.set_cookie(ACCESS_COOKIE, access, httponly=True, path="/",
                        max_age=s.access_token_ttl_seconds, **common)
    response.set_cookie(REFRESH_COOKIE, refresh, httponly=True, path=REFRESH_PATH,
                        max_age=int((sess.expires_at - datetime.now(UTC)).total_seconds()), **common)
    # Cookie legível pelo frontend para o double-submit do CSRF.
    response.set_cookie(CSRF_COOKIE, secrets.token_urlsafe(24), httponly=False, path="/",
                        max_age=s.refresh_absolute_hours * 3600, **common)


def _clear_cookies(response: Response, c: Container) -> None:
    for name, path in ((ACCESS_COOKIE, "/"), (REFRESH_COOKIE, REFRESH_PATH), (CSRF_COOKIE, "/"),
                       (MFA_COOKIE, MFA_PATH)):
        response.delete_cookie(name, path=path, domain=c.settings.cookie_domain)


def _find_user(db: Session, login: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.login) == login.strip().lower()))


def _finish_first_factor(db: Session, c: Container, request: Request, response: Response, user: User, *,
                         method: str, provider: str | None = None, idp_mfa: bool = False) -> LoginOut:
    """Primeiro fator aceito. Pede o código se o usuário tem autenticador ativo."""
    set_actor(db, request_actor(request, c.settings, user))
    ip, ua = db.info["actor"].ip, request.headers.get("user-agent")
    if idp_mfa:
        # Provedor configurado com trust_idp_mfa e que declarou segundo fator.
        sess, refresh = sessions.create_session(db, c.settings, user, method=method, provider=provider,
                                                mfa=True, mfa_method="idp", ip=ip, user_agent=ua)
    elif mfa_svc.is_enrolled(db, user.id):
        sess, ticket = sessions.create_pending_mfa(db, c.settings, user, method=method, provider=provider,
                                                   ip=ip, user_agent=ua)
        audit.record(db, "auth.mfa_challenge", entity="auth_session", entity_id=sess.id,
                     detail={"method": method, "provider": provider})
        db.commit()
        response.set_cookie(MFA_COOKIE, ticket, httponly=True, path=MFA_PATH,
                            max_age=c.settings.mfa_challenge_ttl_seconds, **_common_cookie(c))
        return LoginOut(status="mfa_required")
    else:
        sess, refresh = sessions.create_session(db, c.settings, user, method=method, provider=provider,
                                                mfa=False, ip=ip, user_agent=ua)
    audit.record(db, "auth.login", entity="auth_session", entity_id=sess.id,
                 detail={"method": method, "provider": provider, "mfa": sess.mfa_method})
    db.commit()
    set_session_cookies(response, c, user, sess, refresh)
    return LoginOut(status="authenticated", me=me_out(db, _current_for(db, user, sess)))


# ---------------------------------------------------------------- provedores e SSO
@router.get("/providers", response_model=list[ProviderOut], summary="Provedores de login disponíveis")
def list_providers(c: Container = Depends(get_container)):
    return [ProviderOut(id=pid, name=cl.config.name, login_url=f"/api/v1/auth/oidc/{pid}/login")
            for pid, cl in c.oidc.items()]


def _redirect_uri(c: Container, provider: str) -> str:
    return f"{c.settings.public_base_url.rstrip('/')}/api/v1/auth/oidc/{provider}/callback"


def _front(c: Container, path: str, **params) -> RedirectResponse:
    url = c.settings.frontend_url.rstrip("/") + path
    if params:
        url += "?" + urlencode(params)
    return RedirectResponse(url, status_code=302)


@router.get("/oidc/{provider}/login", summary="Inicia o login por Google, Microsoft ou provedor corporativo")
def oidc_start(provider: str, c: Container = Depends(get_container)):
    client = c.oidc.get(provider)
    if client is None:
        raise error(404, "unknown_provider", "Provedor de login não configurado.")
    state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    verifier, challenge = new_pkce_pair()
    try:
        url = client.authorization_url(state, nonce, challenge, _redirect_uri(c, provider))
    except OidcError:
        raise error(503, "provider_unavailable", "Provedor de login indisponível. Tente outro.") from None
    resp = RedirectResponse(url, status_code=302)
    signed = c.keyring.sign_aux("oidc", {"p": provider, "state": state, "nonce": nonce, "verifier": verifier}, 600)
    # Lax: o cookie precisa voltar no redirecionamento vindo do provedor.
    resp.set_cookie(OIDC_COOKIE, signed, httponly=True, secure=c.settings.cookie_secure,
                    samesite="lax", path=f"{REFRESH_PATH}/oidc/{provider}/callback", max_age=600)
    return resp


@router.get("/oidc/{provider}/callback", summary="Retorno do provedor de login",
            description="Sempre redireciona para o frontend: `/` (logado), `/login/verificacao` "
                        "(falta o código do autenticador) ou `/login?erro=<código>`.")
def oidc_callback(provider: str, request: Request, code: str | None = None, state: str | None = None,
                  error_code: str | None = None, db: Session = Depends(get_db),
                  c: Container = Depends(get_container)):
    set_actor(db, request_actor(request, c.settings))
    ip = db.info["actor"].ip or "unknown"
    allowed, _ = c.limiter.hit(ip)
    if not allowed:
        return _front(c, "/login", erro="rate_limited")
    client = c.oidc.get(provider)
    if client is None:
        return _front(c, "/login", erro="unknown_provider")
    if not code or not state:
        # Usuário cancelou no provedor (error=access_denied) ou chamada inválida.
        return _front(c, "/login", erro="cancelled")
    try:
        saved = c.keyring.verify_aux("oidc", request.cookies.get(OIDC_COOKIE, ""))
    except TokenError:
        return _front(c, "/login", erro="expired")
    if saved.get("p") != provider or not secrets.compare_digest(saved["state"], state):
        return _front(c, "/login", erro="invalid_state")

    def fail(code_: str, detail: dict) -> RedirectResponse:
        audit.record(db, "auth.login_failed", detail={"method": "sso", "provider": provider, **detail})
        db.commit()
        return _front(c, "/login", erro=code_)

    try:
        ident: OidcIdentity = client.exchange(code, saved["verifier"], saved["nonce"], _redirect_uri(c, provider))
    except OidcError as exc:
        return fail("provider_error", {"reason": str(exc)[:200]})
    try:
        user = resolve_user(db, ident, client.config)
    except SsoRejected as rej:
        db.rollback()
        set_actor(db, request_actor(request, c.settings))
        return fail(rej.code, {"reason": rej.code, "email": ident.email})
    if user.source != UserSource.SSO or not user.is_active:
        db.rollback()
        set_actor(db, request_actor(request, c.settings))
        return fail("user_blocked", {"reason": "blocked", "email": ident.email})

    resp = _front(c, "/")
    out = _finish_first_factor(db, c, request, resp, user, method="sso", provider=provider,
                               idp_mfa=client.config.trust_idp_mfa and ident.idp_mfa)
    if out.status == "mfa_required":
        resp.headers["location"] = c.settings.frontend_url.rstrip("/") + "/login/verificacao"
    resp.delete_cookie(OIDC_COOKIE, path=f"{REFRESH_PATH}/oidc/{provider}/callback")
    return resp


# ---------------------------------------------------------------- conta local
@router.post("/local/login", response_model=LoginOut, summary="Login com usuário e senha cadastrados no sistema",
             description="Se o usuário tiver autenticador ativo, responde `mfa_required` e o login "
                         "continua em `POST /auth/mfa/verify`.")
def local_login(body: LocalLoginIn, request: Request, response: Response,
                db: Session = Depends(get_db), c: Container = Depends(get_container)):
    _rate_limit(request, c)
    set_actor(db, request_actor(request, c.settings))
    user = _find_user(db, body.login)
    ok = verify_password(user.password_hash if user else None, body.password)
    if not ok or user is None or user.source != UserSource.LOCAL or not user.is_active:
        audit.record(db, "auth.login_failed", detail={"login": body.login[:120], "method": "local"})
        db.commit()
        raise error(401, "invalid_credentials", "Usuário ou senha inválidos.")
    return _finish_first_factor(db, c, request, response, user, method="local")


# ---------------------------------------------------------------- etapa 2: código
@router.post("/mfa/verify", response_model=LoginOut, summary="Segunda etapa do login: código do autenticador")
def mfa_verify(body: CodeIn, request: Request, response: Response,
               db: Session = Depends(get_db), c: Container = Depends(get_container)):
    _rate_limit(request, c)
    set_actor(db, request_actor(request, c.settings))
    sess = sessions.find_pending(db, request.cookies.get(MFA_COOKIE, ""))
    if sess is None:
        raise error(401, "mfa_challenge_expired", "A verificação expirou. Faça login novamente.")
    user = db.get(User, sess.user_id)
    if user is None or not user.is_active:
        sessions.revoke_session(db, sess, "user_blocked")
        db.commit()
        raise error(401, "mfa_challenge_expired", "A verificação expirou. Faça login novamente.")
    set_actor(db, request_actor(request, c.settings, user))
    user_key = f"mfa:{user.id}"
    blocked, retry = c.mfa_limiter.blocked(user_key)
    if blocked:
        raise error(429, "mfa_locked", "Muitos códigos errados. Aguarde alguns minutos.", retry_after=retry)

    method = mfa_svc.verify(db, c.cipher, user, body.code)
    if method is None:
        c.mfa_limiter.hit(user_key)
        sess.mfa_attempts += 1
        left = c.settings.mfa_max_attempts - sess.mfa_attempts
        if left <= 0:
            sessions.revoke_session(db, sess, "mfa_failed")
        audit.record(db, "auth.mfa_failed", entity="auth_session", entity_id=sess.id,
                     detail={"attempt": sess.mfa_attempts})
        db.commit()
        if left <= 0:
            response.delete_cookie(MFA_COOKIE, path=MFA_PATH)
            raise error(401, "mfa_challenge_expired", "Tentativas esgotadas. Faça login novamente.")
        raise error(401, "invalid_code", "Código inválido.", attempts_left=left)

    refresh = sessions.activate_after_mfa(sess, c.settings, method)
    audit.record(db, "auth.login", entity="auth_session", entity_id=sess.id,
                 detail={"method": sess.auth_method, "provider": sess.provider, "mfa": method})
    db.commit()
    set_session_cookies(response, c, user, sess, refresh)
    response.delete_cookie(MFA_COOKIE, path=MFA_PATH, domain=c.settings.cookie_domain)
    return LoginOut(status="authenticated", me=me_out(db, _current_for(db, user, sess)))


# ---------------------------------------------------------------- sessão
@router.post("/refresh", status_code=204, summary="Renova o token de acesso")
def refresh(request: Request, response: Response,
            db: Session = Depends(get_db), c: Container = Depends(get_container)):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise error(401, "unauthenticated", "Faça login.")
    _check_csrf(request)
    try:
        sess, user, new_refresh = sessions.rotate_refresh(db, c.settings, token)
    except sessions.SessionError as exc:
        _clear_cookies(response, c)
        raise error(401, "session_revoked", str(exc)) from None
    db.commit()
    set_session_cookies(response, c, user, sess, new_refresh)


@router.post("/logout", status_code=204, summary="Encerra a sessão atual")
def logout(response: Response, current: Current = Depends(get_current),
           db: Session = Depends(get_db), c: Container = Depends(get_container)):
    sessions.revoke_session(db, current.session, "logout")
    audit.record(db, "auth.logout", entity="auth_session", entity_id=current.session.id)
    db.commit()
    _clear_cookies(response, c)


# ---------------------------------------------------------------- senha (contas locais)
@router.post("/password/reset-request", status_code=202,
             summary="Solicita nova senha (contas locais). A resposta é sempre a mesma.")
def password_reset_request(body: ResetRequestIn, request: Request,
                           db: Session = Depends(get_db), c: Container = Depends(get_container)):
    _rate_limit(request, c)
    set_actor(db, request_actor(request, c.settings))
    user = _find_user(db, body.login)
    if user and user.source == UserSource.LOCAL and user.is_active and user.email:
        issue_password_reset(db, c, user)
        audit.record(db, "auth.password_reset_requested", entity="app_user", entity_id=user.id)
        db.commit()
    return {"message": "Se a conta existir, um link para criar nova senha foi enviado ao e-mail cadastrado."}


def issue_password_reset(db: Session, c: Container, user: User) -> None:
    token, token_hash = new_opaque_token()
    db.add(PasswordReset(user_id=user.id, token_hash=token_hash,
                         expires_at=datetime.now(UTC) + timedelta(minutes=c.settings.password_reset_ttl_minutes)))
    link = f"{c.settings.frontend_url}/nova-senha?token={token}"
    c.mailer.send(user.email or "", "Criar nova senha",
                  f"Use o link abaixo em até {c.settings.password_reset_ttl_minutes} minutos:\n{link}")


@router.post("/password/reset", status_code=204, summary="Define nova senha a partir do link recebido",
             description="Trocar a senha não desliga o autenticador: o próximo login continua pedindo o código.")
def password_reset(body: ResetIn, request: Request,
                   db: Session = Depends(get_db), c: Container = Depends(get_container)):
    _rate_limit(request, c)
    now = datetime.now(UTC)
    pr = db.scalar(select(PasswordReset).where(PasswordReset.token_hash == sha256_hex(body.token))
                   .with_for_update())
    if pr is None or pr.used_at is not None or pr.expires_at <= now:
        raise error(400, "reset_invalid", "Link inválido ou expirado. Solicite outro.")
    user = db.get(User, pr.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise error(400, "reset_invalid", "Link inválido ou expirado. Solicite outro.")
    try:
        validate_password_policy(body.new_password, c.settings.password_min_length)
    except ValueError as exc:
        raise error(422, "weak_password", str(exc)) from None
    set_actor(db, request_actor(request, c.settings, user))
    pr.used_at = now
    user.password_hash = hash_password(body.new_password)
    user.token_version += 1
    sessions.revoke_all_for_user(db, user.id, "password_reset")
    db.commit()


me_router = APIRouter(tags=["auth"])


@me_router.get("/me", response_model=MeOut, summary="Usuário logado e permissões efetivas")
def me(current: Current = Depends(get_current), db: Session = Depends(get_db)):
    return me_out(db, current)
