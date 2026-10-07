"""TOTP (RFC 6238), compatível com Google Authenticator, Microsoft
Authenticator, Authy, 1Password etc.: SHA-1, 6 dígitos, passo de 30 s."""
import secrets
import time

import pyotp
import segno

STEP_SECONDS = 30
DIGITS = 6
# Aceita o código do passo anterior e do seguinte (relógio do celular adiantado/atrasado).
VALID_WINDOW = 1


def new_secret() -> str:
    return pyotp.random_base32(length=32)  # 160 bits


def provisioning_uri(secret: str, account: str, issuer: str) -> str:
    return pyotp.TOTP(secret, digits=DIGITS, interval=STEP_SECONDS).provisioning_uri(
        name=account, issuer_name=issuer)


def qr_svg_data_uri(uri: str) -> str:
    return segno.make(uri, error="m").svg_data_uri(scale=5, border=2)


def current_step(now: float | None = None) -> int:
    return int((now if now is not None else time.time()) // STEP_SECONDS)


def match_step(secret: str, code: str, now: float | None = None) -> int | None:
    """Devolve o passo de tempo em que o código é válido, ou None.

    O passo devolvido permite recusar a reutilização do mesmo código
    (proteção contra replay): só vale código de passo maior que o último usado.
    """
    code = (code or "").strip().replace(" ", "")
    if len(code) != DIGITS or not code.isdigit():
        return None
    totp = pyotp.TOTP(secret, digits=DIGITS, interval=STEP_SECONDS)
    step = current_step(now)
    found = None
    for s in range(step - VALID_WINDOW, step + VALID_WINDOW + 1):
        # Compara todos os candidatos em tempo constante, sem sair cedo.
        if secrets.compare_digest(totp.at(s * STEP_SECONDS), code):
            found = s
    return found


def code_at(secret: str, step: int) -> str:
    return pyotp.TOTP(secret, digits=DIGITS, interval=STEP_SECONDS).at(step * STEP_SECONDS)


_RC_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O/1/I


def new_recovery_code() -> str:
    raw = "".join(secrets.choice(_RC_ALPHABET) for _ in range(10))  # ~50 bits
    return f"{raw[:5]}-{raw[5:]}"


def normalize_recovery_code(code: str) -> str:
    return "".join(ch for ch in (code or "").upper() if ch.isalnum())
