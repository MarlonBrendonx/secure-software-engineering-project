"""WebSocket de tempo real: avisa quando o faturamento de um período mudou.

Fluxo:
    1. O cliente conecta em ``/ws`` sem token na URL (URL vai para log de proxy).
    2. Envia em até 5 s ``{"type": "auth", "token": "...", "channels": ["billing:2026-09"]}``.
    3. O servidor responde ``{"type": "auth_ok", "sub": "<usuário>"}`` ou fecha com 4003.

Depois, o cliente pode enviar ``subscribe:<canal>`` e ``unsubscribe:<canal>``. A conexão
fecha com 4003 quando o token expira; o front renova o token e reconecta.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.infrastructure.realtime.hub import CLOSE_UNAUTHORIZED, Connection, RealtimeHub
from src.presentation.api.container import Container
from src.presentation.api.deps import BILLING_ROLES, ws_authenticated

logger = logging.getLogger("psp.api.ws")
router = APIRouter()

AUTH_TIMEOUT_SECONDS = 5
CLOSE_BAD_AUTH_MESSAGE = 4001
CLOSE_FORBIDDEN_ORIGIN = 4403
CLOSE_TOO_MANY = 1008
CLOSE_TOO_BIG = 1009
# Mensagens legítimas têm poucas dezenas de bytes; o teto barra abuso de memória.
MAX_AUTH_MESSAGE_BYTES = 8192
MAX_COMMAND_BYTES = 256


async def _read_auth(ws: WebSocket) -> dict[str, object] | None:
    """Lê a mensagem inicial. Devolve `None` (e fecha) se faltar, estourar o prazo ou for ruim."""
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=AUTH_TIMEOUT_SECONDS)
    except TimeoutError:
        await ws.close(code=CLOSE_BAD_AUTH_MESSAGE)
        return None
    except WebSocketDisconnect:
        return None

    if len(raw) > MAX_AUTH_MESSAGE_BYTES:
        await ws.close(code=CLOSE_TOO_BIG)
        return None
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        msg = None
    if not isinstance(msg, dict) or msg.get("type") != "auth":
        await ws.close(code=CLOSE_BAD_AUTH_MESSAGE)
        return None
    return msg


@router.websocket("/ws")
@ws_authenticated
async def realtime(ws: WebSocket) -> None:
    container: Container = ws.app.state.container

    # O CORS não vale para WebSocket: sem esta conferência, qualquer site aberto no navegador
    # do usuário poderia abrir a conexão. Navegador sempre envia Origin; sem ele, nega.
    if ws.headers.get("origin") not in container.settings.CORS_ORIGINS:
        await ws.close(code=CLOSE_FORBIDDEN_ORIGIN)
        return

    await ws.accept()
    msg = await _read_auth(ws)
    if msg is None:
        return

    token = msg.get("token")
    try:
        # Mesma verificação das rotas HTTP de faturamento: token, sessão, perfil e MFA.
        auth = await container.authenticator.authorize(
            token if isinstance(token, str) else None,
            allowed_roles=BILLING_ROLES,
            route="/ws",
            origin=ws.client.host if ws.client else None,
        )
    except Exception:
        # Qualquer falha nega. A resposta é genérica para não distinguir a causa ao cliente.
        await ws.send_json({"type": "auth_error", "reason": "Não autorizado"})
        await ws.close(code=CLOSE_UNAUTHORIZED)
        return

    hub = container.realtime
    conn = Connection(ws, auth.user.username, auth.claims.sid, auth.claims.exp)
    if not hub.register(conn):
        await ws.send_json({"type": "auth_error", "reason": "Limite de conexões atingido"})
        await ws.close(code=CLOSE_TOO_MANY)
        return

    try:
        channels = msg.get("channels")
        for channel in channels if isinstance(channels, list) else []:
            if isinstance(channel, str):
                await hub.subscribe(conn, channel)
        await ws.send_json({"type": "auth_ok", "sub": conn.username})
        await _serve(ws, hub, conn)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Falha na conexão de tempo real")
    finally:
        hub.unregister(conn)


async def _serve(ws: WebSocket, hub: RealtimeHub, conn: Connection) -> None:
    while True:
        # O token deixa de valer em `exp`; a conexão acaba junto para não sobreviver à sessão.
        remaining = conn.exp - time.time()
        try:
            text = await asyncio.wait_for(ws.receive_text(), timeout=max(remaining, 0))
        except TimeoutError:
            await ws.close(code=CLOSE_UNAUTHORIZED)
            return

        if len(text) > MAX_COMMAND_BYTES:
            await ws.close(code=CLOSE_TOO_BIG)
            return
        command, _, channel = text.partition(":")
        if command == "subscribe":
            await hub.subscribe(conn, channel.strip())
        elif command == "unsubscribe":
            hub.unsubscribe(conn, channel.strip())
