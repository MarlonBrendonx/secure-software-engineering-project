"""Autenticação por requisição: token → sessão → perfil → MFA (RS02 / Prática 2).

Qualquer exceção ou dado ausente resulta em negação; nunca em acesso liberado (RS06).
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from src.application.actor import Actor
from src.application.security_monitor import SecurityMonitor
from src.domain.entities.session import TokenClaims
from src.domain.entities.user import User
from src.domain.exceptions import ForbiddenError, UnauthenticatedError
from src.domain.ports.gateways.security_gateway import SessionGateway, UserGateway
from src.domain.ports.services.token_service import TokenService
from src.domain.value_objects.user_role import PRIVILEGED_ROLES


@dataclass(frozen=True)
class AuthenticatedUser:
    actor: Actor
    user: User
    claims: TokenClaims


class Authenticator:
    def __init__(
        self,
        tokens: TokenService,
        users: UserGateway,
        sessions: SessionGateway,
        monitor: SecurityMonitor,
    ) -> None:
        self._tokens = tokens
        self._users = users
        self._sessions = sessions
        self._monitor = monitor

    async def identify(self, token: str | None) -> AuthenticatedUser:
        """Valida token e sessão, sem exigir perfil nem MFA (ex.: consulta da própria sessão)."""
        if not token:
            raise UnauthenticatedError("Missing or invalid authorization", "token_ausente")

        claims = self._tokens.decode_access(token)

        # O token sozinho não basta: a sessão registrada no servidor é o que permite revogar.
        session = await self._sessions.get(claims.sid)
        if session is None or session.username != claims.sub:
            raise UnauthenticatedError("Sessão inválida ou revogada", "sessao_invalida")

        user = await self._users.get_by_username(claims.sub)
        if user is None:
            raise UnauthenticatedError("Sessão inválida ou revogada", "sessao_invalida")

        # O perfil vem do cadastro e não do token: assim uma troca de perfil vale na hora.
        return AuthenticatedUser(Actor(user.username, str(user.role)), user, claims)

    async def authorize(
        self,
        token: str | None,
        *,
        allowed_roles: Collection[str],
        route: str,
        origin: str | None = None,
    ) -> AuthenticatedUser:
        auth = await self.identify(token)

        if auth.actor.role not in allowed_roles:
            raise ForbiddenError("Permissão insuficiente para esta operação")

        if auth.user.role in PRIVILEGED_ROLES:
            # Confere o claim do token e o registro da sessão: quem só forja o token não passa.
            session = await self._sessions.get(auth.claims.sid)
            mfa_ok = auth.claims.mfa_completed and session is not None and "mfa" in session.amr
            if not mfa_ok:
                await self._monitor.mfa_missing(auth.user.username, route=route, origin=origin)
                raise UnauthenticatedError("MFA necessário para este perfil", "mfa_necessario")

        return auth
