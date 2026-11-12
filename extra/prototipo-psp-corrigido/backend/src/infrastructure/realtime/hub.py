"""Hub de tempo real em memória: avisa por WebSocket que o faturamento de um período mudou.

O evento é só um aviso de invalidação (cliente e período, sem valores). Quem recebe busca o
dado de novo pela API HTTP, que já aplica o escopo (RS03). Assim o canal não vira um caminho
paralelo para ler dados de outro cliente.

Limitação: o estado vive em um processo. Com mais de um worker, o aviso só chega a quem está
conectado no mesmo worker; em produção o hub precisaria de um barramento externo (ex.: Redis
pub/sub).
"""

from __future__ import annotations

import contextlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from fastapi import WebSocket

from src.domain.ports.gateways.security_gateway import SessionGateway, UserGateway

logger = logging.getLogger("psp.realtime")

# Único formato de canal aceito. Lista fechada: nada de canais livres nem de `:me`.
_BILLING_CHANNEL = re.compile(r"^billing:(\d{4})-(0[1-9]|1[0-2])$")

BILLING_CHANGED = "billing_changed"
CLOSE_UNAUTHORIZED = 4003


def billing_channel(year: int, month: int) -> str:
    return f"billing:{year}-{month:02d}"


def parse_billing_channel(channel: str) -> tuple[int, int] | None:
    match = _BILLING_CHANNEL.fullmatch(channel)
    return (int(match.group(1)), int(match.group(2))) if match else None


@dataclass(eq=False)
class Connection:
    """Conexão autenticada. `sid` e `exp` vêm do token validado no handshake."""

    ws: WebSocket
    username: str
    sid: str
    exp: int
    channels: set[str] = field(default_factory=set)


class RealtimeHub:
    def __init__(
        self,
        sessions: SessionGateway,
        users: UserGateway,
        *,
        max_connections_per_user: int = 5,
        max_channels_per_connection: int = 12,
    ) -> None:
        self._sessions = sessions
        self._users = users
        self._max_connections = max_connections_per_user
        self._max_channels = max_channels_per_connection
        self._connections: set[Connection] = set()

    # ── Ciclo de vida da conexão ─────────────────────────────────────

    def register(self, conn: Connection) -> bool:
        """Falso quando o usuário já atingiu o limite de conexões simultâneas."""
        mine = sum(1 for c in self._connections if c.username == conn.username)
        if mine >= self._max_connections:
            return False
        self._connections.add(conn)
        return True

    def unregister(self, conn: Connection) -> None:
        self._connections.discard(conn)

    async def close_session(self, sid: str) -> None:
        """Derruba as conexões de uma sessão (logout), sem esperar o próximo evento."""
        for conn in [c for c in self._connections if c.sid == sid]:
            await self._drop(conn)

    # ── Inscrição ────────────────────────────────────────────────────

    async def subscribe(self, conn: Connection, channel: str) -> bool:
        """Inscreve só se o canal é válido e o período está no escopo do usuário.

        Canal inválido e período negado dão a mesma resposta: o cliente não descobre
        quais períodos existem fora do escopo dele.
        """
        parsed = parse_billing_channel(channel)
        if parsed is None:
            return False
        if channel not in conn.channels and len(conn.channels) >= self._max_channels:
            return False
        scope = await self._users.get_scope(conn.username)
        if not scope.allows_period(*parsed):
            return False
        conn.channels.add(channel)
        return True

    @staticmethod
    def unsubscribe(conn: Connection, channel: str) -> None:
        conn.channels.discard(channel)

    # ── Publicação (porta BillingEventPublisher) ─────────────────────

    async def billing_changed(self, client_uuid: UUID, year: int, month: int) -> None:
        channel = billing_channel(year, month)
        try:
            for conn in [c for c in self._connections if channel in c.channels]:
                await self._deliver(conn, channel, client_uuid, year, month)
        except Exception:
            # A alteração já foi gravada; falha de entrega não pode virar erro na API.
            logger.exception("Falha ao publicar evento de faturamento")

    async def _deliver(
        self, conn: Connection, channel: str, client_uuid: UUID, year: int, month: int
    ) -> None:
        try:
            # O token só vale uma vez no handshake; por isso a sessão e o prazo são
            # conferidos a cada entrega, para logout e expiração cortarem o fluxo.
            session = await self._sessions.get(conn.sid)
            if session is None or session.username != conn.username or time.time() >= conn.exp:
                await self._drop(conn)
                return

            # O escopo é relido a cada entrega: uma redução de acesso vale na hora.
            scope = await self._users.get_scope(conn.username)
            if not (scope.allows_client(client_uuid) and scope.allows_period(year, month)):
                return

            await conn.ws.send_text(
                json.dumps(
                    {
                        "channel": channel,
                        "event": BILLING_CHANGED,
                        "data": {"client_uuid": str(client_uuid)},
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )
            )
        except Exception:
            # Uma conexão quebrada não pode impedir a entrega às demais.
            logger.warning("Conexão de tempo real descartada após falha de envio")
            await self._drop(conn)

    async def _drop(self, conn: Connection) -> None:
        self._connections.discard(conn)
        # A conexão pode já estar fechada; nesse caso não há o que fazer.
        with contextlib.suppress(Exception):
            await conn.ws.close(code=CLOSE_UNAUTHORIZED)
