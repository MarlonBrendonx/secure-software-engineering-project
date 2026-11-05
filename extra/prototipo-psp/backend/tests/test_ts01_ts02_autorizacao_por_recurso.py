"""Prática 1 — autorização por recurso (RS03 / risco R03). Testes TS01 e TS02."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from src.infrastructure.persistence.redis.seed import CLIENT_GAMA
from tests.conftest import GAMA_FIXED_RULE, create_payload


async def _create(client: Any, headers: dict[str, str], **kw: Any) -> str:
    resp = await client.post("/v1/billing/items", json=create_payload(**kw), headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["uuid"]


async def test_ts01_analista_le_lancamento_do_proprio_escopo(client, login):
    analyst = await login("analyst")
    l1 = await _create(client, analyst)

    resp = await client.get(f"/v1/billing/items/{l1}", headers=analyst)

    assert resp.status_code == 200
    assert resp.json()["data"]["uuid"] == l1


async def test_ts02_analista_nao_le_lancamento_de_outro_cliente(client, login, audit):
    admin = await login("admin", mfa=True)
    analyst = await login("analyst")
    # O admin lança na Gama, cliente fora do escopo da analista.
    l2 = await _create(client, admin, client_uuid=CLIENT_GAMA, rule=GAMA_FIXED_RULE)

    fora_do_escopo = await client.get(f"/v1/billing/items/{l2}", headers=analyst)
    inexistente = await client.get(f"/v1/billing/items/{uuid4()}", headers=analyst)

    assert fora_do_escopo.status_code == 404
    # Mesma resposta de um id inexistente (ignora só o request_id e o horário de cada chamada).
    assert fora_do_escopo.json()["error"] == inexistente.json()["error"]
    assert "Gama" not in fora_do_escopo.text
    evento = next(e for e in await audit.list_recent(10) if e.type == "acesso_negado")
    assert (evento.user, evento.resource, evento.resource_id) == ("analyst", "lancamento", l2)


async def test_analista_nao_altera_nem_exclui_nem_muda_status_de_outro_cliente(client, login):
    admin = await login("admin", mfa=True)
    analyst = await login("analyst")
    l2 = await _create(client, admin, client_uuid=CLIENT_GAMA, rule=GAMA_FIXED_RULE)

    patch = await client.patch(
        f"/v1/billing/items/{l2}", json={"version": 1, "total_value": "1.00"}, headers=analyst
    )
    delete = await client.delete(f"/v1/billing/items/{l2}", headers=analyst)
    status = await client.patch(
        f"/v1/billing/items/{l2}/status", json={"new_status": "ManagementApproval"}, headers=analyst
    )
    historico = await client.get(f"/v1/billing/items/{l2}/history", headers=analyst)
    lote = await client.post(
        "/v1/billing/items/batch-status",
        json={"item_uuids": [l2], "new_status": "ManagementApproval"},
        headers=analyst,
    )

    assert [r.status_code for r in (patch, delete, status, historico, lote)] == [404] * 5
    intacto = await client.get(f"/v1/billing/items/{l2}", headers=admin)
    assert intacto.json()["data"]["version"] == 1


async def test_analista_nao_cria_lancamento_em_cliente_fora_do_escopo(client, login):
    analyst = await login("analyst")

    resp = await client.post(
        "/v1/billing/items",
        json=create_payload(client_uuid=CLIENT_GAMA, rule=GAMA_FIXED_RULE),
        headers=analyst,
    )

    assert resp.status_code == 404


async def test_listagem_so_traz_clientes_do_escopo(client, login):
    analyst = await login("analyst")
    admin = await login("admin", mfa=True)

    da_analista = await client.get("/v1/billing?year=2026&month=9", headers=analyst)
    do_admin = await client.get("/v1/billing?year=2026&month=9", headers=admin)

    nomes = {c["client_name"] for c in da_analista.json()["data"]}
    assert nomes == {"Rede Alfa Saúde", "Farmácias Beta"}
    assert len(do_admin.json()["data"]) == 3


async def test_rotas_por_cliente_e_faturamento_negam_com_404_identico_ao_inexistente(client, login):
    admin = await login("admin", mfa=True)
    analyst = await login("analyst")
    gama = await _create(client, admin, client_uuid=CLIENT_GAMA, rule=GAMA_FIXED_RULE)
    billing_gama = (await client.get(f"/v1/billing/items/{gama}", headers=admin)).json()["data"][
        "billing_uuid"
    ]
    periodo = "year=2026&month=9"

    casos = [
        (
            f"/v1/billing/clients/{CLIENT_GAMA}/services?{periodo}",
            f"/v1/billing/clients/{uuid4()}/services?{periodo}",
        ),
        (
            f"/v1/billing/clients/{CLIENT_GAMA}/average?{periodo}",
            f"/v1/billing/clients/{uuid4()}/average?{periodo}",
        ),
        (f"/v1/billing/{billing_gama}/history", f"/v1/billing/{uuid4()}/history"),
    ]
    for fora, inexistente in casos:
        a = await client.get(fora, headers=analyst)
        b = await client.get(inexistente, headers=analyst)
        assert (a.status_code, b.status_code) == (404, 404), fora
        assert a.json()["error"] == b.json()["error"], fora


async def test_escopo_por_periodo(client, login, app):
    """Usuário limitado a 2026-09 não alcança lançamento de 2026-10 do mesmo cliente."""
    from src.domain.entities.user import User, UserScope
    from src.domain.value_objects.user_role import UserRole
    from src.infrastructure.persistence.redis import keys
    from src.infrastructure.persistence.redis.codec import dumps
    from src.infrastructure.persistence.redis.seed import CLIENT_ALFA

    restrita = User(
        "analyst.set",
        UserRole.ANALYST,
        "Analista Set",
        "set@example.com",
        UserScope(clients=frozenset({str(CLIENT_ALFA)}), periods=frozenset({"2026-09"})),
    )
    await app.state.container.redis.set(keys.user(restrita.username), dumps(restrita))
    admin = await login("admin", mfa=True)
    setembro = await _create(client, admin, reference_month=9, billing_month=9)
    outubro = await _create(client, admin, reference_month=10, billing_month=10)

    import os

    resp = await client.post(
        "/v1/auth/login",
        json={"username": "analyst.set", "password": os.environ["MOCK_LOGIN_PASSWORD"]},
    )
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    client.cookies.clear()

    assert (await client.get(f"/v1/billing/items/{setembro}", headers=headers)).status_code == 200
    assert (await client.get(f"/v1/billing/items/{outubro}", headers=headers)).status_code == 404
    lista = await client.get("/v1/billing?year=2026&month=10", headers=headers)
    assert lista.json()["data"] == []
    criar = await client.post(
        "/v1/billing/items",
        json=create_payload(reference_month=10, billing_month=10),
        headers=headers,
    )
    assert criar.status_code == 404
