"""Critérios de verificação de RS01, R18 e RS05 (etapa 3, tabela de requisitos).

- RS01: depois do envio para aprovação, PATCH e DELETE diretos são recusados; a mudança só
  ocorre pela transição "reabrir" (volta a `New`) e exige novo envio e nova aprovação.
- R18 (premissa de RS01): quem criou, enviou ou alterou o lançamento não o aprova.
- RS05: a auditoria é gravada na mesma transação da operação; se falhar, nada é efetivado.

No fim, dois `xfail` documentam o que ainda não foi implementado (RS04 assimétrico e RS08).
"""

from __future__ import annotations

from typing import Any

import pytest

from src.infrastructure.persistence.redis import billing_gateways
from tests.conftest import ALFA_MULT_RULE, PASSWORD, create_payload


async def _create(client: Any, headers: dict[str, str]) -> dict[str, Any]:
    resp = await client.post("/v1/billing/items", json=create_payload(), headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


async def _get(client: Any, item: str, headers: dict[str, str]) -> dict[str, Any]:
    return (await client.get(f"/v1/billing/items/{item}", headers=headers)).json()["data"]


async def _status(client: Any, item: str, new: str, headers: dict[str, str]) -> Any:
    return await client.patch(
        f"/v1/billing/items/{item}/status", json={"new_status": new}, headers=headers
    )


async def _patch(client: Any, item: str, headers: dict[str, str], **fields: Any) -> Any:
    version = (await _get(client, item, headers))["version"]
    return await client.patch(
        f"/v1/billing/items/{item}", json={"version": version, **fields}, headers=headers
    )


# ── RS01 ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "etapa", [["ManagementApproval"], ["ManagementApproval", "FinancialReview"]]
)
async def test_rs01_patch_e_delete_apos_envio_sao_recusados(client, login, etapa):
    analyst = await login("analyst")
    manager = await login("manager", mfa=True)
    item = (await _create(client, analyst))["uuid"]
    for new in etapa:
        headers = analyst if new == "ManagementApproval" else manager
        assert (await _status(client, item, new, headers)).status_code == 200

    alterar = await _patch(client, item, analyst, notes="alterado depois do envio")
    excluir = await client.delete(f"/v1/billing/items/{item}", headers=analyst)

    assert (alterar.status_code, excluir.status_code) == (422, 422)
    assert (await _get(client, item, analyst)).get("notes") != "alterado depois do envio"


async def test_rs01_rascunho_e_reprovado_continuam_editaveis(client, login):
    analyst = await login("analyst")
    manager = await login("manager", mfa=True)
    item = (await _create(client, analyst))["uuid"]
    assert (await _patch(client, item, analyst, notes="rascunho")).status_code == 200

    assert (await _status(client, item, "ManagementApproval", analyst)).status_code == 200
    reprovar = await client.patch(
        f"/v1/billing/items/{item}/status",
        json={"new_status": "Rejected", "rejection_reason": "valor errado"},
        headers=manager,
    )
    assert reprovar.status_code == 200
    assert (await _patch(client, item, analyst, notes="corrigido")).status_code == 200


async def test_rs01_reabrir_exige_novo_envio_e_nova_aprovacao(client, login, audit):
    analyst = await login("analyst")
    manager = await login("manager", mfa=True)
    item = (await _create(client, analyst))["uuid"]
    assert (await _status(client, item, "ManagementApproval", analyst)).status_code == 200

    # Gestor não reabre: reabrir é do perfil que envia.
    assert (await _status(client, item, "New", manager)).status_code == 403
    assert (await _status(client, item, "New", analyst)).status_code == 200
    assert (await _patch(client, item, analyst, notes="depois de reabrir")).status_code == 200

    # Volta a precisar do fluxo inteiro: não pula do rascunho para a aprovação.
    assert (await _status(client, item, "FinancialReview", manager)).status_code == 422
    assert (await _status(client, item, "ManagementApproval", analyst)).status_code == 200
    assert (await _status(client, item, "FinancialReview", manager)).status_code == 200
    assert (await _status(client, item, "Approved", manager)).status_code == 200

    transicoes = [e.detail for e in await audit.list_recent() if e.type == "mudanca_status"]
    assert "ManagementApproval → New" in transicoes


async def test_rs01_aprovado_nao_reabre(client, login):
    analyst = await login("analyst")
    manager = await login("manager", mfa=True)
    item = (await _create(client, analyst))["uuid"]
    assert (await _status(client, item, "ManagementApproval", analyst)).status_code == 200
    assert (await _status(client, item, "FinancialReview", manager)).status_code == 200
    assert (await _status(client, item, "Approved", manager)).status_code == 200
    assert (await _status(client, item, "New", analyst)).status_code == 422


# ── R18 ──────────────────────────────────────────────────────────────


async def test_r18_admin_nao_aprova_o_proprio_lancamento(client, login, audit):
    admin = await login("admin", mfa=True)
    item = (await _create(client, admin))["uuid"]
    assert (await _status(client, item, "ManagementApproval", admin)).status_code == 200

    resp = await _status(client, item, "FinancialReview", admin)

    assert resp.status_code == 403
    assert (await _get(client, item, admin))["status"] == "ManagementApproval"
    negadas = [e for e in await audit.list_recent() if e.type == "autoaprovacao_negada"]
    assert [(e.user, e.resource_id) for e in negadas] == [("admin", item)]


