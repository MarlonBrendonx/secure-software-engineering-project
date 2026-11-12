"""RS03 (cobertura de autorização por rota) e RS06 (negar por padrão)."""

from __future__ import annotations

from fastapi.routing import APIRoute

from src.presentation.api.deps import POLICY_ATTR, assert_all_routes_have_policy
from src.presentation.api.routes import audit, auth, billing
from tests.conftest import create_payload

# Rotas com identificador na URL cobertas por teste de autorização (TS02 e correlatos).
ROTAS_COM_TESTE_DE_AUTORIZACAO = {
    "/clients/{client_uuid}/services",
    "/clients/{client_uuid}/average",
    "/items/{item_uuid}",
    "/items/{item_uuid}/status",
    "/items/{item_uuid}/history",
    "/{billing_uuid}/history",
}


def test_toda_rota_com_identificador_tem_teste_de_autorizacao():
    rotas_com_id = {
        r.path for r in billing.router.routes if isinstance(r, APIRoute) and "{" in r.path
    }
    assert rotas_com_id - ROTAS_COM_TESTE_DE_AUTORIZACAO == set()


def test_toda_rota_declara_politica_de_acesso():
    routers = [("/v1", auth.router), ("/v1/billing", billing.router), ("/v1", audit.router)]
    assert_all_routes_have_policy(routers)  # não levanta


def test_rota_sem_politica_impede_a_inicializacao():
    from fastapi import APIRouter

    solto = APIRouter()
    solto.add_api_route("/sem-politica", lambda: None, methods=["GET"])

    try:
        assert_all_routes_have_policy([("/v1", solto)])
    except RuntimeError as exc:
        assert "/sem-politica" in str(exc)
    else:
        raise AssertionError("deveria recusar rota sem política")


def test_marcador_de_politica_existe_nas_dependencias():
    assert POLICY_ATTR == "policy"


async def test_sem_token_e_negado(client):
    resp = await client.get("/v1/billing?year=2026&month=9")
    assert resp.status_code == 401


async def test_falha_do_redis_na_verificacao_nega_e_nao_grava(client, login, app, monkeypatch):
    analyst = await login("analyst")

    async def quebrado(*_a, **_k):
        raise ConnectionError("redis indisponível")

    monkeypatch.setattr(app.state.container.sessions, "get", quebrado)
    resp = await client.post("/v1/billing/items", json=create_payload(), headers=analyst)

    assert resp.status_code == 503
    monkeypatch.undo()
    lista = await client.get("/v1/billing?year=2026&month=9", headers=analyst)
    assert lista.json()["status_summary"][1]["count"] == 0  # status "New": nada foi gravado


async def test_login_com_senha_errada_nao_revela_se_o_usuario_existe(client):
    existente = await client.post(
        "/v1/auth/login", json={"username": "analyst", "password": "errada"}
    )
    inexistente = await client.post(
        "/v1/auth/login", json={"username": "ninguem", "password": "errada"}
    )

    assert existente.status_code == inexistente.status_code == 401
    assert existente.json()["error"] == inexistente.json()["error"]


async def test_limite_de_login_por_ip(redis):
    import httpx

    from src.core.config import Settings
    from src.presentation.api.main import create_app

    app = create_app(Settings(RATE_LIMIT_ENABLED=True), redis)  # type: ignore[call-arg]
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            codigos = [
                (
                    await c.post("/v1/auth/login", json={"username": "x", "password": "y"})
                ).status_code
                for _ in range(12)
            ]
    assert codigos[:10] == [401] * 10
    assert codigos[10:] == [429, 429]
