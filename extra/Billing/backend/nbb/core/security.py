"""Senhas, tokens opacos e JWT com chaveiro rotacionável."""
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from nbb.config import Settings

_hasher = PasswordHasher()  # Argon2id com os parâmetros recomendados pela biblioteca

# Hash fictício para igualar o tempo de resposta quando o login não existe.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def validate_password_policy(password: str, min_length: int) -> None:
    if len(password) < min_length:
        raise ValueError(f"A senha precisa ter pelo menos {min_length} caracteres.")
    classes = sum([
        any(c.islower() for c in password),
        any(c.isupper() for c in password),
        any(c.isdigit() for c in password),
        any(not c.isalnum() for c in password),
    ])
    if classes < 3:
        raise ValueError("A senha precisa combinar ao menos 3 tipos: minúsculas, maiúsculas, dígitos, símbolos.")


def new_opaque_token() -> tuple[str, str]:
    """Gera um token aleatório e devolve (token, sha256 hex). Só o hash é guardado."""
    token = secrets.token_urlsafe(32)
    return token, sha256_hex(token)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    session_id: uuid.UUID
    token_version: int
    kid: str


class TokenError(Exception):
    pass


class JwtKeyring:
    """Assina com a chave ativa e valida com qualquer chave do chaveiro.

    Rotação periódica: adicionar a nova chave, torná-la ativa e remover a
    antiga depois de `access_token_ttl_seconds`. Em suspeita de vazamento,
    remover a chave comprometida invalida na hora todos os tokens assinados
    com ela (ver `nbb rotate-keys --emergency`).
    """

    ALG = "HS256"

    def __init__(self, settings: Settings):
        settings.validate_for_runtime()
        self._keys = dict(settings.jwt_keys)
        self._active = settings.jwt_active_kid
        self._issuer = settings.jwt_issuer
        self._ttl = settings.access_token_ttl_seconds

    def issue(self, user_id: uuid.UUID, session_id: uuid.UUID, token_version: int) -> tuple[str, datetime]:
        now = datetime.now(UTC)
        exp = now + timedelta(seconds=self._ttl)
        payload = {
            "iss": self._issuer,
            "sub": str(user_id),
            "sid": str(session_id),
            "tv": token_version,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "jti": secrets.token_hex(8),
        }
        token = jwt.encode(payload, self._keys[self._active], algorithm=self.ALG, headers={"kid": self._active})
        return token, exp

    def sign_aux(self, purpose: str, data: dict, ttl_seconds: int) -> str:
        """Assina dados auxiliares de curta duração (ex.: state do OIDC)."""
        now = datetime.now(UTC)
        payload = {"pur": purpose, "dat": data, "iat": int(now.timestamp()),
                   "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp())}
        return jwt.encode(payload, self._keys[self._active], algorithm=self.ALG, headers={"kid": self._active})

    def verify_aux(self, purpose: str, token: str) -> dict:
        try:
            kid = jwt.get_unverified_header(token).get("kid")
            key = self._keys[kid]
            data = jwt.decode(token, key, algorithms=[self.ALG], options={"require": ["exp"]})
        except (jwt.PyJWTError, KeyError) as exc:
            raise TokenError("dados assinados inválidos") from exc
        if data.get("pur") != purpose:
            raise TokenError("finalidade incorreta")
        return data["dat"]

    def verify(self, token: str) -> AccessClaims:
        try:
            kid = jwt.get_unverified_header(token).get("kid")
        except jwt.PyJWTError as exc:
            raise TokenError("token malformado") from exc
        key = self._keys.get(kid or "")
        if key is None:
            raise TokenError("chave desconhecida ou revogada")
        try:
            data = jwt.decode(
                token, key, algorithms=[self.ALG], issuer=self._issuer,
                options={"require": ["exp", "iat", "sub", "sid", "tv"]},
            )
            return AccessClaims(uuid.UUID(data["sub"]), uuid.UUID(data["sid"]), int(data["tv"]), kid)
        except (jwt.PyJWTError, ValueError, KeyError) as exc:
            raise TokenError("token inválido ou expirado") from exc
