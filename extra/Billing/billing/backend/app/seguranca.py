"""Tokens de acesso, tokens de renovação e segundo fator (TOTP)."""
import base64
import hashlib
import secrets
from datetime import datetime, timedelta

import jwt
import pyotp
from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings
from .models import agora

TIPO_ACESSO = "acesso"
TIPO_DESAFIO_MFA = "desafio_mfa"


class TokenInvalido(Exception):
    pass


# --------------------------- JWT -------------------------------------------
def _chaves() -> dict[str, str]:
    s = get_settings()
    chaves = {s.jwt_kid_atual: s.jwt_chave_atual}
    if s.jwt_chave_anterior and s.jwt_kid_anterior:
        chaves[s.jwt_kid_anterior] = s.jwt_chave_anterior
    return chaves


def emitir_jwt(dados: dict, duracao: timedelta) -> str:
    s = get_settings()
    inicio = agora()
    payload = {**dados, "iat": inicio, "exp": inicio + duracao, "jti": secrets.token_hex(16)}
    return jwt.encode(payload, s.jwt_chave_atual, algorithm=s.jwt_algoritmo, headers={"kid": s.jwt_kid_atual})


def ler_jwt(token: str, tipo_esperado: str) -> dict:
    s = get_settings()
    try:
        kid = jwt.get_unverified_header(token).get("kid")
        chave = _chaves().get(kid)
        if chave is None:
            raise TokenInvalido("Chave de assinatura desconhecida")
        payload = jwt.decode(token, chave, algorithms=[s.jwt_algoritmo], options={"require": ["exp", "iat", "jti"]})
    except jwt.ExpiredSignatureError as exc:
        raise TokenInvalido("Token expirado") from exc
    except jwt.PyJWTError as exc:
        raise TokenInvalido("Token inválido") from exc
    if payload.get("typ") != tipo_esperado:
        raise TokenInvalido("Tipo de token incorreto")
    return payload


def emitir_access_token(usuario_id: int, papel: str, sessao_id: str) -> str:
    s = get_settings()
    return emitir_jwt(
        {"sub": str(usuario_id), "papel": papel, "sid": sessao_id, "typ": TIPO_ACESSO},
        timedelta(minutes=s.access_token_minutos),
    )


def emitir_desafio_mfa(usuario_id: int) -> str:
    s = get_settings()
    return emitir_jwt({"sub": str(usuario_id), "typ": TIPO_DESAFIO_MFA}, timedelta(minutes=s.desafio_mfa_minutos))


# --------------------------- Refresh token (opaco) --------------------------
def novo_refresh_token() -> tuple[str, str]:
    """Retorna (token para o cookie, hash para o banco). O banco nunca guarda o token."""
    token = secrets.token_urlsafe(48)
    return token, hash_refresh(token)


def hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def expiracao_sessao() -> datetime:
    return agora() + timedelta(hours=get_settings().sessao_maxima_horas)


# --------------------------- Segundo fator (TOTP) ---------------------------
def _fernet() -> Fernet:
    chave = hashlib.sha256(get_settings().mfa_chave_cifragem.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(chave))


def novo_segredo_mfa() -> str:
    return pyotp.random_base32()


def cifrar_segredo(segredo: str) -> str:
    return _fernet().encrypt(segredo.encode()).decode()


def decifrar_segredo(cifrado: str) -> str:
    try:
        return _fernet().decrypt(cifrado.encode()).decode()
    except InvalidToken as exc:
        raise TokenInvalido("Segredo do segundo fator ilegível") from exc


def uri_mfa(segredo: str, login: str) -> str:
    return pyotp.TOTP(segredo).provisioning_uri(name=login, issuer_name=get_settings().mfa_emissor)


def verificar_codigo_mfa(segredo: str, codigo: str) -> bool:
    codigo = (codigo or "").strip()
    if not (codigo.isdigit() and len(codigo) == 6):
        return False
    return pyotp.TOTP(segredo).verify(codigo, valid_window=1)
