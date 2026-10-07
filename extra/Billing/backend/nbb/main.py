import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from nbb.api import audit as audit_api
from nbb.api import auth, mfa, settings as settings_api, users
from nbb.api.deps import Container
from nbb.config import Settings, get_settings
from nbb.core.mailer import Mailer, OutboxMailer
from nbb.core.crypto import DataCipher
from nbb.core.oidc import OidcClient, build_clients
from nbb.core.ratelimit import LoginRateLimiter
from nbb.core.security import JwtKeyring
from nbb.db import new_session

log = logging.getLogger(__name__)
API_PREFIX = "/api/v1"


def build_container(settings: Settings, *, oidc: dict[str, OidcClient] | None = None,
                    mailer: Mailer | None = None) -> Container:
    return Container(
        settings=settings,
        keyring=JwtKeyring(settings),
        limiter=LoginRateLimiter(settings.redis_url, settings.login_rate_limit, settings.login_rate_window_seconds),
        # 2FA: no máximo N códigos errados por usuário a cada 5 minutos, somando todas as sessões.
        mfa_limiter=LoginRateLimiter(settings.redis_url, settings.mfa_max_attempts, 300),
        mailer=mailer or OutboxMailer(),
        cipher=DataCipher(settings.data_encryption_keys),
        oidc=oidc if oidc is not None else build_clients(settings.oidc_providers),
    )


def create_app(container: Container | None = None) -> FastAPI:
    app = FastAPI(
        title="Network Billing Backend",
        version="0.1.0",
        description="Faturamento da rede credenciada. Autenticação por cookie HttpOnly; "
                    "requisições que alteram dados exigem o cabeçalho X-CSRF-Token igual ao cookie nbb_csrf.",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
    )
    app.state.container = container or build_container(get_settings())

    for r in (auth.router, mfa.router, auth.me_router, users.router, audit_api.router, settings_api.router):
        app.include_router(r, prefix=API_PREFIX)

    @app.exception_handler(DBAPIError)
    def db_error(request: Request, exc: DBAPIError):
        sqlstate = getattr(exc.orig, "sqlstate", None)
        if sqlstate == "NB001":
            return JSONResponse(status_code=409, content={"detail": {
                "code": "immutable_record",
                "message": "Registro imutável: use estorno ou lançamento de ajuste."}})
        log.exception("Erro de banco")
        return JSONResponse(status_code=500, content={"detail": {"code": "db_error", "message": "Erro interno."}})

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    @app.get("/health/live", tags=["saude"], include_in_schema=False)
    def live():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["saude"], include_in_schema=False)
    def ready():
        db = new_session()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        return {"status": "ok"}

    return app
