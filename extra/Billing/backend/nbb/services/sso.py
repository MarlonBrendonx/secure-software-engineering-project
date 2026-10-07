"""Decide quem pode entrar por SSO e com qual usuário.

Ordem de resolução de uma identidade (provedor, sub):
1. Já vinculada -> o usuário dono do vínculo.
2. E-mail verificado igual ao de um usuário SSO pré-cadastrado pelo
   administrador (e o provedor permite `link_by_email`) -> vincula.
3. Domínio do e-mail na lista do provedor e `auto_provision` ligado ->
   cria usuário sem perfil (só pode solicitar acesso).
4. Caso contrário -> recusado.

Nunca se vincula por e-mail não verificado: isso permitiria que alguém
criasse uma conta num provedor com o e-mail de outra pessoa e assumisse
o usuário dela.
"""
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nbb.config import OidcProviderConfig
from nbb.core import audit
from nbb.core.oidc import OidcIdentity
from nbb.models import User, UserIdentity, UserSource


class SsoRejected(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _domain(email: str | None) -> str | None:
    return email.rsplit("@", 1)[1].lower() if email and "@" in email else None


def _email_trusted(ident: OidcIdentity, cfg: OidcProviderConfig) -> bool:
    return bool(ident.email) and (ident.email_verified or not cfg.require_email_verified)


def resolve_user(db: Session, ident: OidcIdentity, cfg: OidcProviderConfig) -> User:
    now = datetime.now(UTC)
    link = db.scalar(select(UserIdentity).where(
        UserIdentity.provider == ident.provider, UserIdentity.subject == ident.subject))
    if link is not None:
        link.last_login_at = now
        if ident.email and link.email != ident.email:
            link.email = ident.email
        user = db.get(User, link.user_id)
        assert user is not None
        return user

    trusted = _email_trusted(ident, cfg)
    domain = _domain(ident.email)
    domain_ok = not cfg.allowed_domains or (domain in cfg.allowed_domains)
    if not trusted:
        raise SsoRejected("email_not_verified",
                          "O provedor não confirmou o seu e-mail. Use uma conta com e-mail verificado.")
    if not domain_ok:
        raise SsoRejected("domain_not_allowed",
                          f"Contas do domínio {domain} não têm acesso por este provedor.")

    user = None
    if cfg.link_by_email:
        user = db.scalar(select(User).where(
            func.lower(User.email) == ident.email, User.source == UserSource.SSO))
        if user is not None and db.scalar(select(UserIdentity.id).where(
                UserIdentity.user_id == user.id, UserIdentity.provider == ident.provider)):
            # Já existe outra conta deste provedor vinculada a esse usuário.
            raise SsoRejected("identity_conflict",
                              "Seu usuário já está vinculado a outra conta deste provedor. Procure o administrador.")

    if user is None and db.scalar(select(User.id).where(func.lower(User.email) == ident.email)):
        # O e-mail pertence a uma conta local (ou a um SSO sem link_by_email): não cria duplicata.
        raise SsoRejected("identity_conflict",
                          "Já existe um usuário com este e-mail que não entra por este provedor. "
                          "Procure o administrador.")

    if user is None:
        if not (cfg.auto_provision and cfg.allowed_domains):
            raise SsoRejected("not_registered",
                              "Usuário não cadastrado. Peça ao administrador para liberar o seu e-mail.")
        assert ident.email is not None
        if db.scalar(select(User.id).where(func.lower(User.login) == ident.email)):
            raise SsoRejected("identity_conflict",
                              "Já existe um usuário com este login. Procure o administrador.")
        user = User(login=ident.email, name=ident.name, email=ident.email, source=UserSource.SSO)
        db.add(user)
        db.flush()

    db.add(UserIdentity(user_id=user.id, provider=ident.provider, subject=ident.subject,
                        email=ident.email, last_login_at=now))
    audit.record(db, "auth.sso_identity_linked", entity="app_user", entity_id=user.id,
                 detail={"provider": ident.provider, "email": ident.email})
    return user
