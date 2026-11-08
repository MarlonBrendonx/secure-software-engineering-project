"""WebSocket de tempo real: autenticação, escopo e revogação (RS02, RS03, RS06).

Os testes são síncronos de propósito: o `TestClient` do Starlette é o que suporta WebSocket
e roda o app no próprio laço de eventos. O Redis falso nasce sem laço, então serve nos dois.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import fakeredis.aioredis
import pytest
from fastapi import APIRouter, WebSocket
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.core.config import Settings
from src.domain.entities.session import AuthSession
from src.domain.entities.user import UserScope
from src.infrastructure.persistence.redis.seed import (
    CLIENT_ALFA,
    CLIENT_BETA,
    CLIENT_GAMA,
)
from src.infrastructure.realtime.hub import Connection, RealtimeHub, parse_billing_channel
from src.presentation.api.deps import assert_all_routes_have_policy
from src.presentation.api.main import create_app
from tests.conftest import ALFA_FIXED_RULE, GAMA_FIXED_RULE, OTP, PASSWORD, create_payload

CHANNEL = "billing:2026-09"


@pytest.fixture
def web() -> Iterator[TestClient]:
    app = create_app(Settings(RATE_LIMIT_ENABLED=False), fakeredis.aioredis.FakeRedis())  # type: ignore[call-arg]
    with TestClient(app) as client:
        yield client


def _origin(web: TestClient) -> dict[str, str]:
    return {"origin": web.app.state.container.settings.CORS_ORIGINS[0]}  # type: ignore[attr-defined]


def _login(web: TestClient, username: str, *, mfa: bool = False) -> str:
    body = {"username": username, "password": PASSWORD}
    if mfa:
        body["otp"] = OTP
    resp = web.post("/v1/auth/login", json=body)
    assert resp.status_code == 200, resp.text
    web.cookies.clear()
    return str(resp.json()["access_token"])


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_item(web: TestClient, token: str, client_uuid: Any, rule: Any) -> None:
    resp = web.post(
        "/v1/billing/items",
        json=create_payload(client_uuid=client_uuid, rule=rule),
        headers=_bearer(token),
    )
    assert resp.status_code == 201, resp.text


def _auth(ws: Any, token: str, channels: list[str] | None = None) -> dict[str, Any]:
    ws.send_text(json.dumps({"type": "auth", "token": token, "channels": channels or []}))
    return json.loads(ws.receive_text())  # type: ignore[no-any-return]


# ── Autenticação ─────────────────────────────────────────────────────


def test_analista_autentica_e_recebe_aviso_do_proprio_escopo(web: TestClient) -> None:
    analyst = _login(web, "analyst")
    admin = _login(web, "admin", mfa=True)

    with web.websocket_connect("/ws", headers=_origin(web)) as ws:
        assert _auth(ws, analyst, [CHANNEL]) == {"type": "auth_ok", "sub": "analyst"}

        _create_item(web, admin, CLIENT_ALFA, ALFA_FIXED_RULE)
        event = json.loads(ws.receive_text())

    assert event["channel"] == CHANNEL
    assert event["event"] == "billing_changed"
    # O aviso só invalida: nenhum valor ou dado do lançamento viaja pelo canal.
    assert event["data"] == {"client_uuid": str(CLIENT_ALFA)}


def test_origem_fora_da_lista_e_recusada(web: TestClient) -> None:
    with (
        pytest.raises(WebSocketDisconnect),
        web.websocket_connect("/ws", headers={"origin": "https://site-malicioso.example"}),
    ):
        pass


def test_sem_origem_e_recusada(web: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect), web.websocket_connect("/ws"):
        pass


def test_token_invalido_fecha_com_4003(web: TestClient) -> None:
    with web.websocket_connect("/ws", headers=_origin(web)) as ws:
        reply = _auth(ws, "token.invalido.qualquer")
        assert reply["type"] == "auth_error"
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_text()
    assert closed.value.code == 4003


def test_perfil_privilegiado_sem_otp_e_recusado(web: TestClient) -> None:
    manager_sem_mfa = _login(web, "manager")

    with web.websocket_connect("/ws", headers=_origin(web)) as ws:
        assert _auth(ws, manager_sem_mfa)["type"] == "auth_error"
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_text()
    assert closed.value.code == 4003


def test_primeira_mensagem_que_nao_e_auth_fecha_com_4001(web: TestClient) -> None:
    with web.websocket_connect("/ws", headers=_origin(web)) as ws:
        ws.send_text(f"subscribe:{CHANNEL}")
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_text()
    assert closed.value.code == 4001


# ── Escopo ───────────────────────────────────────────────────────────


def test_analista_nao_recebe_aviso_de_cliente_fora_do_escopo(web: TestClient) -> None:
    analyst = _login(web, "analyst")
    admin = _login(web, "admin", mfa=True)

    with web.websocket_connect("/ws", headers=_origin(web)) as ws:
        _auth(ws, analyst, [CHANNEL])

        # A Gama vem primeiro. Se o aviso dela vazasse, seria a primeira mensagem recebida.
        _create_item(web, admin, CLIENT_GAMA, GAMA_FIXED_RULE)
        _create_item(web, admin, CLIENT_ALFA, ALFA_FIXED_RULE)
        event = json.loads(ws.receive_text())

    assert event["data"]["client_uuid"] == str(CLIENT_ALFA)


# ── Revogação ────────────────────────────────────────────────────────


def test_logout_derruba_a_conexao(web: TestClient) -> None:
    analyst = _login(web, "analyst")

    with web.websocket_connect("/ws", headers=_origin(web)) as ws:
        _auth(ws, analyst, [CHANNEL])
        assert web.post("/v1/auth/logout", headers=_bearer(analyst)).status_code == 200
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_text()
    assert closed.value.code == 4003


# ── RS06: toda rota declara a política de acesso ─────────────────────


def test_rota_websocket_sem_politica_derruba_a_inicializacao() -> None:
    router = APIRouter()

    @router.websocket("/ws-sem-politica")
    async def sem_politica(ws: WebSocket) -> None:
        await ws.close()

    with pytest.raises(RuntimeError, match="ws-sem-politica"):
        assert_all_routes_have_policy([("", router)])


# ── Hub: inscrição ───────────────────────────────────────────────────


class _Users:
    def __init__(self, scope: UserScope) -> None:
        self._scope = scope

    async def get_by_username(self, username: str) -> None:
        return None

    async def get_scope(self, username: str) -> UserScope:
        return self._scope


class _Sessions:
    async def create(self, session: AuthSession, ttl_seconds: int) -> None: ...

    async def get(self, sid: str) -> AuthSession | None:
        return None

    async def revoke(self, sid: str) -> None: ...


def _conn() -> Connection:
    return Connection(ws=None, username="analyst", sid="s", exp=2**31)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "channel",
    [
        "notifications:me",
        "billing:me",
        "billing:2026-13",
        "billing:2026-00",
        "billing:2026-9",
        "billing:2026-09:x",
        "billing:2026-09\n",
        "",
        "*",
    ],
)
async def test_hub_so_aceita_canal_de_periodo_bem_formado(channel: str) -> None:
    assert parse_billing_channel(channel) is None
    hub = RealtimeHub(_Sessions(), _Users(UserScope(periods=frozenset({"*"}))))  # type: ignore[arg-type]
    conn = _conn()
    assert await hub.subscribe(conn, channel) is False
    assert conn.channels == set()


async def test_hub_nega_inscricao_em_periodo_fora_do_escopo() -> None:
    scope = UserScope(clients=frozenset({str(CLIENT_BETA)}), periods=frozenset({"2026-09"}))
    hub = RealtimeHub(_Sessions(), _Users(scope))  # type: ignore[arg-type]
    conn = _conn()

    assert await hub.subscribe(conn, "billing:2026-10") is False
    assert await hub.subscribe(conn, "billing:2026-09") is True
    assert conn.channels == {"billing:2026-09"}


async def test_hub_limita_canais_e_conexoes_por_usuario() -> None:
    scope = UserScope(periods=frozenset({"*"}))
    hub = RealtimeHub(
        _Sessions(),  # type: ignore[arg-type]
        _Users(scope),  # type: ignore[arg-type]
        max_connections_per_user=1,
        max_channels_per_connection=1,
    )
    first, second = _conn(), _conn()

    assert hub.register(first) is True
    assert hub.register(second) is False
    assert await hub.subscribe(first, "billing:2026-09") is True
    assert await hub.subscribe(first, "billing:2026-10") is False
