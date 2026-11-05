"""Dependências do FastAPI: guards de acesso, limite de requisições e utilidades.

Toda rota declara a sua política de acesso por uma destas dependências (RS06). A função
`assert_all_routes_have_policy` impede a aplicação de subir com rota sem política.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.routing import APIRoute

from src.application.authenticator import AuthenticatedUser
from src.domain.exceptions import DomainError
from src.presentation.api.container import Container
from src.presentation.api.schemas.common import PaginationParams

logger = logging.getLogger("psp.api")

POLICY_ATTR = "policy"


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def client_ip(request: Request) -> str:
    # Não confia em X-Forwarded-For: o cabeçalho é do cliente e burlaria o limite por IP.
    return request.client.host if request.client else "desconhecido"


def extract_token(request: Request) -> str | None:
    """O cookie `access_token` tem prioridade; na falta dele, vale o cabeçalho Bearer."""
    cookie = request.cookies.get("access_token")
    if cookie:
        return cookie
    header = request.headers.get("Authorization", "")
    scheme, _, value = header.partition(" ")
    return value if scheme.lower() == "bearer" and value else None


def _with_policy(dependency: Callable[..., Any], policy: object) -> Any:
    setattr(dependency, POLICY_ATTR, policy)
    return dependency


def require_roles(*roles: str) -> Callable[..., Coroutine[Any, Any, AuthenticatedUser]]:
    """Guard de perfil + sessão + MFA. Nega por padrão: falha inesperada nunca libera."""
    allowed = frozenset(roles)

    async def dependency(request: Request, container: ContainerDep) -> AuthenticatedUser:
        try:
            return await container.authenticator.authorize(
                extract_token(request),
                allowed_roles=allowed,
                route=request.url.path,
                origin=client_ip(request),
            )
        except (DomainError, HTTPException):
            raise
        except Exception:
            logger.exception("Falha ao verificar acesso; requisição negada")
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "Verificação de acesso indisponível"
            ) from None

    return _with_policy(dependency, allowed)


async def _require_session(request: Request, container: ContainerDep) -> AuthenticatedUser:
    """Sessão válida, sem exigir perfil específico nem MFA (ex.: consultar a própria sessão)."""
    try:
        return await container.authenticator.identify(extract_token(request))
    except (DomainError, HTTPException):
        raise
    except Exception:
        logger.exception("Falha ao verificar sessão; requisição negada")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Verificação de acesso indisponível"
        ) from None


require_session: Any = _with_policy(_require_session, "session")


async def _public_route() -> None:
    """Marcador explícito de rota pública (login e refresh)."""


public_route: Any = _with_policy(_public_route, "public")


def rate_limit(name: str, limit: int, window_seconds: int = 60) -> Callable[..., Any]:
    """Limite de requisições por IP e por rota (contador no Redis)."""

    async def dependency(request: Request, container: ContainerDep) -> None:
        if not container.settings.RATE_LIMIT_ENABLED:
            return
        total = await container.counters.increment(
            f"rl:{name}:{client_ip(request)}", window_seconds
        )
        if total > limit:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Limite de requisições excedido",
                headers={"Retry-After": str(window_seconds)},
            )

    return dependency


def get_request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def get_pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginationParams:
    return PaginationParams(page=page, per_page=per_page)


RequestId = Annotated[str, Depends(get_request_id)]
Pagination = Annotated[PaginationParams, Depends(get_pagination)]

# Perfis com acesso ao negócio do PSP.
billing_user = require_roles("analyst", "manager", "admin")
BillingUser = Annotated[AuthenticatedUser, Depends(billing_user)]
AdminUser = Annotated[AuthenticatedUser, Depends(require_roles("admin"))]


def assert_all_routes_have_policy(routers: list[tuple[str, APIRouter]]) -> None:
    """Falha a inicialização se alguma rota não declarar a política de acesso (RS06).

    Recebe os routers (prefixo → router) em vez de `app.routes`: nas versões novas do FastAPI
    o `include_router` é resolvido de forma preguiçosa e `app.routes` não lista as rotas.
    """
    missing: list[str] = []
    checked = 0
    for prefix, router in routers:
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            checked += 1
            declared = any(
                getattr(dep.call, POLICY_ATTR, None) is not None
                for dep in route.dependant.dependencies
            )
            if not declared:
                missing.append(f"{sorted(route.methods or [])} {prefix}{route.path}")
    if missing:
        raise RuntimeError(f"Rotas sem política de acesso declarada: {missing}")
    if checked == 0:
        raise RuntimeError("Nenhuma rota encontrada para verificar a política de acesso")
