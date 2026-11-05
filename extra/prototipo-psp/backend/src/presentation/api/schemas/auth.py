"""Schemas de autenticação."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)
    # Segundo fator (mock). Sem ele o token sai com amr=["pwd"] e a API recusa
    # os perfis privilegiados.
    otp: str | None = Field(default=None, max_length=20)


class LoginUser(BaseModel):
    username: str
    role: str
    display_name: str
    email: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None
    user: LoginUser
    mfa: bool


class SessionResponse(BaseModel):
    username: str
    role: str
    display_name: str
    email: str
    exp: int
    mfa: bool
