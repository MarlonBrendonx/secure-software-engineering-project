import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nbb.models.base import Base, created_at_col, utcnow, uuid_pk


class UserSource(enum.StrEnum):
    SSO = "sso"      # entra por Google, Microsoft ou provedor corporativo (OIDC)
    LOCAL = "local"  # usuário e senha cadastrados no sistema (ex.: auditoria externa)


class UserStatus(enum.StrEnum):
    ACTIVE = "active"
    TERMINATED = "terminated"


class User(Base):
    __tablename__ = "app_user"
    __audited__ = True
    __audit_redact__ = frozenset({"password_hash"})

    id: Mapped[uuid.UUID] = uuid_pk()
    login: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254))
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=UserStatus.ACTIVE)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = created_at_col()
    terminated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terminated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))

    roles: Mapped[list["UserRole"]] = relationship(
        back_populates="user", foreign_keys="UserRole.user_id", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE


class Permission(Base):
    __tablename__ = "permission"
    code: Mapped[str] = mapped_column(String(60), primary_key=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)


class Role(Base):
    __tablename__ = "role"
    __audited__ = True

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    requires_mfa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    permissions: Mapped[list["RolePermission"]] = relationship(cascade="all, delete-orphan")


class RolePermission(Base):
    __tablename__ = "role_permission"
    __audited__ = True

    role_code: Mapped[str] = mapped_column(ForeignKey("role.code"), primary_key=True)
    permission_code: Mapped[str] = mapped_column(ForeignKey("permission.code"), primary_key=True)


class UserRole(Base):
    __tablename__ = "user_role"
    __audited__ = True

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), primary_key=True)
    role_code: Mapped[str] = mapped_column(ForeignKey("role.code"), primary_key=True)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    granted_at: Mapped[datetime] = created_at_col()

    user: Mapped[User] = relationship(back_populates="roles", foreign_keys=[user_id])


class Delegation(Base):
    """Substituição em férias: o substituto recebe temporariamente um perfil
    do titular. As ações continuam registradas no nome do substituto, com a
    referência à delegação usada."""

    __tablename__ = "delegation"
    __audited__ = True

    id: Mapped[uuid.UUID] = uuid_pk()
    titular_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    substitute_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    role_code: Mapped[str] = mapped_column(ForeignKey("role.code"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    document_ref: Mapped[str | None] = mapped_column(String(200))
    granted_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    created_at: Mapped[datetime] = created_at_col()
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))

    def is_active_at(self, when: datetime) -> bool:
        return self.revoked_at is None and self.starts_at <= when < self.ends_at


class AccessRequestStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AccessRequest(Base):
    __tablename__ = "access_request"
    __audited__ = True

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    role_code: Mapped[str] = mapped_column(ForeignKey("role.code"), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AccessRequestStatus.PENDING)
    created_at: Mapped[datetime] = created_at_col()
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_comment: Mapped[str | None] = mapped_column(Text)


class AuthSession(Base):
    """Sessão de login. O access token (JWT) referencia esta linha pelo `sid`;
    revogá-la derruba o usuário na próxima requisição."""

    __tablename__ = "auth_session"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    auth_method: Mapped[str] = mapped_column(String(20), nullable=False)
    mfa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    refresh_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prev_refresh_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = created_at_col()
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoke_reason: Mapped[str | None] = mapped_column(String(60))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    # 'pending_mfa': a senha/SSO foi aceita mas falta o código do autenticador.
    stage: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    mfa_ticket_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    mfa_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mfa_method: Mapped[str | None] = mapped_column(String(20))  # totp | recovery | idp
    provider: Mapped[str | None] = mapped_column(String(40))


class UserIdentity(Base):
    """Conta de um provedor externo (Google, Microsoft…) vinculada a um usuário."""

    __tablename__ = "user_identity"
    __audited__ = True

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254))
    created_at: Mapped[datetime] = created_at_col()
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserMfa(Base):
    __tablename__ = "user_mfa"
    __audited__ = True
    __audit_redact__ = frozenset({"totp_secret_enc"})

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), primary_key=True)
    totp_secret_enc: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_step: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = created_at_col()


class MfaRecoveryCode(Base):
    __tablename__ = "mfa_recovery_code"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = created_at_col()
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PasswordReset(Base):
    __tablename__ = "password_reset"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = created_at_col()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
