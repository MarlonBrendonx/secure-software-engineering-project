"""Rotas de autenticação (login mock, sessão, renovação, logout)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from src.application.authenticator import AuthenticatedUser
from src.application.use_cases.auth.login import LoginCommand
from src.core.config import Settings
from src.domain.exceptions import UnauthenticatedError
from src.domain.ports.services.token_service import IssuedTokens
from src.presentation.api.deps import (
    ContainerDep,
    client_ip,
    public_route,
    rate_limit,
    require_session,
)
from src.presentation.api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LoginUser,
    SessionResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

SessionUser = Annotated[AuthenticatedUser, Depends(require_session)]


def _set_cookies(response: Response, tokens: IssuedTokens, settings: Settings) -> None:
    """HttpOnly: o JavaScript da página não lê o token. O refresh só viaja para /refresh."""
    common: dict[str, Any] = {
        "httponly": True,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "domain": settings.AUTH_COOKIE_DOMAIN or None,
    }
    response.set_cookie(
        "access_token", tokens.access_token, max_age=tokens.expires_in, path="/", **common
    )
    response.set_cookie(
        "refresh_token",
        tokens.refresh_token,
        max_age=tokens.refresh_expires_in,
        path="/v1/auth/refresh",
        **common,
    )


def _clear_cookies(response: Response, settings: Settings) -> None:
    domain = settings.AUTH_COOKIE_DOMAIN or None
    response.delete_cookie("access_token", path="/", domain=domain)
    response.delete_cookie("refresh_token", path="/v1/auth/refresh", domain=domain)


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(public_route), Depends(rate_limit("login", 10))],
)
async def login(
    request: Request, response: Response, body: LoginRequest, container: ContainerDep
) -> LoginResponse:
    result = await container.login.execute(
        LoginCommand(body.username, body.password, body.otp, client_ip(request))
    )
    _set_cookies(response, result.tokens, container.settings)
    return LoginResponse(
        access_token=result.tokens.access_token,
        expires_in=result.tokens.expires_in,
        refresh_token=result.tokens.refresh_token,
        user=LoginUser(
            username=result.user.username,
            role=str(result.user.role),
            display_name=result.user.display_name,
            email=result.user.email,
        ),
        mfa="mfa" in result.amr,
    )


@router.post("/refresh", dependencies=[Depends(public_route)])
async def refresh(request: Request, container: ContainerDep) -> JSONResponse:
    token = request.cookies.get("refresh_token")
    if not token:
        raise UnauthenticatedError("Missing refresh token", "token_ausente")
    tokens = await container.refresh.execute(token)
    response = JSONResponse({"access_token": tokens.access_token, "expires_in": tokens.expires_in})
    _set_cookies(response, tokens, container.settings)
    return response


@router.post("/logout")
async def logout(response: Response, auth: SessionUser, container: ContainerDep) -> dict[str, str]:
    await container.logout.execute(auth.user.username, auth.claims.sid)
    _clear_cookies(response, container.settings)
    return {"message": "Logged out"}


@router.get("/get-session", response_model=SessionResponse)
async def get_session(auth: SessionUser) -> SessionResponse:
    # Não exige MFA: o frontend precisa saber quem é o usuário e se o MFA foi concluído,
    # mesmo quando a API vai recusar as ações privilegiadas.
    return SessionResponse(
        username=auth.user.username,
        role=str(auth.user.role),
        display_name=auth.user.display_name,
        email=auth.user.email,
        exp=auth.claims.exp,
        mfa=auth.claims.mfa_completed,
    )


__all__ = ["router"]
