"""Fluxo PSP de lançamentos: cálculo, bloqueio otimista, máquina de estados e lote."""

from __future__ import annotations

from typing import Any

from tests.conftest import (
    ALFA_MULT_RULE,
    ALFA_PERCENT_RULE,
    ALFA_RANGE_RULE,
    create_payload,
)


async def _create(client: Any, headers: dict[str, str], **kw: Any) -> dict[str, Any]:
    resp = await client.post("/v1/billing/items", json=create_payload(**kw), headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_servidor_recalcula_o_valor_e_avisa(client, login):
    analyst = await login("analyst")

    # Multiplicação: 10 × 12,50 = 125,00, não os 999 que o cliente enviou.
    body = await _create(
        client, analyst, rule=ALFA_MULT_RULE, quantity="10", total_value="999", unit_value="1"
    )

    assert body["data"]["total_value"] == "125.00"
    assert {w["code"] for w in body["warnings"]} == {"VALUE_RECALCULATED"}


async def test_regras_percentual_e_faixa(client, login):
    analyst = await login("analyst")

    pct = await _create(client, analyst, rule=ALFA_PERCENT_RULE, total_value="0")
    faixa = await _create(client, analyst, rule=ALFA_RANGE_RULE, quantity="200", total_value="0")

    assert pct["data"]["total_value"] == "350.0"  # 10000 × 3,5%
    assert faixa["data"]["total_value"] == "840.00"  # faixa 101–500: 200 × 4,20


async def test_valor_zero_e_recusado_e_descricao_padrao_e_montada(client, login):
    analyst = await login("analyst")

    zero = await client.post(
        "/v1/billing/items", json=create_payload(total_value="0"), headers=analyst
    )
    ok = await _create(client, analyst, po_number="PO-1")

    assert zero.status_code == 422
    assert ok["data"]["invoice_description"].startswith("PO: PO-1 - Taxa de Administração - ")


async def test_bloqueio_otimista_devolve_409_e_registra_diff(client, login):
    analyst = await login("analyst")
    item = (await _create(client, analyst))["data"]

    primeiro = await client.patch(
        f"/v1/billing/items/{item['uuid']}",
        json={"version": item["version"], "total_value": "2000.00"},
        headers=analyst,
    )
    obsoleto = await client.patch(
        f"/v1/billing/items/{item['uuid']}",
        json={"version": item["version"], "total_value": "3000.00"},
        headers=analyst,
    )

    assert primeiro.status_code == 200
    assert primeiro.json()["data"]["version"] == item["version"] + 1
    assert obsoleto.status_code == 409
    hist = await client.get(f"/v1/billing/items/{item['uuid']}/history", headers=analyst)
    acoes = [h["action"] for h in hist.json()["data"]]
    assert acoes == ["lancamento_criado", "lancamento_atualizado"]


async def test_fluxo_completo_de_aprovacao_com_segregacao_de_perfis(client, login):
    analyst = await login("analyst")
    manager = await login("manager", mfa=True)
    item = (await _create(client, analyst))["data"]["uuid"]
    url = f"/v1/billing/items/{item}/status"

    # Analista não aprova; gestor não envia para a gestão.
    assert (
        await client.patch(url, json={"new_status": "FinancialReview"}, headers=analyst)
    ).status_code == 403
    assert (
        await client.patch(url, json={"new_status": "ManagementApproval"}, headers=manager)
    ).status_code == 403
    assert (
        await client.patch(url, json={"new_status": "ManagementApproval"}, headers=analyst)
    ).status_code == 200
    # Transição inválida (pula FinancialReview).
    assert (
        await client.patch(url, json={"new_status": "Approved"}, headers=manager)
    ).status_code == 422
    assert (
        await client.patch(url, json={"new_status": "FinancialReview"}, headers=manager)
    ).status_code == 200
    assert (
        await client.patch(url, json={"new_status": "Approved"}, headers=manager)
    ).status_code == 200

    # Aprovado não pode mais ser alterado nem excluído.
    atual = (await client.get(f"/v1/billing/items/{item}", headers=manager)).json()["data"]
    alterar = await client.patch(
        f"/v1/billing/items/{item}",
        json={"version": atual["version"], "notes": "x"},
        headers=analyst,
    )
    excluir = await client.delete(f"/v1/billing/items/{item}", headers=analyst)
    assert (alterar.status_code, excluir.status_code) == (422, 422)


async def test_reprovacao_exige_motivo_e_so_guarda_enquanto_reprovado(client, login):
    analyst = await login("analyst")
    manager = await login("manager", mfa=True)
    item = (await _create(client, analyst))["data"]["uuid"]
    url = f"/v1/billing/items/{item}/status"
    await client.patch(url, json={"new_status": "ManagementApproval"}, headers=analyst)

    sem_motivo = await client.patch(url, json={"new_status": "Rejected"}, headers=manager)
    com_motivo = await client.patch(
        url,
        json={"new_status": "Rejected", "rejection_reason": "valor divergente"},
        headers=manager,
    )
    reenviado = await client.patch(url, json={"new_status": "ManagementApproval"}, headers=analyst)

    assert sem_motivo.status_code == 422
    assert com_motivo.json()["data"]["rejection_reason"] == "valor divergente"
    assert reenviado.json()["data"]["rejection_reason"] is None


async def test_aprovacao_do_cliente_exige_contrato_habilitado(client, login):
    analyst = await login("analyst")
    manager = await login("manager", mfa=True)
    # Beta não tem contrato com aprovação de cliente (RF-PSP-33).
    from src.infrastructure.persistence.redis.seed import CLIENT_BETA, demo_id

    beta_rule = demo_id(f"rule/{CLIENT_BETA}/201")
    item = (await _create(client, analyst, client_uuid=CLIENT_BETA, rule=beta_rule))["data"]["uuid"]
    url = f"/v1/billing/items/{item}/status"
    await client.patch(url, json={"new_status": "ManagementApproval"}, headers=analyst)

    resp = await client.patch(url, json={"new_status": "ClientApproval"}, headers=manager)

    assert resp.status_code == 422
    assert "Farmácias Beta" in resp.json()["error"]["message"]


async def test_lote_e_tudo_ou_nada(client, login):
    analyst = await login("analyst")
    manager = await login("manager", mfa=True)
    a = (await _create(client, analyst))["data"]["uuid"]
    b = (await _create(client, analyst, reference_month=10, billing_month=10))["data"]["uuid"]
    await client.patch(
        f"/v1/billing/items/{a}/status", json={"new_status": "ManagementApproval"}, headers=analyst
    )
    # `b` continua em New: a transição New → FinancialReview é inválida para ele.

    resp = await client.post(
        "/v1/billing/items/batch-status",
        json={"item_uuids": [a, b], "new_status": "FinancialReview"},
        headers=manager,
    )

    assert resp.status_code == 422
    assert len(resp.json()["errors"]) == 1
    atual = await client.get(f"/v1/billing/items/{a}", headers=manager)
    assert atual.json()["data"]["status"] == "ManagementApproval"  # nenhum item mudou


async def test_exclusao_do_ultimo_lancamento_remove_o_faturamento(client, login):
    analyst = await login("analyst")
    item = (await _create(client, analyst))["data"]
    billing_uuid = item["billing_uuid"]
    assert (
        await client.get(f"/v1/billing/{billing_uuid}/history", headers=analyst)
    ).status_code == 200

    assert (
        await client.delete(f"/v1/billing/items/{item['uuid']}", headers=analyst)
    ).status_code == 204

    assert (
        await client.get(f"/v1/billing/{billing_uuid}/history", headers=analyst)
    ).status_code == 404


async def test_replicacao_e_listagem_com_resumo(client, login):
    analyst = await login("analyst")
    resp = await client.post(
        "/v1/billing/items/replicate",
        json={**create_payload(), "subsequent_months": 3},
        headers=analyst,
    )
    assert resp.status_code == 201
    assert len(resp.json()["data"]) == 3

    lista = await client.get("/v1/billing?year=2026&month=9&per_page=5", headers=analyst)
    resumo = {s["status"]: s for s in lista.json()["status_summary"]}
    assert resumo["New"]["count"] == 1
    assert resumo["NoEntry"]["count"] > 0
    assert lista.json()["pagination"]["total"] == 2
