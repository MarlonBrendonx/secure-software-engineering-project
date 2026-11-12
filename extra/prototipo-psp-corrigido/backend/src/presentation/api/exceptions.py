"""Tratamento de erros: todo erro sai no envelope padrão, sem vazar detalhes internos."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.domain.exceptions import (
    BusinessValidationError,
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    UnauthenticatedError,
)

logger = logging.getLogger("psp.api")

_DOMAIN_STATUS: dict[type[DomainError], tuple[int, str]] = {
    NotFoundError: (404, "NOT_FOUND"),
    ConflictError: (409, "CONFLICT"),
    BusinessValidationError: (422, "VALIDATION_ERROR"),
    ForbiddenError: (403, "FORBIDDEN"),
}


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def _meta(request: Request) -> dict[str, str]:
    return {"request_id": _request_id(request), "timestamp": datetime.now(UTC).isoformat()}


def error_body(
    request: Request, code: str, message: str, field: str | None = None
) -> dict[str, Any]:
    return {
        "success": False,
        "error": {"code": code, "message": message, "field": field},
        "meta": _meta(request),
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UnauthenticatedError)
    async def _unauthenticated(request: Request, exc: UnauthenticatedError) -> JSONResponse:
        body = error_body(request, exc.reason, str(exc.detail))
        # `motivo` no topo é o contrato estável que os testes TS03 e TS04 verificam.
        body["motivo"] = exc.reason
        return JSONResponse(body, status_code=401, headers={"WWW-Authenticate": "Bearer"})

    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError) -> JSONResponse:
        status_code, code = 500, "INTERNAL_ERROR"
        for cls, (s, c) in _DOMAIN_STATUS.items():
            if isinstance(exc, cls):
                status_code, code = s, c
                break

        # Lista de erros (ex.: lote com vários itens inválidos): o frontend lê `errors`.
        if isinstance(exc.detail, list):
            body: dict[str, Any] = {
                "success": False,
                "errors": [{"code": code, "message": str(m)} for m in exc.detail],
                "meta": _meta(request),
            }
            return JSONResponse(body, status_code=status_code)
        return JSONResponse(error_body(request, code, str(exc.detail)), status_code=status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "code": "VALIDATION_ERROR",
                "message": str(e.get("msg", "Valor inválido")).removeprefix("Value error, "),
                "field": ".".join(str(p) for p in e.get("loc", ()) if p not in ("body", "query")),
            }
            for e in exc.errors()
        ]
        return JSONResponse(
            {"success": False, "errors": errors, "meta": _meta(request)}, status_code=422
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 429: "RATE_LIMITED"}.get(
            exc.status_code, "HTTP_ERROR"
        )
        return JSONResponse(
            error_body(request, code, str(exc.detail)),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        # A causa fica no log; o cliente recebe só uma mensagem genérica.
        logger.exception("Erro não tratado em %s", request.url.path)
        return JSONResponse(
            error_body(request, "INTERNAL_ERROR", "Erro interno do servidor"), status_code=500
        )
