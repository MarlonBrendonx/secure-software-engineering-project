"""Etapa 6 — validação das regras de detecção e dos campos de correlação.

Cada teste gera os eventos de entrada pela API, como um usuário faria, e confere o evento
gravado e o alerta disparado em `psp:alerts`. O alerta só dispara uma vez por janela, então os
testes conferem também que a repetição não gera alertas duplicados.

Vale para os dois protótipos (original e corrigido). O teste de D07 está em
`test_etapa6_d07_corrigido.py`, porque o original não recusa a autoaprovação.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import fakeredis.aioredis
import httpx
import jwt
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.core.config import Settings
from src.domain.entities.user import User, UserScope
from src.domain.value_objects.user_role import UserRole
from src.infrastructure.persistence.redis import keys
from src.infrastructure.persistence.redis.codec import dumps
from src.infrastructure.persistence.redis.seed import CLIENT_ALFA, CLIENT_GAMA
from src.presentation.api.main import create_app
from tests.conftest import GAMA_FIXED_RULE, OTP, PASSWORD, create_payload

ALFA_RULES = f"/v1/registry/clients/{CLIENT_ALFA}/service-rules"


async def _alertas(redis: Any, nome: str | None = None) -> list[dict[str, Any]]:
    todos = [json.loads(r) for r in await redis.lrange("psp:alerts", 0, -1)]
    return [a for a in todos if nome is None or a["alert"] == nome]


async def _criar(client: Any, headers: dict[str, str], **kw: Any) -> str:
    resp = await client.post("/v1/billing/items", json=create_payload(**kw), headers=headers)
    assert resp.status_code == 201, resp.text
    return str(resp.json()["data"]["uuid"])


async def _login_errado(client: Any, username: str) -> httpx.Response:
    return await client.post(
        "/v1/auth/login", json={"username": username, "password": "senha-errada"}
    )


# ── Campos de correlação (objetivos e eventos) ───────────────────────


async def test_evento_traz_request_id_sessao_perfil_origem_e_rota(client, login, audit):
    admin = await login("admin", mfa=True)
    analyst = await login("analyst")
    item = await _criar(client, admin, client_uuid=CLIENT_GAMA, rule=GAMA_FIXED_RULE)

    resp = await client.get(f"/v1/billing/items/{item}", headers=analyst)

    assert resp.status_code == 404
    evento = next(e for e in await audit.list_recent(10) if e.type == "acesso_negado")
    # O mesmo request_id devolvido ao cliente liga o evento ao log da aplicação.
    assert evento.request_id == resp.headers["X-Request-ID"]
    assert evento.role == "analyst"
    assert evento.sid is not None
    assert evento.origin == "127.0.0.1"
    assert (evento.method, evento.route) == ("GET", f"/v1/billing/items/{item}")
    assert evento.result == "negado"


async def test_login_recusado_nao_herda_sessao_de_ninguem(client, audit):
    await _login_errado(client, "manager")

    evento = next(e for e in await audit.list_recent(5) if e.type == "login_falha")
    assert evento.user == "manager"
    assert (evento.sid, evento.role) == (None, None)
    assert evento.request_id is not None


async def test_consulta_da_auditoria_nao_carimba_eventos_antigos(client, login, redis):
    # Evento gravado antes da etapa 6, sem os campos de correlação.
    antigo = {"type": "logout", "user": "admin", "created_at": "2026-01-01T00:00:00+00:00"}
    await redis.lpush(keys.AUDIT, json.dumps(antigo))
    admin = await login("admin", mfa=True)

    # A consulta é feita pelo próprio admin, dentro de uma requisição com request_id e sessão.
    resp = await client.get("/v1/audit/events?limit=50", headers=admin)

    assert resp.status_code == 200
    lido = next(e for e in resp.json()["data"] if e["created_at"].startswith("2026-01-01"))
    assert (lido["request_id"], lido["origin"], lido["sid"], lido["role"]) == (None,) * 4


# ── D01 e D02 ────────────────────────────────────────────────────────


async def test_d01_dispara_uma_vez_por_janela(client, login, redis):
    analyst = await login("analyst")
    item = await _criar(client, analyst)
    await client.patch(
        f"/v1/billing/items/{item}/status",
        json={"new_status": "ManagementApproval"},
        headers=analyst,
    )
    gestor_sem_mfa = await login("manager")

    for _ in range(7):
        await client.patch(
            f"/v1/billing/items/{item}/status",
            json={"new_status": "FinancialReview"},
            headers=gestor_sem_mfa,
        )

    alertas = await _alertas(redis, "mfa_falhas_repetidas")
    assert len(alertas) == 1
    assert (alertas[0]["regra"], alertas[0]["severidade"]) == ("D01", "Alta")


async def test_d02_conta_negacoes_de_item_e_de_periodo(client, login, app, redis):
    restrita = User(
        "analyst.set",
        UserRole.ANALYST,
        "Analista Set",
        "set@example.com",
        UserScope(clients=frozenset({str(CLIENT_ALFA)}), periods=frozenset({"2026-09"})),
    )
    await app.state.container.redis.set(keys.user(restrita.username), dumps(restrita))
    admin = await login("admin", mfa=True)
    gama = await _criar(client, admin, client_uuid=CLIENT_GAMA, rule=GAMA_FIXED_RULE)
    headers = await login("analyst.set")

    for _ in range(5):
        assert (await client.get(f"/v1/billing/items/{gama}", headers=headers)).status_code == 404
    for _ in range(5):
        # Listagem de período fora do escopo: antes da etapa 6 não entrava no contador.
        await client.get("/v1/billing?year=2026&month=10", headers=headers)

    alertas = await _alertas(redis, "acesso_negado_repetido")
    assert len(alertas) == 1
    assert (alertas[0]["regra"], alertas[0]["user"]) == ("D02", "analyst.set")


# ── D03 e D04 ────────────────────────────────────────────────────────


async def test_d03_falhas_repetidas_na_mesma_conta(client, redis):
    for _ in range(11):
        await _login_errado(client, "analyst")

    alertas = await _alertas(redis, "login_falhas_repetidas")
    assert len(alertas) == 1
    assert (alertas[0]["regra"], alertas[0]["severidade"]) == ("D03", "Média")


async def test_d03_mesma_origem_contra_varias_contas_sem_expor_quais_existem(client, redis):
    for nome in ("analyst", "manager", "admin", "nao.existe.1", "nao.existe.2"):
        await _login_errado(client, nome)

    alertas = await _alertas(redis, "login_falhas_por_origem")
    assert len(alertas) == 1
    assert alertas[0]["severidade"] == "Alta"
    assert alertas[0]["usuarios_distintos"] == 5
    assert "user" not in alertas[0]


async def test_d04_login_privilegiado_depois_de_falhas(client, redis):
    await _login_errado(client, "manager")

    resp = await client.post(
        "/v1/auth/login", json={"username": "manager", "password": PASSWORD, "otp": OTP}
    )

    assert resp.status_code == 200
    alertas = await _alertas(redis, "login_privilegiado_suspeito")
    assert len(alertas) == 1
    assert (alertas[0]["severidade"], alertas[0]["motivo"]) == ("Crítica", "apos_falhas_de_senha")
    assert alertas[0]["sid"]


async def test_d04_origem_nova_so_depois_da_linha_de_base(app, client, redis):
    corpo = {"username": "admin", "password": PASSWORD, "otp": OTP}
    # Primeiro login: só registra a origem conhecida, sem alerta.
    assert (await client.post("/v1/auth/login", json=corpo)).status_code == 200
    assert await _alertas(redis, "login_privilegiado_suspeito") == []

    outra_origem = httpx.ASGITransport(app=app, client=("10.9.9.9", 50000))
    async with httpx.AsyncClient(transport=outra_origem, base_url="http://test") as outro:
        assert (await outro.post("/v1/auth/login", json=corpo)).status_code == 200

    alertas = await _alertas(redis, "login_privilegiado_suspeito")
    assert [(a["motivo"], a["origin"]) for a in alertas] == [("origem_nova", "10.9.9.9")]


async def test_d04_ignora_perfil_nao_privilegiado(app, client, redis):
    await _login_errado(client, "analyst")
    resp = await client.post("/v1/auth/login", json={"username": "analyst", "password": PASSWORD})

    assert resp.status_code == 200
    assert await _alertas(redis, "login_privilegiado_suspeito") == []


# ── D05 (correção do V01) ────────────────────────────────────────────


async def test_d05_reuso_do_refresh_revoga_a_sessao_e_alerta(client, redis, audit):
    login = await client.post("/v1/auth/login", json={"username": "analyst", "password": PASSWORD})
    antigo = login.json()["refresh_token"]
    client.cookies.clear()

    renovado = await client.post("/v1/auth/refresh", headers={"Cookie": f"refresh_token={antigo}"})
    assert renovado.status_code == 200
    novo = renovado.cookies["refresh_token"]
    client.cookies.clear()

    reuso = await client.post("/v1/auth/refresh", headers={"Cookie": f"refresh_token={antigo}"})
    depois = await client.post("/v1/auth/refresh", headers={"Cookie": f"refresh_token={novo}"})

    # O caso do V01: antes da correção, o reuso respondia 200.
    assert (reuso.status_code, reuso.json()["motivo"]) == (401, "refresh_reutilizado")
    # A sessão foi revogada: nem o refresh mais recente renova.
    assert (depois.status_code, depois.json()["motivo"]) == (401, "sessao_invalida")
    evento = next(e for e in await audit.list_recent(10) if e.type == "refresh_reutilizado")
    assert evento.user == "analyst"
    assert evento.sid
    alertas = await _alertas(redis, "refresh_token_reutilizado")
    assert [(a["regra"], a["user"]) for a in alertas] == [("D05", "analyst")]


async def test_renovacao_legitima_continua_funcionando(client):
    login = await client.post("/v1/auth/login", json={"username": "analyst", "password": PASSWORD})
    atual = login.json()["refresh_token"]
    client.cookies.clear()

    for _ in range(3):
        resp = await client.post("/v1/auth/refresh", headers={"Cookie": f"refresh_token={atual}"})
        assert resp.status_code == 200
        atual = resp.cookies["refresh_token"]
        client.cookies.clear()


# ── D06 ──────────────────────────────────────────────────────────────


def _claims(**extra: Any) -> dict[str, Any]:
    settings = Settings()  # type: ignore[call-arg]
    agora = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": "analyst",
        "sid": uuid4().hex,
        "amr": ["pwd", "mfa"],
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int(agora.timestamp()),
        "exp": int((agora + timedelta(minutes=5)).timestamp()),
        "type": "access",
    }
    claims.update(extra)
    return claims


async def test_d06_tokens_forjados_geram_evento_e_alerta_medio(client, redis, audit):
    forjados = [
        jwt.encode(_claims(), key="", algorithm="none"),
        jwt.encode(_claims(), "outra-chave-qualquer-com-tamanho-suficiente", algorithm="HS256"),
        jwt.encode(_claims(sub="admin", role="admin"), "chave-do-atacante-0123456789abcdef"),
    ]

    for token in forjados:
        resp = await client.get(
            "/v1/billing?year=2026&month=9", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    recusas = [e for e in await audit.list_recent(10) if e.type == "token_recusado"]
    assert [e.detail for e in recusas] == ["token_invalido"] * 3
    alertas = await _alertas(redis, "tokens_invalidos_repetidos")
    assert [(a["regra"], a["severidade"]) for a in alertas] == [("D06", "Média")]


async def test_d06_token_valido_de_sessao_encerrada_e_critico(client, login, redis):
    headers = await login("analyst")
    assert (await client.post("/v1/auth/logout", headers=headers)).status_code == 200

    resp = await client.get("/v1/billing?year=2026&month=9", headers=headers)

    assert (resp.status_code, resp.json()["motivo"]) == (401, "sessao_invalida")
    alertas = await _alertas(redis, "token_valido_sessao_desconhecida")
    assert [(a["regra"], a["severidade"]) for a in alertas] == [("D06", "Crítica")]


async def test_d06_token_expirado_e_registrado_sem_alerta(client, redis, audit):
    settings = Settings()  # type: ignore[call-arg]
    vencido = jwt.encode(
        _claims(exp=int((datetime.now(UTC) - timedelta(minutes=1)).timestamp())),
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    resp = await client.get(
        "/v1/billing?year=2026&month=9", headers={"Authorization": f"Bearer {vencido}"}
    )

    assert resp.json()["motivo"] == "token_expirado"
    assert any(e.detail == "token_expirado" for e in await audit.list_recent(5))
    assert await _alertas(redis) == []


# ── D08 ──────────────────────────────────────────────────────────────


async def test_d08_alteracoes_repetidas_de_regra(client, login, redis):
    admin = await login("admin", mfa=True)
    criada = await client.post(
        ALFA_RULES,
        json={"name": "Serviço D08", "rule_type": "fixed_value", "status": "Ativo"},
        headers=admin,
    )
    regra = criada.json()["data"]
    url = f"{ALFA_RULES}/{regra['uuid']}"
    versao = regra["version"]

    for i in range(6):
        resp = await client.patch(
            url, json={"version": versao, "name": f"Serviço D08 v{i}"}, headers=admin
        )
        assert resp.status_code == 200, resp.text
        versao = resp.json()["data"]["version"]

    alertas = await _alertas(redis, "alteracoes_de_regra_repetidas")
    assert len(alertas) == 1
    assert (alertas[0]["regra"], alertas[0]["destino"]) == ("D08", "Negócio, Segurança")


# ── D12 ──────────────────────────────────────────────────────────────


def test_d12_websocket_de_outra_origem(redis_sync_app: TestClient) -> None:
    web = redis_sync_app
    for _ in range(3):
        with (
            pytest.raises(WebSocketDisconnect),
            web.websocket_connect("/ws", headers={"origin": "https://site-malicioso.example"}),
        ):
            pass

    redis = web.app.state.container.redis  # type: ignore[attr-defined]
    alertas = web.portal.call(_alertas, redis, "websocket_origem_recusada_repetida")  # type: ignore[union-attr]
    assert len(alertas) == 1
    assert alertas[0]["pagina"] == "https://site-malicioso.example"


@pytest.fixture
def redis_sync_app() -> Any:
    app = create_app(Settings(RATE_LIMIT_ENABLED=False), fakeredis.aioredis.FakeRedis())  # type: ignore[call-arg]
    with TestClient(app) as client:
        yield client


# ── D13 ──────────────────────────────────────────────────────────────


@pytest.fixture
async def app_com_limite(redis: Any) -> Any:
    application: FastAPI = create_app(Settings(RATE_LIMIT_ENABLED=True), redis)  # type: ignore[call-arg]
    async with application.router.lifespan_context(application):
        yield application


async def test_d13_varredura_alcanca_o_limite(app_com_limite, redis):
    transport = httpx.ASGITransport(app=app_com_limite)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        respostas = [(await _login_errado(c, "scan")).status_code for _ in range(110)]
        # A rota de login aceita 10 por minuto; da 11ª em diante, 429. São 100 respostas 429.
        assert respostas[:10] == [401] * 10
        assert set(respostas[10:]) == {429}
        # A regra pede "mais de 100": com exatamente 100 ainda não há alerta.
        assert await _alertas(redis, "varredura_limite_excedido") == []

        for _ in range(5):
            await _login_errado(c, "scan")

    alertas = await _alertas(redis, "varredura_limite_excedido")
    assert len(alertas) == 1
    assert (alertas[0]["regra"], alertas[0]["total"]) == ("D13", 101)


async def test_falha_nas_regras_nao_derruba_a_operacao(client, app, audit, monkeypatch):
    async def quebra(*_: Any, **__: Any) -> None:
        raise RuntimeError("detecção indisponível")

    monkeypatch.setattr(app.state.container.detection, "_dispatch", quebra)

    # O login grava `login_sucesso`, que passa pelas regras. A falha delas fica no log.
    resp = await client.post("/v1/auth/login", json={"username": "analyst", "password": PASSWORD})

    assert resp.status_code == 200
    assert any(e.type == "login_sucesso" for e in await audit.list_recent(5))


async def test_alertas_nao_carregam_senha_nem_otp(client, redis):
    for _ in range(10):
        await client.post(
            "/v1/auth/login", json={"username": "manager", "password": PASSWORD, "otp": "000000"}
        )

    texto = json.dumps(await _alertas(redis))
    assert "mfa_falhas_repetidas" in texto
    assert PASSWORD not in texto
    assert "000000" not in texto and OTP not in texto
