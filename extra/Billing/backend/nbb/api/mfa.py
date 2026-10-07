"""Tela "Segurança da conta": ativar, gerenciar e desativar o autenticador."""
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from nbb.api.auth import CodeIn, MeOut, _current_for, me_out, set_session_cookies
from nbb.api.deps import Container, Current, error, get_container, get_current
from nbb.core import audit
from nbb.db import get_db
from nbb.models import AuthSession
from nbb.services import mfa as mfa_svc
from nbb.services import sessions

router = APIRouter(prefix="/auth/mfa", tags=["2fa"])


class MfaStatusOut(BaseModel):
    enrolled: bool
    required: bool = Field(description="Algum perfil do usuário exige 2FA")
    session_verified: bool
    recovery_codes_left: int


class SetupOut(BaseModel):
    secret: str = Field(description="Para digitar no app caso a câmera não leia o QR code")
    otpauth_uri: str
    qr_svg: str = Field(description="QR code como data URI SVG; use direto em <img src>")


class ConfirmOut(BaseModel):
    recovery_codes: list[str] = Field(description="Mostre uma única vez e peça para o usuário guardar")
    me: MeOut


class RecoveryCodesOut(BaseModel):
    recovery_codes: list[str]


def _guard(c: Container, current: Current) -> str:
    key = f"mfa:{current.user.id}"
    blocked, retry = c.mfa_limiter.blocked(key)
    if blocked:
        raise error(429, "mfa_locked", "Muitos códigos errados. Aguarde alguns minutos.", retry_after=retry)
    return key


def _invalid(c: Container, db: Session, key: str, current: Current, action: str):
    c.mfa_limiter.hit(key)
    audit.record(db, "mfa.code_rejected", entity="app_user", entity_id=current.user.id, detail={"action": action})
    db.commit()
    return error(422, "invalid_code", "Código inválido. Confira o horário do celular e tente de novo.")


@router.get("", response_model=MfaStatusOut, summary="Situação do 2FA do usuário logado")
def status(current: Current = Depends(get_current), db: Session = Depends(get_db)):
    return MfaStatusOut(
        enrolled=mfa_svc.is_enrolled(db, current.user.id),
        required=current.access.mfa_required,
        session_verified=current.session.mfa,
        recovery_codes_left=mfa_svc.remaining_recovery_codes(db, current.user.id),
    )


@router.post("/totp/setup", response_model=SetupOut,
             summary="Passo 1: gera o QR code para o app autenticador",
             description="Funciona com Google Authenticator, Microsoft Authenticator, Authy, 1Password etc. "
                         "O 2FA só passa a valer depois de `POST /auth/mfa/totp/confirm`.")
def setup(current: Current = Depends(get_current), db: Session = Depends(get_db),
          c: Container = Depends(get_container)):
    try:
        enr = mfa_svc.start_enrollment(db, c.cipher, current.user, c.settings.totp_issuer)
    except mfa_svc.MfaError as exc:
        raise error(409, exc.code, exc.message) from None
    db.commit()
    return SetupOut(secret=enr.secret, otpauth_uri=enr.otpauth_uri, qr_svg=enr.qr_svg)


@router.post("/totp/confirm", response_model=ConfirmOut,
             summary="Passo 2: confirma com o primeiro código e ativa o 2FA",
             description="Encerra as outras sessões do usuário e troca a sessão atual por uma nova, já verificada.")
def confirm(body: CodeIn, request: Request, response: Response, current: Current = Depends(get_current),
            db: Session = Depends(get_db), c: Container = Depends(get_container)):
    key = _guard(c, current)
    try:
        codes = mfa_svc.confirm_enrollment(db, c.cipher, current.user, body.code, c.settings.recovery_codes_count)
    except mfa_svc.MfaError as exc:
        if exc.code == "invalid_code":
            raise _invalid(c, db, key, current, "confirm") from None
        raise error(409, exc.code, exc.message) from None
    # Mudou o nível de segurança: sessão nova (evita fixação) e as demais caem.
    sessions.revoke_all_for_user(db, current.user.id, "mfa_enrolled")
    old: AuthSession = current.session
    new, refresh = sessions.create_session(
        db, c.settings, current.user, method=old.auth_method, provider=old.provider, mfa=True,
        mfa_method="totp", ip=db.info["actor"].ip, user_agent=request.headers.get("user-agent"))
    db.commit()
    set_session_cookies(response, c, current.user, new, refresh)
    return ConfirmOut(recovery_codes=codes, me=me_out(db, _current_for(db, current.user, new)))


@router.post("/recovery-codes", response_model=RecoveryCodesOut,
             summary="Gera novos códigos de recuperação (os antigos deixam de valer)")
def regenerate(body: CodeIn, current: Current = Depends(get_current), db: Session = Depends(get_db),
               c: Container = Depends(get_container)):
    key = _guard(c, current)
    if mfa_svc.verify(db, c.cipher, current.user, body.code) != "totp":
        raise _invalid(c, db, key, current, "regenerate_codes")
    codes = mfa_svc.regenerate_recovery_codes(db, current.user, c.settings.recovery_codes_count)
    db.commit()
    return RecoveryCodesOut(recovery_codes=codes)


@router.post("/disable", status_code=204, summary="Desativa o 2FA (não permitido se o perfil exige)")
def disable(body: CodeIn, current: Current = Depends(get_current), db: Session = Depends(get_db),
            c: Container = Depends(get_container)):
    if current.access.mfa_required:
        raise error(409, "mfa_mandatory", "Seu perfil exige verificação em duas etapas; ela não pode ser desativada.")
    key = _guard(c, current)
    if mfa_svc.verify(db, c.cipher, current.user, body.code) is None:
        raise _invalid(c, db, key, current, "disable")
    mfa_svc.remove(db, current.user.id)
    audit.record(db, "mfa.disabled", entity="app_user", entity_id=current.user.id)
    sessions.revoke_all_for_user(db, current.user.id, "mfa_disabled", except_id=current.session.id)
    current.session.mfa = False
    current.session.mfa_method = None
    db.commit()
