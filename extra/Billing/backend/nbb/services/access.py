"""Permissões efetivas: perfis próprios + substituições ativas, respeitando MFA."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from nbb.models import Delegation, Role, RolePermission, User, UserRole, UserStatus


@dataclass
class EffectiveAccess:
    roles: set[str] = field(default_factory=set)
    # permissão -> None (perfil próprio) ou id da delegação que a concede
    permissions: dict[str, uuid.UUID | None] = field(default_factory=dict)
    # permissões que o usuário teria se a sessão tivesse segundo fator
    blocked_by_mfa: set[str] = field(default_factory=set)
    delegations: list[Delegation] = field(default_factory=list)
    # Algum perfil do usuário exige 2FA (independe de a sessão já ter feito).
    mfa_required: bool = False
    # Perfis (próprios ou recebidos em substituição) suspensos até a sessão ter 2FA.
    roles_pending_mfa: set[str] = field(default_factory=set)

    def has(self, perm: str) -> bool:
        return perm in self.permissions


def _role_perms(db: Session, role_codes: set[str]) -> dict[str, tuple[bool, set[str]]]:
    if not role_codes:
        return {}
    rows = db.execute(
        select(Role.code, Role.requires_mfa, RolePermission.permission_code)
        .join(RolePermission, RolePermission.role_code == Role.code, isouter=True)
        .where(Role.code.in_(role_codes))
    ).all()
    out: dict[str, tuple[bool, set[str]]] = {}
    for code, mfa, perm in rows:
        entry = out.setdefault(code, (mfa, set()))
        if perm:
            entry[1].add(perm)
    return out


def active_delegations(db: Session, substitute_id: uuid.UUID, now: datetime) -> list[Delegation]:
    titular = User.__table__.alias("titular")
    return list(
        db.scalars(
            select(Delegation)
            .join(titular, titular.c.id == Delegation.titular_id)
            .where(
                Delegation.substitute_id == substitute_id,
                Delegation.revoked_at.is_(None),
                Delegation.starts_at <= now,
                Delegation.ends_at > now,
                titular.c.status == UserStatus.ACTIVE,
            )
        )
    )


def effective_access(db: Session, user: User, session_mfa: bool, now: datetime,
                     mfa_for_all: bool = False) -> EffectiveAccess:
    acc = EffectiveAccess()
    own = set(db.scalars(select(UserRole.role_code).where(UserRole.user_id == user.id)))
    if not own:
        own = {"none"}
    acc.delegations = active_delegations(db, user.id, now)
    delegated = {d.role_code: d.id for d in acc.delegations}
    perms = _role_perms(db, own | set(delegated))

    def grant(role: str, source: uuid.UUID | None) -> None:
        mfa_needed, role_perms = perms.get(role, (False, set()))
        # "none" nunca exige 2FA: quem acabou de chegar precisa poder pedir acesso.
        mfa_needed = mfa_needed or (mfa_for_all and role != "none")
        acc.mfa_required |= mfa_needed
        if mfa_needed and not session_mfa:
            acc.blocked_by_mfa |= role_perms
            acc.roles_pending_mfa.add(role)
            return
        acc.roles.add(role)
        for p in role_perms:
            # Perfil próprio tem precedência sobre delegação no registro.
            if p not in acc.permissions or source is None:
                acc.permissions[p] = source

    for role in own:
        grant(role, None)
    for role, deleg_id in delegated.items():
        if role not in own:
            grant(role, deleg_id)
    acc.blocked_by_mfa -= set(acc.permissions)
    return acc
