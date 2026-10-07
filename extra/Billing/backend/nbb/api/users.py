"""Usuários, perfis, desligamento, substituições e pedidos de acesso."""
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime, BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nbb.api.auth import issue_password_reset
from nbb.api.deps import Container, Current, error, get_container, require
from nbb.core import audit
from nbb.core.permissions import P
from nbb.db import get_db
from nbb.models import (
    AccessRequest, AccessRequestStatus, Delegation, Role, User, UserIdentity, UserMfa, UserRole, UserSource,
    UserStatus,
)
from nbb.services import mfa as mfa_svc
from nbb.services import sessions
from nbb.services.settings import get_value

router = APIRouter(tags=["usuarios"])


# ---------------------------------------------------------------- schemas
class UserOut(BaseModel):
    id: uuid.UUID
    login: str
    name: str
    email: str | None
    source: str
    status: str
    roles: list[str]
    mfa_enrolled: bool
    sso_providers: list[str]
    created_at: datetime
    terminated_at: datetime | None


class UserCreateIn(BaseModel):
    login: str = Field(min_length=2, max_length=120, pattern=r"^[A-Za-z0-9._@-]+$")
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr = Field(description="SSO: o e-mail da conta Google/Microsoft que a pessoa vai usar. "
                                        "Local: recebe o link para criar a senha.")
    source: UserSource = UserSource.SSO
    roles: list[str] = Field(default_factory=list)


class MfaResetIn(BaseModel):
    reason: str = Field(min_length=5, max_length=500, description="Ex.: perdeu o celular, chamado 1234")


class RolesIn(BaseModel):
    roles: list[str]


class TerminateIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class DelegationIn(BaseModel):
    titular_id: uuid.UUID
    substitute_id: uuid.UUID
    role_code: str
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    justification: str = Field(min_length=5, max_length=2000)
    document_ref: str | None = Field(default=None, max_length=200)


class DelegationOut(BaseModel):
    id: uuid.UUID
    titular_id: uuid.UUID
    substitute_id: uuid.UUID
    role_code: str
    starts_at: datetime
    ends_at: datetime
    justification: str
    document_ref: str | None
    granted_by: uuid.UUID
    revoked_at: datetime | None
    active: bool


class AccessRequestIn(BaseModel):
    role_code: str
    justification: str = Field(min_length=5, max_length=2000)


class AccessRequestOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role_code: str
    justification: str
    status: str
    created_at: datetime
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    decision_comment: str | None


class DecisionIn(BaseModel):
    approve: bool
    comment: str | None = Field(default=None, max_length=2000)


# ---------------------------------------------------------------- helpers
def _user_out(db: Session, u: User) -> UserOut:
    roles = sorted(db.scalars(select(UserRole.role_code).where(UserRole.user_id == u.id)))
    providers = sorted(set(db.scalars(select(UserIdentity.provider).where(UserIdentity.user_id == u.id))))
    return UserOut(id=u.id, login=u.login, name=u.name, email=u.email, source=u.source, status=u.status,
                   roles=roles, mfa_enrolled=mfa_svc.is_enrolled(db, u.id), sso_providers=providers,
                   created_at=u.created_at, terminated_at=u.terminated_at)


def _get_user(db: Session, user_id: uuid.UUID) -> User:
    u = db.get(User, user_id)
    if u is None:
        raise error(404, "not_found", "Usuário não encontrado.")
    return u


def _validate_roles_for(db: Session, user: User, codes: set[str]) -> None:
    roles = {r.code: r for r in db.scalars(select(Role).where(Role.code.in_(codes)))}
    unknown = codes - set(roles) | ({"none"} & codes)
    if unknown:
        raise error(422, "invalid_role", f"Perfis inválidos: {', '.join(sorted(unknown))}.")


def _set_roles(db: Session, user: User, codes: set[str], by: uuid.UUID) -> None:
    current = set(db.scalars(select(UserRole.role_code).where(UserRole.user_id == user.id)))
    for code in current - codes:
        db.delete(db.get(UserRole, (user.id, code)))
    for code in codes - current:
        db.add(UserRole(user_id=user.id, role_code=code, granted_by=by))


def _delegation_out(d: Delegation, now: datetime) -> DelegationOut:
    return DelegationOut(**{k: getattr(d, k) for k in DelegationOut.model_fields if k != "active"},
                         active=d.is_active_at(now))


# ---------------------------------------------------------------- usuários
@router.get("/users", response_model=list[UserOut], summary="Lista usuários")
def list_users(status: UserStatus | None = None, q: str | None = Query(default=None, max_length=100),
               current: Current = Depends(require(P.USERS_MANAGE)), db: Session = Depends(get_db)):
    stmt = select(User).order_by(User.name)
    if status:
        stmt = stmt.where(User.status == status)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(User.login).like(like) | func.lower(User.name).like(like))
    return [_user_out(db, u) for u in db.scalars(stmt.limit(500))]


@router.post("/users", response_model=UserOut, status_code=201,
             summary="Cadastra usuário (local recebe link para criar a senha)")
