"""Regras de detecção da etapa 6 (D01 a D08, D12 e D13).

As regras olham os eventos no momento em que são gravados na auditoria: o `DetectingAuditLog`
envolve o gateway de auditoria e entrega cada evento ao `DetectionEngine`. Assim, um evento
gravado por qualquer caso de uso entra na contagem, inclusive as negações de período da
listagem, que antes não passavam pelo `SecurityMonitor` (lacuna apontada em D02).

Os limites e as janelas são os valores iniciais da tabela de regras da etapa 6. Cada alerta é
disparado uma vez por janela, quando a contagem atinge o limite, e não a cada evento seguinte.

Ficam fora deste módulo: D09 (falta registrar o volume das leituras), D10 (a falha do guard é
justamente a do Redis, onde a regra gravaria), D11 (não há outbox) e D14 (não há carga do ERP).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.domain.entities.audit import AuditEvent
from src.domain.ports.gateways.detection_gateway import DetectionStateGateway
from src.domain.ports.gateways.security_gateway import (
    AlertGateway,
    AuditLogGateway,
    CounterGateway,
    UserGateway,
)
from src.domain.value_objects.user_role import PRIVILEGED_ROLES

logger = logging.getLogger("psp.security")


@dataclass(frozen=True)
class DetectionLimits:
    """Valores iniciais das regras. A calibração depende do volume real de uso."""

    window_seconds: int = 600
    mfa_failures: int = 5  # D01
    access_denials: int = 10  # D02
    login_failures_per_user: int = 10  # D03
    login_failures_users_per_origin: int = 5  # D03
    # D04: por quanto tempo a conta fica marcada depois de D03. O roteiro não fixa o valor.
    failed_login_mark_seconds: int = 3600
    origin_lookback_seconds: int = 30 * 24 * 3600  # D04
    invalid_tokens_per_origin: int = 3  # D06
    rule_changes: int = 5  # D08
    rule_changes_window_seconds: int = 3600  # D08
    ws_refusals_per_origin: int = 3  # D12
    rate_limited_per_origin: int = 101  # D13: "mais de 100"


class DetectionEngine:
    def __init__(
        self,
        counters: CounterGateway,
        state: DetectionStateGateway,
        alerts: AlertGateway,
        users: UserGateway,
        limits: DetectionLimits | None = None,
    ) -> None:
        self._counters = counters
        self._state = state
        self._alerts = alerts
        self._users = users
        self._limits = limits or DetectionLimits()

    async def observe(self, event: AuditEvent) -> None:
        """Avalia o evento. Uma falha aqui fica no log e não desfaz a operação já gravada."""
        try:
            await self._dispatch(event)
        except Exception:
            logger.exception("Falha ao avaliar as regras de detecção para %s", event.type)

    async def rate_limited(self, origin: str) -> None:
        """D13. Não passa pela auditoria: uma varredura geraria milhares de eventos e
        empurraria para fora da lista os registros que interessam à investigação."""
        try:
            total = await self._counters.increment(f"d13:{origin}", self._limits.window_seconds)
            if total == self._limits.rate_limited_per_origin:
                await self._fire(
                    "D13",
                    "varredura_limite_excedido",
                    "Baixa",
                    "Infraestrutura, Segurança",
                    origin=origin,
                    total=total,
                )
        except Exception:
            logger.exception("Falha ao avaliar a regra D13")

    async def _dispatch(self, event: AuditEvent) -> None:
        handler = {
            "mfa_invalido": self._d01,
            "mfa_ausente": self._d01,
            "acesso_negado": self._d02,
            "login_falha": self._d03,
            "login_sucesso": self._d04,
            "refresh_reutilizado": self._d05,
            "token_recusado": self._d06,
            "autoaprovacao_negada": self._d07,
            "regra_servico_atualizada": self._d08,
            "regra_servico_excluida": self._d08,
            "websocket_origem_recusada": self._d12,
        }.get(event.type)
        if handler is not None:
            await handler(event)

    async def _count(self, key: str, window: int | None = None) -> int:
        return await self._counters.increment(key, window or self._limits.window_seconds)

    async def _fire(
        self, rule: str, name: str, severity: str, destination: str, **context: object
    ) -> None:
        await self._alerts.fire(
            name, regra=rule, severidade=severity, destino=destination, **context
        )

    async def _d01(self, event: AuditEvent) -> None:
        total = await self._count(f"d01:{event.user}")
        if total == self._limits.mfa_failures:
            await self._fire(
                "D01",
                "mfa_falhas_repetidas",
                "Alta",
                "Segurança",
                user=event.user,
                origin=event.origin,
                total=total,
            )

    async def _d02(self, event: AuditEvent) -> None:
        total = await self._count(f"d02:{event.user}")
        if total == self._limits.access_denials:
            await self._fire(
                "D02",
                "acesso_negado_repetido",
                "Alta",
                "Segurança",
                user=event.user,
                total=total,
            )

    async def _d03(self, event: AuditEvent) -> None:
        limits = self._limits
        # A marca alimenta D04: um login com sucesso logo depois das falhas é suspeito.
        await self._state.mark(f"d03:{event.user}", limits.failed_login_mark_seconds)

        total = await self._count(f"d03:{event.user}")
        if total == limits.login_failures_per_user:
            await self._fire(
                "D03",
                "login_falhas_repetidas",
                "Média",
                "Segurança",
                user=event.user,
                origin=event.origin,
                total=total,
            )

        if event.origin and event.user:
            users = await self._state.count_distinct(
                f"d03:{event.origin}", event.user, limits.window_seconds
            )
            if users == limits.login_failures_users_per_origin:
                # Mesma origem contra várias contas: sobe para Alta (tabela de severidade).
                # O alerta não lista os usuários, para não revelar quais contas existem.
                await self._fire(
                    "D03",
                    "login_falhas_por_origem",
                    "Alta",
                    "Segurança",
                    origin=event.origin,
                    usuarios_distintos=users,
                )

    async def _d04(self, event: AuditEvent) -> None:
        if not event.user:
            return
        user = await self._users.get_by_username(event.user)
        if user is None or user.role not in PRIVILEGED_ROLES:
            return

        after_failures = await self._state.is_marked(f"d03:{event.user}")
        seen_before, history = (False, 0)
        if event.origin:
            seen_before, history = await self._state.remember_origin(
                event.user, event.origin, self._limits.origin_lookback_seconds
            )
        # Sem histórico, o primeiro login só estabelece a linha de base e não gera alerta.
        new_origin = event.origin is not None and history > 0 and not seen_before

        if after_failures or new_origin:
            await self._fire(
                "D04",
                "login_privilegiado_suspeito",
                "Crítica",
                "Segurança",
                user=event.user,
                origin=event.origin,
                sid=event.sid,
                motivo="apos_falhas_de_senha" if after_failures else "origem_nova",
            )

    async def _d05(self, event: AuditEvent) -> None:
        await self._fire(
            "D05",
            "refresh_token_reutilizado",
            "Alta",
            "Segurança",
            user=event.user,
            origin=event.origin,
            sid=event.sid,
        )

    async def _d06(self, event: AuditEvent) -> None:
        if event.detail == "sessao_invalida":
            # Assinatura válida com sessão inexistente ou revogada: quem tem a chave ou guardou
            # um token de sessão encerrada. Tratado como possível vazamento da chave.
            await self._fire(
                "D06",
                "token_valido_sessao_desconhecida",
                "Crítica",
                "Segurança",
                user=event.user,
                origin=event.origin,
            )
        elif event.detail == "token_invalido" and event.origin:
            total = await self._count(f"d06:{event.origin}")
            if total == self._limits.invalid_tokens_per_origin:
                await self._fire(
                    "D06",
                    "tokens_invalidos_repetidos",
                    "Média",
                    "Segurança",
                    origin=event.origin,
                    total=total,
                )

    async def _d07(self, event: AuditEvent) -> None:
        await self._fire(
            "D07",
            "autoaprovacao_recusada",
            "Alta",
            "Segurança, Negócio",
            user=event.user,
            lancamento=event.resource_id,
            transicao=event.detail,
        )

    async def _d08(self, event: AuditEvent) -> None:
        total = await self._count(f"d08:{event.user}", self._limits.rule_changes_window_seconds)
        if total == self._limits.rule_changes:
            await self._fire(
                "D08",
                "alteracoes_de_regra_repetidas",
                "Média",
                "Negócio, Segurança",
                user=event.user,
                total=total,
            )

    async def _d12(self, event: AuditEvent) -> None:
        if not event.origin:
            return
        total = await self._count(f"d12:{event.origin}")
        if total == self._limits.ws_refusals_per_origin:
            await self._fire(
                "D12",
                "websocket_origem_recusada_repetida",
                "Média",
                "Segurança",
                origin=event.origin,
                pagina=event.detail,
                total=total,
            )


class DetectingAuditLog:
    """Gateway de auditoria que entrega cada evento gravado às regras de detecção."""

    def __init__(self, inner: AuditLogGateway, engine: DetectionEngine) -> None:
        self._inner = inner
        self._engine = engine

    async def record(self, event: AuditEvent) -> None:
        # Primeiro grava: se a gravação falhar, o erro sobe como antes e nada é avaliado.
        await self._inner.record(event)
        await self._engine.observe(event)

    async def list_recent(self, limit: int = 50) -> list[AuditEvent]:
        return await self._inner.list_recent(limit)
