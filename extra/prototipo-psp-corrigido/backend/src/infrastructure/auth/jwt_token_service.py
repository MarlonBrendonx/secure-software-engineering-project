"""Emissão e validação de tokens JWT (RS02 e RS04 / Prática 2, seção 3.2).

A API não confia só na assinatura: confere algoritmo, emissor, audience, prazo e a
presença dos claims obrigatórios. Qualquer falha vira 401.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import jwt

from src.domain.entities.session import TokenClaims
from src.domain.exceptions import UnauthenticatedError
from src.domain.ports.services.token_service import IssuedTokens

_REQUIRED_CLAIMS = ["exp", "iss", "aud", "sub", "sid"]


class JwtTokenService:
    def __init__(
        self,
        *,
        secret: str,
        algorithm: str,
        issuer: str,
        audience: str,
        access_ttl_minutes: int,
        refresh_ttl_minutes: int,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._issuer = issuer
        self._audience = audience
        self._access_ttl = access_ttl_minutes * 60
        self._refresh_ttl = refresh_ttl_minutes * 60

    def issue(
        self,
        *,
        username: str,
        sid: str,
        amr: list[str],
        role: str,
        display_name: str,
        email: str,
    ) -> IssuedTokens:
        now = int(datetime.now(UTC).timestamp())
        common: dict[str, Any] = {
            "sub": username,
            "sid": sid,
            "amr": amr,
            "iss": self._issuer,
            "aud": self._audience,
            "iat": now,
        }
        # `role` e os dados de exibição seguem no token só para o frontend mostrar o usuário;
        # a API decide o perfil pelo cadastro, nunca por este claim.
        access = {
            **common,
            "type": "access",
            "role": role,
            "display_name": display_name,
            "email": email,
            "exp": now + self._access_ttl,
            "jti": str(uuid.uuid4()),
        }
        refresh = {
            **common,
            "type": "refresh",
            "exp": now + self._refresh_ttl,
            "jti": str(uuid.uuid4()),
        }
        return IssuedTokens(
            access_token=jwt.encode(access, self._secret, algorithm=self._algorithm),
            refresh_token=jwt.encode(refresh, self._secret, algorithm=self._algorithm),
            expires_in=self._access_ttl,
            refresh_expires_in=self._refresh_ttl,
        )

    def decode_access(self, token: str) -> TokenClaims:
        return self._decode(token, expected_type="access")

    def decode_refresh(self, token: str) -> TokenClaims:
        return self._decode(token, expected_type="refresh")

    def _decode(self, token: str, *, expected_type: str) -> TokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],  # lista fixa: nunca aceita "none"
                issuer=self._issuer,
                audience=self._audience,
                options={"require": _REQUIRED_CLAIMS},
            )
        except jwt.ExpiredSignatureError:
            raise UnauthenticatedError("Token expired", "token_expirado") from None
        except jwt.InvalidTokenError:
            raise UnauthenticatedError("Invalid token", "token_invalido") from None

        # Impede usar um refresh token como access token (e o inverso).
        if payload.get("type") != expected_type:
            raise UnauthenticatedError("Invalid token", "token_invalido")

        return TokenClaims(
            sub=payload["sub"],
            sid=payload["sid"],
            amr=tuple(payload.get("amr", [])),
            exp=payload["exp"],
            jti=payload.get("jti", ""),
            token_type=expected_type,
        )