def create_user(body: UserCreateIn, current: Current = Depends(require(P.USERS_MANAGE)),
                db: Session = Depends(get_db), c: Container = Depends(get_container)):
    if db.scalar(select(User.id).where(func.lower(User.login) == body.login.lower())):
        raise error(409, "login_taken", "Já existe usuário com esse login.")
    email = body.email.lower()
    if db.scalar(select(User.id).where(func.lower(User.email) == email, User.status == UserStatus.ACTIVE)):
        # O e-mail é a chave do primeiro login por SSO: não pode haver dois usuários ativos com ele.
        raise error(409, "email_taken", "Já existe usuário ativo com esse e-mail.")
    user = User(login=body.login, name=body.name, email=email, source=body.source)
    db.add(user)
    db.flush()
    codes = set(body.roles)
    _validate_roles_for(db, user, codes)
    _set_roles(db, user, codes, current.user.id)
    if body.source == UserSource.LOCAL:
        issue_password_reset(db, c, user)
    db.commit()
    return _user_out(db, user)


@router.put("/users/{user_id}/roles", response_model=UserOut, summary="Define os perfis de um usuário")
def set_roles(user_id: uuid.UUID, body: RolesIn, current: Current = Depends(require(P.USERS_MANAGE)),
              db: Session = Depends(get_db)):
    if user_id == current.user.id:
        raise error(403, "self_change", "Ninguém altera os próprios perfis.")
    user = _get_user(db, user_id)
    if not user.is_active:
        raise error(409, "user_terminated", "Usuário desligado.")
    codes = set(body.roles)
    _validate_roles_for(db, user, codes)
    # As permissões são recalculadas a cada requisição: a mudança vale na hora.
    _set_roles(db, user, codes, current.user.id)
    db.commit()
    return _user_out(db, user)


@router.post("/users/{user_id}/terminate", response_model=UserOut,
             summary="Desligamento: bloqueia o acesso e encerra todas as sessões imediatamente")
def terminate_user(user_id: uuid.UUID, body: TerminateIn,
                   current: Current = Depends(require(P.USERS_MANAGE)), db: Session = Depends(get_db)):
    if user_id == current.user.id:
        raise error(403, "self_change", "Ninguém desliga a si mesmo.")
    user = _get_user(db, user_id)
    if not user.is_active:
        raise error(409, "already_terminated", "Usuário já desligado.")
    now = datetime.now(UTC)
    user.status = UserStatus.TERMINATED
    user.terminated_at = now
    user.terminated_by = current.user.id
    user.token_version += 1
    closed = sessions.revoke_all_for_user(db, user.id, "terminated")
    for d in db.scalars(select(Delegation).where(
        (Delegation.substitute_id == user.id) | (Delegation.titular_id == user.id),
        Delegation.revoked_at.is_(None), Delegation.ends_at > now,
    )):
        d.revoked_at = now
        d.revoked_by = current.user.id
    audit.record(db, "user.terminated", entity="app_user", entity_id=user.id,
                 detail={"reason": body.reason, "sessions_closed": closed})
    db.commit()
    return _user_out(db, user)


@router.post("/users/{user_id}/mfa/reset", response_model=UserOut,
             summary="Remove o autenticador de um usuário (ex.: perdeu o celular)",
             description="Encerra todas as sessões. No próximo login o usuário entra sem 2FA e, se o perfil "
                         "exigir, só terá as permissões depois de cadastrar o novo autenticador.")
def reset_mfa(user_id: uuid.UUID, body: MfaResetIn, current: Current = Depends(require(P.USERS_MANAGE)),
              db: Session = Depends(get_db)):
    if user_id == current.user.id:
        raise error(403, "self_change", "Peça a outro administrador para resetar o seu 2FA.")
    user = _get_user(db, user_id)
    if not mfa_svc.is_enrolled(db, user.id) and db.get(UserMfa, user.id) is None:
        raise error(409, "mfa_not_enrolled", "Este usuário não tem 2FA ativo.")
    mfa_svc.remove(db, user.id)
    closed = sessions.revoke_all_for_user(db, user.id, "mfa_reset")
    audit.record(db, "mfa.reset_by_admin", entity="app_user", entity_id=user.id,
                 detail={"reason": body.reason, "sessions_closed": closed})
    db.commit()
    return _user_out(db, user)


# ---------------------------------------------------------------- substituições
@router.get("/delegations", response_model=list[DelegationOut], summary="Lista substituições")
def list_delegations(active: bool | None = None, current: Current = Depends(require(P.DELEGATIONS_MANAGE)),
                     db: Session = Depends(get_db)):
    now = datetime.now(UTC)
    rows = db.scalars(select(Delegation).order_by(Delegation.starts_at.desc()).limit(500))
    out = [_delegation_out(d, now) for d in rows]
    return [d for d in out if active is None or d.active == active]


@router.post("/delegations", response_model=DelegationOut, status_code=201,
             summary="Concede permissão temporária a um substituto")