async def test_r18_admin_que_alterou_o_lancamento_nao_o_aprova(client, login):
    analyst = await login("analyst")
    admin = await login("admin", mfa=True)
    item = (await _create(client, analyst))["uuid"]
    assert (await _patch(client, item, admin, notes="ajuste do admin")).status_code == 200
    assert (await _status(client, item, "ManagementApproval", analyst)).status_code == 200

    assert (await _status(client, item, "FinancialReview", admin)).status_code == 403


async def test_r18_admin_aprova_lancamento_de_outra_pessoa(client, login):
    analyst = await login("analyst")
    admin = await login("admin", mfa=True)
    item = (await _create(client, analyst))["uuid"]
    assert (await _status(client, item, "ManagementApproval", analyst)).status_code == 200
    assert (await _status(client, item, "FinancialReview", admin)).status_code == 200
    assert (await _status(client, item, "Approved", admin)).status_code == 200


async def test_r18_lote_com_autoaprovacao_nao_muda_nenhum_item(client, login):
    analyst = await login("analyst")
    admin = await login("admin", mfa=True)
    alheio = (await _create(client, analyst))["uuid"]
    resp = await client.post(
        "/v1/billing/items",
        json=create_payload(rule=ALFA_MULT_RULE, quantity="10"),
        headers=admin,
    )
    assert resp.status_code == 201, resp.text
    proprio = resp.json()["data"]["uuid"]
    for item, quem in ((alheio, analyst), (proprio, admin)):
        assert (await _status(client, item, "ManagementApproval", quem)).status_code == 200

    lote = await client.post(
        "/v1/billing/items/batch-status",
        json={"item_uuids": [alheio, proprio], "new_status": "FinancialReview"},
        headers=admin,
    )

    assert lote.status_code == 403
    assert (await _get(client, alheio, admin))["status"] == "ManagementApproval"


# ── RS05 ─────────────────────────────────────────────────────────────


async def test_rs05_alteracao_grava_item_timeline_e_auditoria_juntos(client, login, audit):
    analyst = await login("analyst")
    item = (await _create(client, analyst))["uuid"]
    assert (await _patch(client, item, analyst, notes="com rastro")).status_code == 200

    eventos = [(e.type, e.resource_id) for e in await audit.list_recent()]
    assert ("lancamento_criado", item) in eventos
    assert ("lancamento_atualizado", item) in eventos


@pytest.mark.parametrize("operacao", ["alterar", "mudar_status", "excluir"])
async def test_rs05_falha_na_auditoria_desfaz_a_operacao(
    client, login, audit, monkeypatch, operacao
):
    analyst = await login("analyst")
    item = (await _create(client, analyst))["uuid"]
    antes = await _get(client, item, analyst)
    eventos_antes = len(await audit.list_recent())

    def falha(pipe: Any, event: Any) -> None:
        raise RuntimeError("auditoria indisponível")

    monkeypatch.setattr(billing_gateways, "queue_audit", falha)
    with pytest.raises(RuntimeError):
        if operacao == "alterar":
            await _patch(client, item, analyst, notes="sem rastro")
        elif operacao == "mudar_status":
            await _status(client, item, "ManagementApproval", analyst)
        else:
            await client.delete(f"/v1/billing/items/{item}", headers=analyst)
    monkeypatch.undo()

    depois = await _get(client, item, analyst)
    assert depois is not None, "lançamento excluído sem registro de auditoria"
    assert (depois["notes"], depois["status"], depois["version"]) == (
        antes["notes"],
        antes["status"],
        antes["version"],
    )
    assert len(await audit.list_recent()) == eventos_antes


# ── Ainda não implementado (documentado) ─────────────────────────────


@pytest.mark.xfail(
    reason="RS04 parcial: o token ainda é HS256, sem chave assimétrica em cofre", strict=True
)
def test_rs04_assinatura_assimetrica():
    from src.core.config import Settings

    assert Settings().JWT_ALGORITHM.startswith(("RS", "ES", "PS", "EdDSA"))  # type: ignore[call-arg]


@pytest.mark.xfail(
    reason="RS08 não implementado: sem token anti-CSRF nem checagem de Origin", strict=True
)
async def test_rs08_requisicao_so_com_cookie_e_origem_externa_e_recusada(client):
    resp = await client.post("/v1/auth/login", json={"username": "analyst", "password": PASSWORD})
    assert resp.status_code == 200 and client.cookies.get("access_token")
    item = (await client.post("/v1/billing/items", json=create_payload())).json()["data"]

    # Página de outro site induz o navegador: só o cookie, Origin externo, sem token anti-CSRF.
    resp = await client.patch(
        f"/v1/billing/items/{item['uuid']}",
        json={"version": item["version"], "notes": "csrf"},
        headers={"Origin": "https://site-malicioso.example"},
    )
    assert resp.status_code == 403
