"""Comandos operacionais.

  nbb bootstrap-admin LOGIN NOME EMAIL  cria o primeiro administrador (entra por SSO)
  nbb create-local-user LOGIN NOME EMAIL --roles admin   cria conta com usuário e senha
  nbb generate-key                 gera um segredo novo para NBB_JWT_KEYS
  nbb generate-data-key            gera uma chave nova para NBB_DATA_ENCRYPTION_KEYS
  nbb revoke-all-sessions          encerra todas as sessões (rotação de emergência)
  nbb reencrypt                    recifra os segredos do 2FA com a chave mais nova
"""
import argparse
import secrets
import sys

from sqlalchemy import func, select

from nbb.core import audit
from nbb.core.audit import Actor, set_actor
from nbb.core.crypto import generate_key
from nbb.db import new_session
from nbb.models import User, UserRole, UserSource
from nbb.services import sessions

CLI_ACTOR = Actor(user_id=None, login="cli")


def bootstrap_admin(login: str, name: str, email: str) -> int:
    db = new_session()
    set_actor(db, CLI_ACTOR)
    if db.scalar(select(func.count()).select_from(UserRole).where(UserRole.role_code == "admin")):
        print("Já existe administrador; use a tela de usuários.", file=sys.stderr)
        return 1
    user = db.scalar(select(User).where(func.lower(User.login) == login.lower()))
    if user is None:
        user = User(login=login, name=name, email=email.lower(), source=UserSource.SSO)
        db.add(user)
        db.flush()
    db.add(UserRole(user_id=user.id, role_code="admin"))
    audit.record(db, "cli.bootstrap_admin", entity="app_user", entity_id=user.id)
    db.commit()
    print(f"Administrador {login} criado. Entre por SSO com {email} e cadastre o autenticador "
          "em 'Segurança da conta' para liberar as permissões de administrador.")
    return 0


def create_local_user(login: str, name: str, email: str, roles: list[str], password: str | None) -> int:
    """Cria conta com usuário e senha (útil para testar sem SSO e para contas externas)."""
    import getpass

    from nbb.config import get_settings
    from nbb.core.security import hash_password, validate_password_policy
    from nbb.models import Role

    db = new_session()
    set_actor(db, CLI_ACTOR)
    if db.scalar(select(User.id).where(func.lower(User.login) == login.lower())):
        print(f"Já existe usuário com o login {login}.", file=sys.stderr)
        return 1
    known = set(db.scalars(select(Role.code)))
    invalid = [r for r in roles if r not in known or r == "none"]
    if invalid:
        print(f"Perfis inválidos: {', '.join(invalid)}. Use: analyst, manager, admin, auditor.", file=sys.stderr)
        return 1
    if password is None:
        password = getpass.getpass("Senha: ")
        if getpass.getpass("Repita a senha: ") != password:
            print("As senhas não conferem.", file=sys.stderr)
            return 1
    try:
        validate_password_policy(password, get_settings().password_min_length)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    user = User(login=login, name=name, email=email.lower(), source=UserSource.LOCAL,
                password_hash=hash_password(password))
    db.add(user)
    db.flush()
    for r in roles:
        db.add(UserRole(user_id=user.id, role_code=r))
    audit.record(db, "cli.create_local_user", entity="app_user", entity_id=user.id, detail={"roles": roles})
    db.commit()
    mfa_roles = [r for r in roles if r in ("manager", "admin")]
    print(f"Usuário {login} criado. Entre em \"Entrar com usuário e senha\".")
    if mfa_roles:
        print("O perfil exige verificação em duas etapas: no primeiro acesso, ative o autenticador em "
              "'Segurança da conta' para liberar as permissões.")
    return 0


def reencrypt() -> int:
    """Recifra os segredos TOTP com a primeira chave de NBB_DATA_ENCRYPTION_KEYS."""
    from nbb.config import get_settings
    from nbb.core.crypto import DataCipher
    from nbb.models import UserMfa

    cipher = DataCipher(get_settings().data_encryption_keys)
    db = new_session()
    set_actor(db, CLI_ACTOR)
    n = 0
    for row in db.scalars(select(UserMfa).with_for_update()):
        row.totp_secret_enc = cipher.rotate(row.totp_secret_enc)
        n += 1
    audit.record(db, "cli.reencrypt_mfa_secrets", detail={"rows": n})
    db.commit()
    print(f"{n} segredos recifrados. Já é seguro remover as chaves antigas.")
    return 0


def revoke_all_sessions() -> int:
    db = new_session()
    set_actor(db, CLI_ACTOR)
    n = sessions.revoke_all(db, "key_rotation_emergency")
    audit.record(db, "cli.revoke_all_sessions", detail={"sessions_closed": n})
    db.commit()
    print(f"{n} sessões encerradas.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nbb")
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bootstrap-admin")
    b.add_argument("login")
    b.add_argument("name")
    b.add_argument("email", help="e-mail da conta Google/Microsoft/corporativa usada no SSO")
    lu = sub.add_parser("create-local-user", help="cria conta com usuário e senha")
    lu.add_argument("login")
    lu.add_argument("name")
    lu.add_argument("email")
    lu.add_argument("--roles", default="", help="perfis separados por vírgula: analyst,manager,admin,auditor")
    lu.add_argument("--password-stdin", action="store_true", help="lê a senha da entrada padrão")
    sub.add_parser("generate-key")
    sub.add_parser("generate-data-key")
    sub.add_parser("revoke-all-sessions")
    sub.add_parser("reencrypt")
    args = parser.parse_args(argv)
    if args.cmd == "bootstrap-admin":
        return bootstrap_admin(args.login, args.name, args.email)
    if args.cmd == "create-local-user":
        pwd = sys.stdin.readline().rstrip("\n") if args.password_stdin else None
        roles = [r.strip() for r in args.roles.split(",") if r.strip()]
        return create_local_user(args.login, args.name, args.email, roles, pwd)
    if args.cmd == "generate-key":
        print(secrets.token_urlsafe(48))
        return 0
    if args.cmd == "generate-data-key":
        print(generate_key())
        return 0
    if args.cmd == "reencrypt":
        return reencrypt()
    return revoke_all_sessions()


if __name__ == "__main__":
    sys.exit(main())
