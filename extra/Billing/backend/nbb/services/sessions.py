"""Sessões de login: criação, renovação com rotação do refresh token e revogação."""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from nbb.config import Settings
from nbb.core import audit
from nbb.core.security import new_opaque_token, sha256_hex
from nbb.models import AuthSession, User


class SessionError(Exception):
    pass


def create_session(db: Session, settings: Settings, user: User, *, method: str, mfa: bool,
                   ip: str | None, user_agent: str | None, provider: str | None = None,
                   mfa_method: str | None = None) -> tuple[AuthSession, str]:
    token, token_hash = new_opaque_token()
    now = datetime.now(UTC)
    sess = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        auth_method=method,
        provider=provider,
        mfa=mfa,
        mfa_method=mfa_method,
        stage="active",
        refresh_hash=token_hash,
        created_at=now,
        last_used_at=now,
        expires_at=now + timedelta(hours=settings.refresh_absolute_hours),
        ip=ip,
        user_agent=(user_agent or "")[:300] or None,
    )
    db.add(sess)
    return sess, token


def create_pending_mfa(db: Session, settings: Settings, user: User, *, method: str, provider: str | None,
                       ip: str | None, user_agent: str | None) -> tuple[AuthSession, str]:
    """Primeiro fator aceito; a sessão só vale depois do código do autenticador.
    Devolve o ticket (uso único, curta duração) que o navegador apresenta na etapa 2."""
    ticket, ticket_hash = new_opaque_token()
    _, unusable_refresh = new_opaque_token()
    now = datetime.now(UTC)
    sess = AuthSession(
        id=uuid.uuid4(), user_id=user.id, auth_method=method, provider=provider, mfa=False,
        stage="pending_mfa", mfa_ticket_hash=ticket_hash, refresh_hash=unusable_refresh,
        created_at=now, last_used_at=now,
        expires_at=now + timedelta(seconds=settings.mfa_challenge_ttl_seconds),
        ip=ip, user_agent=(user_agent or "")[:300] or None,
    )
    db.add(sess)
    return sess, ticket


def find_pending(db: Session, ticket: str) -> AuthSession | None:
    sess = db.scalar(select(AuthSession).where(AuthSession.mfa_ticket_hash == sha256_hex(ticket))
                     .with_for_update())
    now = datetime.now(UTC)
    if sess is None or sess.stage != "pending_mfa" or sess.revoked_at is not None or now >= sess.expires_at:
        return None
    return sess


def activate_after_mfa(sess: AuthSession, settings: Settings, mfa_method: str) -> str:
    token, token_hash = new_opaque_token()
    now = datetime.now(UTC)
    sess.stage = "active"
    sess.mfa = True
    sess.mfa_method = mfa_method
    sess.mfa_ticket_hash = None
    sess.refresh_hash = token_hash
    sess.last_used_at = now
    sess.expires_at = now + timedelta(hours=settings.refresh_absolute_hours)
    return token


def rotate_refresh(db: Session, settings: Settings, refresh_token: str) -> tuple[AuthSession, User, str]:
    """Troca o refresh token. Reuso de um token já trocado indica roubo:
    a sessão inteira é revogada."""
    h = sha256_hex(refresh_token)
    now = datetime.now(UTC)
    sess = db.scalar(select(AuthSession).where(AuthSession.refresh_hash == h).with_for_update())
    if sess is None:
        stolen = db.scalar(select(AuthSession).where(AuthSession.prev_refresh_hash == h).with_for_update())
        if stolen is not None and stolen.revoked_at is None:
            stolen.revoked_at = now
            stolen.revoke_reason = "refresh_reuse"
            audit.record(db, "auth.refresh_reuse_detected", entity="auth_session", entity_id=stolen.id)
            db.commit()
        raise SessionError("refresh inválido")
    if sess.revoked_at is not None or sess.stage != "active":
        raise SessionError("sessão encerrada")
    if now >= sess.expires_at:
        raise SessionError("sessão expirada")
    if now - sess.last_used_at > timedelta(minutes=settings.refresh_idle_minutes):
        sess.revoked_at = now
        sess.revoke_reason = "idle"
        db.commit()
        raise SessionError("sessão expirada por inatividade")
    user = db.get(User, sess.user_id)
    if user is None or not user.is_active:
        raise SessionError("usuário bloqueado")
    token, token_hash = new_opaque_token()
    sess.prev_refresh_hash = sess.refresh_hash
    sess.refresh_hash = token_hash
    sess.last_used_at = now
    return sess, user, token


def touch(db: Session, sess: AuthSession) -> None:
    sess.last_used_at = datetime.now(UTC)


def revoke_session(db: Session, sess: AuthSession, reason: str) -> None:
    if sess.revoked_at is None:
        sess.revoked_at = datetime.now(UTC)
        sess.revoke_reason = reason


def revoke_all_for_user(db: Session, user_id: uuid.UUID, reason: str,
                        except_id: uuid.UUID | None = None) -> int:
    conds = [AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)]
    if except_id is not None:
        conds.append(AuthSession.id != except_id)
    res = db.execute(
        update(AuthSession)
        .where(*conds)
        .values(revoked_at=datetime.now(UTC), revoke_reason=reason)
    )
    return res.rowcount or 0


def revoke_all(db: Session, reason: str) -> int:
    res = db.execute(
        update(AuthSession).where(AuthSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC), revoke_reason=reason)
    )
    return res.rowcount or 0
