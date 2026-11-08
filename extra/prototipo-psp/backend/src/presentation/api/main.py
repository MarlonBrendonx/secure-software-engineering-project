"""Aplicação FastAPI do protótipo PSP."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from src.core.config import Settings, get_settings
from src.infrastructure.persistence.redis.seed import seed_demo_data
from src.presentation.api.container import Container
from src.presentation.api.deps import assert_all_routes_have_policy
from src.presentation.api.exceptions import register_exception_handlers
from src.presentation.api.routes import audit, auth, billing, registry, ws


def create_app(settings: Settings | None = None, redis: Redis | None = None) -> FastAPI:
    """Fábrica da aplicação. Aceita `settings` e `redis` para os testes injetarem os seus."""
    settings = settings or get_settings()
    owns_redis = redis is None
    redis = redis or Redis.from_url(settings.REDIS_URL)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if settings.SEED_ON_STARTUP:
            await seed_demo_data(redis)
        yield
        if owns_redis:
            await redis.aclose()

    app = FastAPI(title="Faturamento PSP — protótipo", version="0.1.0", lifespan=lifespan)
    app.state.container = Container(settings, redis)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    register_exception_handlers(app)
    routers = [
        ("/v1", auth.router),
        ("/v1/billing", billing.router),
        ("/v1", audit.router),
        ("/v1", registry.router),
        ("", ws.router),
    ]
    for prefix, router in routers:
        app.include_router(router, prefix=prefix)

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    assert_all_routes_have_policy(routers)
    return app
