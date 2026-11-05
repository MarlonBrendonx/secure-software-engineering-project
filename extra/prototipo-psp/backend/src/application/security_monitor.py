"""Registro e alerta de eventos de segurança (auditoria + contadores + alertas)."""

from __future__ import annotations

from src.domain.entities.audit import AuditEvent
from src.domain.ports.gateways.security_gateway import AlertGateway, AuditLogGateway, CounterGateway

# Valores iniciais; a equipe de segurança define os definitivos (ver etapa 4, seção 3.4).
DEFAULT_MFA_FAILURE_LIMIT = 5
DEFAULT_DENIAL_LIMIT = 10
DEFAULT_WINDOW_SECONDS = 600


class SecurityMonitor:
    def __init__(
        self,
        audit: AuditLogGateway,
        counters: CounterGateway,
        alerts: AlertGateway,
        *,
        mfa_failure_limit: int = DEFAULT_MFA_FAILURE_LIMIT,
        denial_limit: int = DEFAULT_DENIAL_LIMIT,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self._audit = audit
        self._counters = counters
        self._alerts = alerts
        self._mfa_failure_limit = mfa_failure_limit
        self._denial_limit = denial_limit
        self._window = window_seconds

    async def mfa_missing(self, username: str, *, route: str | None, origin: str | None) -> None:
        """Token de perfil privilegiado sem MFA concluído (RS02 / TS04)."""
        await self._audit.record(
            AuditEvent("mfa_ausente", username, route=route, origin=origin, detail="amr sem mfa")
        )
        await self._count_mfa_failure(username, origin)

    async def mfa_invalid(self, username: str, *, origin: str | None) -> None:
        """Código do segundo fator recusado no login."""
        await self._audit.record(
            AuditEvent("mfa_invalido", username, origin=origin, detail="código OTP recusado")
        )
        await self._count_mfa_failure(username, origin)

    async def access_denied(
        self,
        username: str,
        *,
        resource: str,
        resource_id: str,
        operation: str,
    ) -> None:
        """Recurso fora do escopo (RS03 / TS02). Fica registrado com usuário, recurso e id."""
        await self._audit.record(
            AuditEvent(
                "acesso_negado",
                username,
                resource=resource,
                resource_id=resource_id,
                detail=operation,
            )
        )
        total = await self._counters.increment(f"acesso_negado:{username}", self._window)
        if total >= self._denial_limit:
            await self._alerts.fire("acesso_negado_repetido", user=username, total=total)

    async def _count_mfa_failure(self, username: str, origin: str | None) -> None:
        total = await self._counters.increment(f"mfa_falha:{username}", self._window)
        if total >= self._mfa_failure_limit:
            await self._alerts.fire(
                "mfa_falhas_repetidas", user=username, origin=origin, total=total
            )
