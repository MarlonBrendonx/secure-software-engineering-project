"""Prática 2 — validação de token e MFA (RS02 / risco R02). Testes TS03 e TS04."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from tests.conftest import create_payload


async def _lancamento_aguardando_gestao(client: Any, login: Any) -> str:
    """Analista cria e envia o lançamento; fica pronto para o gestor aprovar."""
    analyst = await login("analyst")
    created = await client.post("/v1/billing/items", json=create_payload(), headers=analyst)
    item = created.json()["data"]["uuid"]
    sent = await client.patch(
        f"/v1/billing/items/{item}/status",
        json={"new_status": "ManagementApproval"},
        headers=analyst,
    )
    assert sent.status_code == 200, sent.text
    return item


async def test_ts03_gestor_com_mfa_aprova_lancamento(client, login):
    item = await _lancamento_aguardando_gestao(client, login)
    manager = await login("manager", mfa=True)

    resp = await client.patch(
        f"/v1/billing/items/{item}/status", json={"new_status": "FinancialReview"}, headers=manager
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "FinancialReview"


async def test_ts04_token_de_gestor_sem_mfa_e_recusado(client, login, audit):
    item = await _lancamento_aguardando_gestao(client, login)
    manager_sem_mfa = await login("manager", mfa=False)  # só a senha

    resp = await client.patch(
        f"/v1/billing/items/{item}/status",
        json={"new_status": "FinancialReview"},
        headers=manager_sem_mfa,
    )

    assert resp.status_code == 401
    assert resp.json()["motivo"] == "mfa_necessario"
    admin = await login("admin", mfa=True)
    atual = await client.get(f"/v1/billing/items/{item}", headers=admin)
    assert atual.json()["data"]["status"] == "ManagementApproval"  # nada foi aprovado
    tipos = [e.type for e in await audit.list_recent(10)]
    assert "mfa_ausente" in tipos


async def test_falhas_repetidas_de_mfa_geram_alerta(client, login, redis):
    item = await _lancamento_aguardando_gestao(client, login)
    manager_sem_mfa = await login("manager", mfa=False)

    for _ in range(5):
        await client.patch(
            f"/v1/billing/items/{item}/status",
            json={"new_status": "FinancialReview"},
            headers=manager_sem_mfa,
        )

    assert await redis.llen("psp:alerts") == 1


async def test_otp_errado_no_login_e_recusado_e_conta_como_falha(client):
    resp = await client.post(
        "/v1/auth/login",
        json={
            "username": "manager",
            "password": os.environ["MOCK_LOGIN_PASSWORD"],
            "otp": "000000",
        },
    )
    assert resp.status_code == 401
    assert resp.json()["motivo"] == "mfa_invalido"


async def test_claim_mfa_forjado_nao_basta_sem_mfa_na_sessao(client, login, app):
    """Quem forja o claim `amr` (ex.: segredo vazado) ainda esbarra na sessão do servidor."""
    manager_sem_mfa = await login("manager", mfa=False)
    token = manager_sem_mfa["Authorization"].removeprefix("Bearer ")
    secret = app.state.container.settings.JWT_SECRET
    claims = jwt.decode(token, secret, algorithms=["HS256"], audience="psp-api")
    forjado = jwt.encode({**claims, "amr": ["pwd", "mfa"]}, secret, algorithm="HS256")

    resp = await client.get(
        "/v1/billing?year=2026&month=9", headers={"Authorization": f"Bearer {forjado}"}
    )

    assert resp.status_code == 401
    assert resp.json()["motivo"] == "mfa_necessario"


def _token(app: Any, **overrides: Any) -> str:
    settings = app.state.container.settings
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": "analyst",
        "sid": "inexistente",
        "amr": ["pwd"],
        "type": "access",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "exp": now + timedelta(minutes=5),
        "iat": now,
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, settings.JWT_SECRET, algorithm="HS256")


async def test_token_invalido_e_recusado(client, login, app):
    casos = {
        "emissor errado": _token(app, iss="outro"),
        "audience errada": _token(app, aud="outra"),
        "expirado": _token(app, exp=datetime.now(UTC) - timedelta(minutes=1)),
        "sem sid": _token(app, sid=None),
        "sessão inexistente": _token(app),
        "assinado com outra chave": jwt.encode(
            {
                "sub": "analyst",
                "sid": "x",
                "iss": "psp-prototype",
                "aud": "psp-api",
                "exp": datetime.now(UTC) + timedelta(minutes=5),
            },
            "outra-chave-de-32-caracteres-xxxxxxxxxx",
            algorithm="HS256",
        ),
        "alg none": jwt.encode(
            {
                "sub": "analyst",
                "sid": "x",
                "iss": "psp-prototype",
                "aud": "psp-api",
                "exp": datetime.now(UTC) + timedelta(minutes=5),
            },
            None,
            algorithm="none",
        ),
    }
    for nome, token in casos.items():
        resp = await client.get(
            "/v1/billing?year=2026&month=9", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401, nome


async def test_logout_revoga_a_sessao_mesmo_com_token_ainda_valido(client, login):
    analyst = await login("analyst")
    assert (await client.get("/v1/billing?year=2026&month=9", headers=analyst)).status_code == 200

    assert (await client.post("/v1/auth/logout", headers=analyst)).status_code == 200

    resp = await client.get("/v1/billing?year=2026&month=9", headers=analyst)
    assert resp.status_code == 401
    assert resp.json()["motivo"] == "sessao_invalida"


async def test_refresh_nao_promove_login_sem_mfa(client):
    login_resp = await client.post(
        "/v1/auth/login",
        json={"username": "manager", "password": os.environ["MOCK_LOGIN_PASSWORD"]},
    )
    assert login_resp.status_code == 200
    renovado = await client.post("/v1/auth/refresh")
    assert renovado.status_code == 200
    sessao = await client.get("/v1/auth/get-session")
    assert sessao.json()["mfa"] is False
