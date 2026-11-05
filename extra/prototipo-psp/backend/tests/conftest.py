"""Fixtures: app real sobre fakeredis, com os dados fictícios do seed."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from typing import Any

import fakeredis.aioredis
import httpx
import pytest
from fastapi import FastAPI

# Valores só de teste; nada disto é segredo real.
os.environ.setdefault("JWT_SECRET", "segredo-somente-para-testes-0123456789")
os.environ.setdefault("MOCK_LOGIN_PASSWORD", "senha-de-teste")
os.environ.setdefault("MOCK_OTP_CODE", "424242")

from src.core.config import Settings  # noqa: E402
from src.infrastructure.persistence.redis.seed import CLIENT_ALFA, CLIENT_GAMA, demo_id  # noqa: E402
from src.presentation.api.main import create_app  # noqa: E402

PASSWORD = os.environ["MOCK_LOGIN_PASSWORD"]
OTP = os.environ["MOCK_OTP_CODE"]
ALFA_FIXED_RULE = demo_id(f"rule/{CLIENT_ALFA}/101")
ALFA_MULT_RULE = demo_id(f"rule/{CLIENT_ALFA}/102")
ALFA_PERCENT_RULE = demo_id(f"rule/{CLIENT_ALFA}/103")
ALFA_RANGE_RULE = demo_id(f"rule/{CLIENT_ALFA}/104")
GAMA_FIXED_RULE = demo_id(f"rule/{CLIENT_GAMA}/301")


@pytest.fixture
async def redis() -> AsyncIterator[fakeredis.aioredis.FakeRedis]:
    server = fakeredis.aioredis.FakeRedis()
    yield server
    await server.aclose()


@pytest.fixture
async def app(redis: Any) -> AsyncIterator[FastAPI]:
    settings = Settings(RATE_LIMIT_ENABLED=False)  # type: ignore[call-arg]
    application = create_app(settings, redis)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


LoginFn = Callable[..., Any]


@pytest.fixture
def login(client: httpx.AsyncClient) -> LoginFn:
    """Faz login e devolve o cabeçalho Bearer (evita cookie para o teste ficar explícito)."""

    async def _login(username: str, *, mfa: bool = False) -> dict[str, str]:
        body: dict[str, str] = {"username": username, "password": PASSWORD}
        if mfa:
            body["otp"] = OTP
        resp = await client.post("/v1/auth/login", json=body)
        assert resp.status_code == 200, resp.text
        # O cookie tem prioridade sobre o Bearer; limpa para o teste controlar quem é o usuário.
        client.cookies.clear()
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _login


@pytest.fixture
def audit(app: FastAPI) -> Any:
    return app.state.container.audit


def create_payload(
    client_uuid: Any = CLIENT_ALFA, rule: Any = ALFA_FIXED_RULE, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "client_uuid": str(client_uuid),
        "service_rule_uuid": str(rule),
        "reference_year": 2026,
        "reference_month": 9,
        "billing_year": 2026,
        "billing_month": 9,
        "total_value": "1000.00",
    }
    payload.update(overrides)
    return payload
