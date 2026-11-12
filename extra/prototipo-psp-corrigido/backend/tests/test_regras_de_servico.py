"""Cadastro de regras de serviço: autorização por perfil e cliente, regras de negócio, auditoria."""

from __future__ import annotations

from typing import Any

from src.infrastructure.persistence.redis.seed import CLIENT_ALFA, CLIENT_BETA, CLIENT_GAMA, demo_id
from tests.conftest import ALFA_FIXED_RULE, create_payload

ALFA_RULES = f"/v1/registry/clients/{CLIENT_ALFA}/service-rules"
GAMA_RULES = f"/v1/registry/clients/{CLIENT_GAMA}/service-rules"
PROGRAMA_VIDA = demo_id("program/Programa Vida+")
PROGRAMA_GAMA = demo_id("program/Programa Gama Care")


def rule_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"name": "Serviço Novo", "rule_type": "fixed_value", "status": "Ativo"}
    body.update(overrides)
    return body


async def _create_rule(client: Any, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    resp = await client.post(ALFA_RULES, json=rule_body(**overrides), headers=headers)
    assert resp.status_code == 201, resp.text
    data: dict[str, Any] = resp.json()["data"]
    return data


# ── Quem pode escrever e ler ─────────────────────────────────────────


async def test_admin_cria_regra_e_ela_aparece_como_sem_lancamento(client, login):
    admin = await login("admin", mfa=True)

    rule = await _create_rule(client, admin, name="Serviço Piloto")

    assert rule["code"] > 1000  # acima dos códigos fictícios do seed
    assert rule["status"] == "Ativo"
    listing = await client.get("/v1/billing?year=2026&month=9&per_page=20", headers=admin)
    services = [s for c in listing.json()["data"] for s in c["services"]]
    created = next(s for s in services if s["service_rule_uuid"] == rule["uuid"])
    assert created["status"] == "NoEntry"


async def test_analista_e_gestor_nao_escrevem_regras(client, login):
    for username, mfa in (("analyst", False), ("manager", True)):
        headers = await login(username, mfa=mfa)

        created = await client.post(ALFA_RULES, json=rule_body(), headers=headers)

        assert created.status_code == 403, username


async def test_admin_sem_mfa_nao_escreve_regras(client, login):
    admin_sem_otp = await login("admin")

    resp = await client.post(ALFA_RULES, json=rule_body(), headers=admin_sem_otp)

    assert resp.status_code == 401
    assert resp.json()["motivo"] == "mfa_necessario"


async def test_sem_login_nao_le_nem_escreve(client):
    assert (await client.get(ALFA_RULES)).status_code == 401
    assert (await client.post(ALFA_RULES, json=rule_body())).status_code == 401


async def test_analista_le_regras_do_seu_cliente(client, login):
    analyst = await login("analyst")

    resp = await client.get(ALFA_RULES, headers=analyst)

    assert resp.status_code == 200
    names = {r["name"] for r in resp.json()["data"]}
    assert "Taxa de Administração" in names


async def test_analista_nao_le_regras_de_cliente_fora_do_escopo(client, login, audit):
    analyst = await login("analyst")

    resp = await client.get(GAMA_RULES, headers=analyst)
    inexistente = await client.get(
        f"/v1/registry/clients/{demo_id('nao-existe')}/service-rules", headers=analyst
    )

    # Mesma resposta de um cliente que não existe: não revela o que há fora do escopo.
    assert resp.status_code == inexistente.status_code == 404
    assert resp.json()["error"] == inexistente.json()["error"]
    evento = next(e for e in await audit.list_recent(10) if e.type == "acesso_negado")
    assert evento.user == "analyst"
    assert evento.detail == "listar_regras_servico"


async def test_analista_nao_lista_programas_nem_clientes_de_fora_do_escopo(client, login):
    analyst = await login("analyst")

    programas = await client.get(f"/v1/registry/clients/{CLIENT_GAMA}/programs", headers=analyst)
    clientes = await client.get("/v1/registry/clients/summary", headers=analyst)

    assert programas.status_code == 404
    assert {c["uuid"] for c in clientes.json()["data"]} == {str(CLIENT_ALFA), str(CLIENT_BETA)}


async def test_busca_de_clientes_filtra_por_nome(client, login):
    admin = await login("admin", mfa=True)

    resp = await client.get("/v1/registry/clients?search=gama", headers=admin)

    assert [c["name"] for c in resp.json()["data"]] == ["Drogaria Gama"]


async def test_nao_aceita_campo_desconhecido(client, login):
    admin = await login("admin", mfa=True)

    resp = await client.post(ALFA_RULES, json=rule_body(management_percentage=100), headers=admin)

    assert resp.status_code == 422


# ── Regras de negócio ────────────────────────────────────────────────


async def test_faixas_sobrepostas_sao_recusadas(client, login):
    admin = await login("admin", mfa=True)
    ranges = [
        {"range_from": 0, "range_to": 100, "range_type": "fixed_value", "value": "500"},
        {
            "range_from": 50,
            "range_to": None,
            "last_range": True,
            "range_type": "per_unit_value",
            "value": "3",
        },
    ]

    resp = await client.post(
        ALFA_RULES, json=rule_body(rule_type="range", ranges=ranges), headers=admin
    )

    assert resp.status_code == 422
    assert "sobrepostas" in str(resp.json())


async def test_regra_de_faixa_valida_e_gravada_em_ordem(client, login):
    admin = await login("admin", mfa=True)
    ranges = [
        {
            "range_from": 101,
            "range_to": None,
            "last_range": True,
            "range_type": "per_unit_value",
            "value": "3",
        },
        {"range_from": 0, "range_to": 100, "range_type": "fixed_value", "value": "500"},
    ]

    rule = await _create_rule(client, admin, rule_type="range", ranges=ranges)

    assert [r["range_from"] for r in rule["ranges"]] == [0, 101]


async def test_tipo_exige_os_seus_campos(client, login):
    admin = await login("admin", mfa=True)

    sem_percentual = await client.post(
        ALFA_RULES, json=rule_body(rule_type="percentage"), headers=admin
    )
    sem_base = await client.post(
        ALFA_RULES, json=rule_body(rule_type="multiplication"), headers=admin
    )

    assert sem_percentual.status_code == 422
    assert sem_base.status_code == 422


async def test_nome_e_programas_repetidos_no_cliente_dao_409(client, login):
    admin = await login("admin", mfa=True)
    programs = [{"program_uuid": str(PROGRAMA_VIDA)}]
    await _create_rule(client, admin, name="Duplicada", programs=programs)

    repetida = await client.post(
        ALFA_RULES, json=rule_body(name="  duplicada ", programs=programs), headers=admin
    )
    outro_conjunto = await client.post(
        ALFA_RULES, json=rule_body(name="Duplicada", programs=[]), headers=admin
    )

    assert repetida.status_code == 409
    assert outro_conjunto.status_code == 201


async def test_programa_de_outro_cliente_e_recusado(client, login):
    admin = await login("admin", mfa=True)

    resp = await client.post(
        ALFA_RULES,
        json=rule_body(programs=[{"program_uuid": str(PROGRAMA_GAMA)}]),
        headers=admin,
    )

    assert resp.status_code == 422


async def test_versao_desatualizada_da_409(client, login):
    admin = await login("admin", mfa=True)
    rule = await _create_rule(client, admin)
    url = f"{ALFA_RULES}/{rule['uuid']}"

    primeira = await client.patch(
        url, json={"version": rule["version"], "name": "A"}, headers=admin
    )
    defasada = await client.patch(
        url, json={"version": rule["version"], "name": "B"}, headers=admin
    )

    assert primeira.status_code == 200
    assert primeira.json()["data"]["version"] == rule["version"] + 1
    assert defasada.status_code == 409


async def test_trocar_o_tipo_limpa_o_que_nao_pertence_ao_novo_tipo(client, login):
    admin = await login("admin", mfa=True)
    rule = await _create_rule(client, admin, rule_type="percentage", percentage="5")
    url = f"{ALFA_RULES}/{rule['uuid']}"

    resp = await client.patch(
        url, json={"version": rule["version"], "rule_type": "fixed_value"}, headers=admin
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["percentage"] is None


async def test_regra_sem_lancamento_pode_ser_editada_e_excluida(client, login):
    admin = await login("admin", mfa=True)
    rule = await _create_rule(client, admin)
    url = f"{ALFA_RULES}/{rule['uuid']}"

    editada = await client.patch(
        url, json={"version": rule["version"], "name": "Renomeada"}, headers=admin
    )
    excluida = await client.delete(url, headers=admin)
    depois = await client.get(url, headers=admin)

    assert editada.json()["data"]["name"] == "Renomeada"
    assert excluida.status_code == 204
    assert depois.status_code == 404


# ── Regra que já tem lançamento ──────────────────────────────────────


async def _rule_com_lancamento(client: Any, admin: dict[str, str]) -> dict[str, Any]:
    rule = await _create_rule(client, admin, name="Com Lançamento")
    created = await client.post(
        "/v1/billing/items", json=create_payload(rule=rule["uuid"]), headers=admin
    )
    assert created.status_code == 201, created.text
    return rule


async def test_regra_com_lancamento_nao_pode_ser_excluida(client, login):
    admin = await login("admin", mfa=True)
    rule = await _rule_com_lancamento(client, admin)

    resp = await client.delete(f"{ALFA_RULES}/{rule['uuid']}", headers=admin)
    leitura = await client.get(f"{ALFA_RULES}/{rule['uuid']}", headers=admin)

    assert resp.status_code == 422
    assert leitura.json()["data"]["has_billing_items"] is True


async def test_regra_com_lancamento_so_muda_o_status(client, login):
    admin = await login("admin", mfa=True)
    rule = await _rule_com_lancamento(client, admin)
    url = f"{ALFA_RULES}/{rule['uuid']}"

    bloqueada = await client.patch(
        url, json={"version": rule["version"], "name": "Outro nome"}, headers=admin
    )
    inativa = await client.patch(
        url, json={"version": rule["version"], "status": "Inativo"}, headers=admin
    )

    assert bloqueada.status_code == 422
    assert "name" in str(bloqueada.json())
    assert inativa.status_code == 200
    assert inativa.json()["data"]["status"] == "Inativo"


async def test_regra_de_faixa_com_lancamento_aceita_reenvio_das_mesmas_faixas(client, login):
    # O front reenvia as faixas a cada edição; sem mudança, só o status deve passar.
    admin = await login("admin", mfa=True)
    ranges = [
        {
            "range_from": 0,
            "range_to": None,
            "last_range": True,
            "range_type": "fixed_value",
            "value": "10",
        }
    ]
    rule = await _create_rule(client, admin, name="Faixa", rule_type="range", ranges=ranges)
    await client.post(
        "/v1/billing/items",
        json=create_payload(rule=rule["uuid"], quantity="1", total_value="0"),
        headers=admin,
    )

    resp = await client.patch(
        f"{ALFA_RULES}/{rule['uuid']}",
        json={"version": rule["version"], "status": "Inativo", "ranges": ranges},
        headers=admin,
    )

    assert resp.status_code == 200, resp.text


async def test_regra_do_seed_com_lancamento_e_protegida(client, login):
    admin = await login("admin", mfa=True)
    await client.post("/v1/billing/items", json=create_payload(), headers=admin)
    listing = await client.get(ALFA_RULES, headers=admin)
    seed_rule = next(r for r in listing.json()["data"] if r["uuid"] == str(ALFA_FIXED_RULE))

    resp = await client.delete(f"{ALFA_RULES}/{seed_rule['uuid']}", headers=admin)

    assert resp.status_code == 422


# ── Auditoria ────────────────────────────────────────────────────────


async def test_criar_editar_e_excluir_ficam_na_auditoria(client, login, audit):
    admin = await login("admin", mfa=True)
    rule = await _create_rule(client, admin)
    url = f"{ALFA_RULES}/{rule['uuid']}"
    await client.patch(url, json={"version": rule["version"], "name": "Novo nome"}, headers=admin)
    await client.delete(url, headers=admin)

    eventos = [e for e in await audit.list_recent(50) if e.resource_id == rule["uuid"]]

    assert {e.type for e in eventos} == {
        "regra_servico_criada",
        "regra_servico_atualizada",
        "regra_servico_excluida",
    }
    assert all(e.user == "admin" for e in eventos)
    editado = next(e for e in eventos if e.type == "regra_servico_atualizada")
    assert editado.detail == "campos=name"
