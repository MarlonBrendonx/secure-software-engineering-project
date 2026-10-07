import hmac
import ipaddress
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from nbb.config import Settings
from nbb.core.audit import Actor, set_actor
from nbb.core.crypto import DataCipher
from nbb.core.mailer import Mailer
from nbb.core.oidc import OidcClient
from nbb.core.ratelimit import LoginRateLimiter
from nbb.core.security import JwtKeyring, TokenError
from nbb.db import get_db
from nbb.models import AuthSession, User
from nbb.services.access import EffectiveAccess, effective_access
from nbb.services.settings import get_value

ACCESS_COOKIE = "nbb_at"
REFRESH_COOKIE = "nbb_rt"
CSRF_COOKIE = "nbb_csrf"
CSRF_HEADER = "X-CSRF-Token"
REFRESH_PATH = "/api/v1/auth"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass
class Container:
    settings: Settings
    keyring: JwtKeyring
    limiter: LoginRateLimiter          # tentativas de login por IP
    mfa_limiter: LoginRateLimiter      # tentativas de código 2FA por usuário
    mailer: Mailer
    cipher: DataCipher
    oidc: dict[str, OidcClient] = field(default_factory=dict)


@dataclass
class Current:
    user: User
    session: AuthSession
    access: EffectiveAccess


def error(status: int, code: str, message: str, **extra) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message, **extra})


def get_container(request: Request) -> Container:
    return request.app.state.container


def client_ip(request: Request, settings: Settings) -> str:
    peer = request.client.host if request.client else "unknown"
    if not settings.trusted_proxies or peer not in settings.trusted_proxies:
        return peer
    # Percorre o X-Forwarded-For da direita para a esquerda, pulando proxies confiáveis.
    chain = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    for hop in reversed(chain):
        if hop not in settings.trusted_proxies:
            try:
                ipaddress.ip_address(hop)
                return hop
            except ValueError:
                break
    return peer


def request_actor(request: Request, settings: Settings, user: User | None = None) -> Actor:
    return Actor(
        user_id=user.id if user else None,
        login=user.login if user else None,
        ip=client_ip(request, settings),
        request_id=request.headers.get("x-request-id") or uuid.uuid4().hex,
    )


def _check_csrf(request: Request) -> None:
    if request.method in SAFE_METHODS:
        return
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get(CSRF_HEADER, "")
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise error(403, "csrf", "Token CSRF ausente ou inválido.")


def get_current(request: Request, db: Session = Depends(get_db),
                c: Container = Depends(get_container)) -> Current:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise error(401, "unauthenticated", "Faça login.")
    try:
        claims = c.keyring.verify(token)
    except TokenError:
        raise error(401, "token_invalid", "Sessão inválida ou expirada.") from None
    user = db.get(User, claims.user_id)
    sess = db.get(AuthSession, claims.session_id)
    now = datetime.now(UTC)
    if (
        user is None or sess is None or sess.user_id != user.id
        or not user.is_active
        or user.token_version != claims.token_version
        or sess.revoked_at is not None
        or sess.stage != "active"
        or now >= sess.expires_at
    ):
        raise error(401, "session_revoked", "Sessão encerrada.")
    _check_csrf(request)
    access = effective_access(db, user, sess.mfa, now, mfa_for_all=bool(get_value(db, "mfa.required_for_all")))
    set_actor(db, request_actor(request, c.settings, user))
    return Current(user=user, session=sess, access=access)


def require(permission: str):
    def dep(current: Current = Depends(get_current), db: Session = Depends(get_db)) -> Current:
        if not current.access.has(permission):
            if permission in current.access.blocked_by_mfa:
                raise error(403, "mfa_required",
                            "Esta ação exige verificação em duas etapas. Ative o autenticador em "
                            "'Segurança da conta' ou entre de novo informando o código.")
            raise error(403, "forbidden", "Você não tem permissão para esta ação.")
        # Registra na auditoria se a permissão veio de uma substituição.
        actor = db.info.get("actor")
        if actor is not None:
            actor.via_delegation_id = current.access.permissions[permission]
        return current

    return dep
