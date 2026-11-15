"""Etapa 6 — regra D07 (autoaprovação recusada). Só para o protótipo corrigido.

O protótipo original aceita a autoaprovação, então não há recusa para detectar. Lá este teste
falharia pelo motivo certo: falta o controle de R18, não a regra de detecção.
"""

from __future__ import annotations

import json
from typing import Any

from tests.conftest import create_payload


async def test_d07_autoaprovacao_recusada_gera_alerta(client, login, redis):
    admin = await login("admin", mfa=True)
    criado = await client.post("/v1/billing/items", json=create_payload(), headers=admin)
    item = criado.json()["data"]["uuid"]
    url = f"/v1/billing/items/{item}/status"
    assert (
        await client.patch(url, json={"new_status": "ManagementApproval"}, headers=admin)
    ).status_code == 200

    resp = await client.patch(url, json={"new_status": "FinancialReview"}, headers=admin)

    assert resp.status_code == 403
    alertas: list[dict[str, Any]] = [json.loads(r) for r in await redis.lrange("psp:alerts", 0, -1)]
    d07 = [a for a in alertas if a["alert"] == "autoaprovacao_recusada"]
    assert len(d07) == 1
    assert (d07[0]["regra"], d07[0]["severidade"], d07[0]["lancamento"]) == ("D07", "Alta", item)
