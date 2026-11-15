"""Registro de eventos de segurança.

Na etapa 6 a contagem e os alertas saíram daqui e foram para `src.application.detection`.
O monitor só grava os eventos; as regras os avaliam quando chegam à auditoria. Os métodos que
já existiam mantêm a assinatura, então `Authenticator`, `LoginUseCase` e `ResourceAccessGuard`
não mudam.
"""

from __future__ import annotations

from src.application.detection import DetectionEngine
from src.domain.entities.audit import AuditEvent
from src.domain.ports.gateways.security_gateway import AuditLogGateway


class SecurityMonitor:
    def __init__(self, audit: AuditLogGateway, engine: DetectionEngine) -> None:
        self._audit = audit
        self._engine = engine

    async def mfa_missing(self, username: str, *, route: str | None, origin: str | None) -> None:
        """Token de perfil privilegiado sem MFA concluído (RS02 / TS04). Entra em D01."""
        await self._audit.record(
            AuditEvent(
                "mfa_ausente",
                username,
                route=route,
                origin=origin,
                detail="amr sem mfa",
                result="negado",
            )
        )

    async def mfa_invalid(self, username: str, *, origin: str | None) -> None:
        """Código do segundo fator recusado no login. Entra em D01."""
        await self._audit.record(
            AuditEvent(
                "mfa_invalido",
                username,
                origin=origin,
                detail="código OTP recusado",
                result="negado",
            )
        )

    async def access_denied(
        self,
        username: str,
        *,
        resource: str,
        resource_id: str,
        operation: str,
    ) -> None:
        """Recurso fora do escopo (RS03 / TS02). Entra em D02."""
        await self._audit.record(
            AuditEvent(
                "acesso_negado",
                username,
                resource=resource,
                resource_id=resource_id,
                detail=operation,
                result="negado",
            )
        )

    async def token_rejected(self, reason: str, *, user: str | None = None) -> None:
        """Token recusado (grupo 2 dos eventos mínimos). Entra em D06.

        `reason` é o motivo devolvido ao cliente: `token_invalido` (assinatura, algoritmo,
        emissor, audiência ou claims), `token_expirado` ou `sessao_invalida` (assinatura
        válida, mas sessão inexistente ou revogada).
        """
        await self._audit.record(AuditEvent("token_recusado", user, detail=reason, result="negado"))

    async def refresh_reused(self, user: str | None, *, sid: str | None) -> None:
        """Refresh token já trocado foi apresentado de novo (V01). Entra em D05."""
        await self._audit.record(AuditEvent("refresh_reutilizado", user, sid=sid, result="negado"))

    async def websocket_origin_refused(self, origin: str | None, *, page: str | None) -> None:
        """WebSocket fechado com 4403 por `Origin` fora da lista. Entra em D12."""
        await self._audit.record(
            AuditEvent(
                "websocket_origem_recusada",
                None,
                route="/ws",
                origin=origin,
                detail=page,
                result="negado",
            )
        )

    async def rate_limited(self, origin: str) -> None:
        """Requisição recusada com 429. Só alimenta o contador de D13, sem evento."""
        await self._engine.rate_limited(origin)