def create_delegation(body: DelegationIn, current: Current = Depends(require(P.DELEGATIONS_MANAGE)),
                      db: Session = Depends(get_db)):
    if body.substitute_id == current.user.id:
        raise error(403, "self_grant", "Ninguém concede substituição a si mesmo.")
    if body.titular_id == body.substitute_id:
        raise error(422, "invalid", "Titular e substituto devem ser pessoas diferentes.")
    if body.ends_at <= body.starts_at:
        raise error(422, "invalid_period", "A data de término deve ser posterior ao início.")
    if body.ends_at <= datetime.now(UTC):
        raise error(422, "invalid_period", "A data de término já passou.")
    max_days = int(get_value(db, "delegation.max_days"))
    if body.ends_at - body.starts_at > timedelta(days=max_days):
        raise error(422, "too_long", f"Substituição limitada a {max_days} dias.")
    titular = _get_user(db, body.titular_id)
    substitute = _get_user(db, body.substitute_id)
    if not titular.is_active or not substitute.is_active:
        raise error(409, "user_terminated", "Titular e substituto precisam estar ativos.")
    if db.get(UserRole, (titular.id, body.role_code)) is None:
        raise error(422, "role_not_held", "O titular não tem o perfil que está sendo delegado.")
    _validate_roles_for(db, substitute, {body.role_code})
    d = Delegation(granted_by=current.user.id, **body.model_dump())
    db.add(d)
    db.commit()
    return _delegation_out(d, datetime.now(UTC))


@router.post("/delegations/{delegation_id}/revoke", response_model=DelegationOut,
             summary="Encerra uma substituição antes do prazo")
def revoke_delegation(delegation_id: uuid.UUID, current: Current = Depends(require(P.DELEGATIONS_MANAGE)),
                      db: Session = Depends(get_db)):
    d = db.get(Delegation, delegation_id)
    if d is None:
        raise error(404, "not_found", "Substituição não encontrada.")
    if d.revoked_at is None:
        d.revoked_at = datetime.now(UTC)
        d.revoked_by = current.user.id
        db.commit()
    return _delegation_out(d, datetime.now(UTC))


# ---------------------------------------------------------------- pedidos de acesso
@router.post("/access-requests", response_model=AccessRequestOut, status_code=201,
             summary="Solicita um perfil de acesso")
def create_access_request(body: AccessRequestIn, current: Current = Depends(require(P.ACCESS_REQUEST)),
                          db: Session = Depends(get_db)):
    _validate_roles_for(db, current.user, {body.role_code})
    if db.get(UserRole, (current.user.id, body.role_code)):
        raise error(409, "already_has_role", "Você já tem esse perfil.")
    if db.scalar(select(AccessRequest.id).where(
        AccessRequest.user_id == current.user.id, AccessRequest.role_code == body.role_code,
        AccessRequest.status == AccessRequestStatus.PENDING,
    )):
        raise error(409, "duplicate", "Já existe um pedido pendente para esse perfil.")
    ar = AccessRequest(user_id=current.user.id, **body.model_dump())
    db.add(ar)
    db.commit()
    return AccessRequestOut.model_validate(ar, from_attributes=True)


@router.get("/access-requests", response_model=list[AccessRequestOut], summary="Lista pedidos de acesso")
def list_access_requests(status: AccessRequestStatus | None = AccessRequestStatus.PENDING,
                         current: Current = Depends(require(P.USERS_MANAGE)), db: Session = Depends(get_db)):
    stmt = select(AccessRequest).order_by(AccessRequest.created_at)
    if status:
        stmt = stmt.where(AccessRequest.status == status)
    return [AccessRequestOut.model_validate(a, from_attributes=True) for a in db.scalars(stmt.limit(500))]


@router.post("/access-requests/{request_id}/decision", response_model=AccessRequestOut,
             summary="Aprova ou recusa um pedido de acesso")
def decide_access_request(request_id: uuid.UUID, body: DecisionIn,
                          current: Current = Depends(require(P.USERS_MANAGE)), db: Session = Depends(get_db)):
    ar = db.get(AccessRequest, request_id)
    if ar is None:
        raise error(404, "not_found", "Pedido não encontrado.")
    if ar.user_id == current.user.id:
        raise error(403, "self_change", "Ninguém decide o próprio pedido.")
    if ar.status != AccessRequestStatus.PENDING:
        raise error(409, "already_decided", "Pedido já decidido.")
    user = _get_user(db, ar.user_id)
    if body.approve:
        if not user.is_active:
            raise error(409, "user_terminated", "Usuário desligado.")
        _validate_roles_for(db, user, {ar.role_code})
        if db.get(UserRole, (user.id, ar.role_code)) is None:
            db.add(UserRole(user_id=user.id, role_code=ar.role_code, granted_by=current.user.id))
    ar.status = AccessRequestStatus.APPROVED if body.approve else AccessRequestStatus.REJECTED
    ar.decided_by = current.user.id
    ar.decided_at = datetime.now(UTC)
    ar.decision_comment = body.comment
    db.commit()
    return AccessRequestOut.model_validate(ar, from_attributes=True)
