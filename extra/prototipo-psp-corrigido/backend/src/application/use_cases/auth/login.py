"""Casos de uso de sessão: login, renovação e encerramento."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from src.application.security_monitor import SecurityMonitor
from src.domain.entities.audit import AuditEvent
from src.domain.entities.session import AuthSession
from src.domain.entities.user import User
from src.domain.exceptions import UnauthenticatedError
from src.domain.ports.gateways.security_gateway import AuditLogGateway, SessionGateway, UserGateway
from src.domain.ports.services.identity_provider import IdentityProvider
from src.domain.ports.services.token_service import IssuedTokens, TokenService


@dataclass(frozen=True)
class LoginCommand:
    username: str
    password: str
    otp: str | None = None
    origin: str | None = None


@dataclass(frozen=True)
class LoginResult:
    tokens: IssuedTokens
    user: User
    amr: list[str]


class LoginUseCase:
    def __init__(
        self,
        users: UserGateway,
        sessions: SessionGateway,
        tokens: TokenService,
        identity: IdentityProvider,
        audit: AuditLogGateway,
        monitor: SecurityMonitor,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._tokens = tokens
        self._identity = identity
        self._audit = audit
        self._monitor = monitor

    async def execute(self, cmd: LoginCommand) -> LoginResult:
        user = await self._users.get_by_username(cmd.username)
        password_ok = self._identity.check_password(cmd.username, cmd.password)

        # Mesma resposta para usuário inexistente e senha errada (RF-AUTH-03).
        if user is None or not password_ok:
            await self._audit.record(
                AuditEvent("login_falha", cmd.username, origin=cmd.origin, detail="credenciais")
            )
            raise UnauthenticatedError("Nome ou senha inválidos", "credenciais_invalidas")

        amr = ["pwd"]
        if cmd.otp:
            if not self._identity.check_second_factor(cmd.username, cmd.otp):
                await self._monitor.mfa_invalid(cmd.username, origin=cmd.origin)
                raise UnauthenticatedError("Código MFA inválido", "mfa_invalido")
            amr.append("mfa")

        session = AuthSession(sid=uuid4().hex, username=user.username, amr=amr)
        tokens = self._tokens.issue(
            username=user.username,
            sid=session.sid,
            amr=amr,
            role=str(user.role),
            display_name=user.display_name,
            email=user.email,
        )
        await self._sessions.create(session, tokens.refresh_expires_in)
        await self._audit.record(
            AuditEvent(
                "login_sucesso", user.username, origin=cmd.origin, detail=f"amr={','.join(amr)}"
            )
        )
        return LoginResult(tokens, user, amr)


class RefreshSessionUseCase:
    def __init__(
        self,
        users: UserGateway,
        sessions: SessionGateway,
        tokens: TokenService,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._tokens = tokens

    async def execute(self, refresh_token: str) -> IssuedTokens:
        claims = self._tokens.decode_refresh(refresh_token)
        session = await self._sessions.get(claims.sid)
        user = await self._users.get_by_username(claims.sub)
        if session is None or user is None or session.username != claims.sub:
            raise UnauthenticatedError("Sessão inválida ou revogada", "sessao_invalida")

        # O `amr` vem da sessão do servidor: renovar não promove um login sem MFA.
        return self._tokens.issue(
            username=user.username,
            sid=session.sid,
            amr=session.amr,
            role=str(user.role),
            display_name=user.display_name,
            email=user.email,
        )


class LogoutUseCase:
    def __init__(self, sessions: SessionGateway, audit: AuditLogGateway) -> None:
        self._sessions = sessions
        self._audit = audit

    async def execute(self, username: str, sid: str) -> None:
        await self._sessions.revoke(sid)
        await self._audit.record(AuditEvent("logout", username))
