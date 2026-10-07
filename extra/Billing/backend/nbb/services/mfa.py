"""Ciclo de vida do 2FA por aplicativo autenticador (TOTP)."""
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from nbb.core import audit, totp
from nbb.core.crypto import DataCipher
from nbb.core.security import sha256_hex
from nbb.models import MfaRecoveryCode, User, UserMfa


class MfaError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Enrollment:
    secret: str
    otpauth_uri: str
    qr_svg: str


def get_confirmed(db: Session, user_id: uuid.UUID) -> UserMfa | None:
    row = db.get(UserMfa, user_id)
    return row if row is not None and row.confirmed_at is not None else None


def is_enrolled(db: Session, user_id: uuid.UUID) -> bool:
    return get_confirmed(db, user_id) is not None


def start_enrollment(db: Session, cipher: DataCipher, user: User, issuer: str) -> Enrollment:
    row = db.get(UserMfa, user.id)
    if row is not None and row.confirmed_at is not None:
        raise MfaError("already_enrolled", "O 2FA já está ativo. Desative-o antes de cadastrar outro aparelho.")
    secret = totp.new_secret()
    if row is None:
        row = UserMfa(user_id=user.id, totp_secret_enc=cipher.encrypt(secret))
        db.add(row)
    else:  # recomeçou o cadastro: troca o segredo pendente
        row.totp_secret_enc = cipher.encrypt(secret)
        row.created_at = datetime.now(UTC)
    uri = totp.provisioning_uri(secret, user.email or user.login, issuer)
    return Enrollment(secret=secret, otpauth_uri=uri, qr_svg=totp.qr_svg_data_uri(uri))


def _check_totp(row: UserMfa, cipher: DataCipher, code: str) -> bool:
    step = totp.match_step(cipher.decrypt(row.totp_secret_enc), code)
    if step is None or step <= row.last_used_step:
        # Código errado, ou o mesmo código já usado (replay).
        return False
    row.last_used_step = step
    return True


def confirm_enrollment(db: Session, cipher: DataCipher, user: User, code: str, n_codes: int) -> list[str]:
    row = db.scalar(select(UserMfa).where(UserMfa.user_id == user.id).with_for_update())
    if row is None or row.confirmed_at is not None:
        raise MfaError("no_pending_enrollment", "Não há cadastro de 2FA pendente.")
    if not _check_totp(row, cipher, code):
        raise MfaError("invalid_code", "Código inválido. Confira o horário do celular e tente de novo.")
    row.confirmed_at = datetime.now(UTC)
    audit.record(db, "mfa.enrolled", entity="app_user", entity_id=user.id)
    return regenerate_recovery_codes(db, user, n_codes, audit_event=False)


def regenerate_recovery_codes(db: Session, user: User, n: int, *, audit_event: bool = True) -> list[str]:
    db.execute(delete(MfaRecoveryCode).where(MfaRecoveryCode.user_id == user.id))
    codes = [totp.new_recovery_code() for _ in range(n)]
    for c in codes:
        db.add(MfaRecoveryCode(user_id=user.id, code_hash=sha256_hex(totp.normalize_recovery_code(c))))
    if audit_event:
        audit.record(db, "mfa.recovery_codes_regenerated", entity="app_user", entity_id=user.id)
    return codes


def verify(db: Session, cipher: DataCipher, user: User, code: str) -> str | None:
    """Confere um código TOTP ou de recuperação. Devolve o método usado ou None."""
    row = db.scalar(select(UserMfa).where(UserMfa.user_id == user.id).with_for_update())
    if row is None or row.confirmed_at is None:
        return None
    if code and code.strip().replace(" ", "").isdigit():
        return "totp" if _check_totp(row, cipher, code) else None
    rc = db.scalar(select(MfaRecoveryCode).where(
        MfaRecoveryCode.user_id == user.id,
        MfaRecoveryCode.code_hash == sha256_hex(totp.normalize_recovery_code(code)),
        MfaRecoveryCode.used_at.is_(None),
    ).with_for_update())
    if rc is None:
        return None
    rc.used_at = datetime.now(UTC)
    remaining = db.scalar(select(MfaRecoveryCode.id).where(
        MfaRecoveryCode.user_id == user.id, MfaRecoveryCode.used_at.is_(None), MfaRecoveryCode.id != rc.id))
    audit.record(db, "mfa.recovery_code_used", entity="app_user", entity_id=user.id,
                 detail={"codes_left": remaining is not None})
    return "recovery"


def remaining_recovery_codes(db: Session, user_id: uuid.UUID) -> int:
    return len(db.scalars(select(MfaRecoveryCode.id).where(
        MfaRecoveryCode.user_id == user_id, MfaRecoveryCode.used_at.is_(None))).all())


def remove(db: Session, user_id: uuid.UUID) -> None:
    db.execute(delete(MfaRecoveryCode).where(MfaRecoveryCode.user_id == user_id))
    row = db.get(UserMfa, user_id)
    if row is not None:
        db.delete(row)
