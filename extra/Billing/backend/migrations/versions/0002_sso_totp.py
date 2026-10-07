"""SSO com vários provedores e 2FA por TOTP.

- user_identity: vínculo (provedor, sub) -> usuário. Um usuário pode entrar
  por mais de um provedor; uma identidade só pertence a um usuário.
- user_mfa: segredo TOTP cifrado + último passo usado (anti-replay).
- mfa_recovery_code: códigos de uso único, guardados só como hash.
- auth_session ganha a etapa 'pending_mfa' (senha/SSO ok, falta o código).

Revision ID: 0002_sso_totp
"""
import os

from alembic import op

revision = "0002_sso_totp"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None

APP_ROLE = os.environ.get("NBB_DATABASE_APP_ROLE", "nbb_app")


def upgrade() -> None:
    op.execute(
        """
        -- 'corporate' passa a ser 'sso' (qualquer provedor OIDC).
        ALTER TABLE app_user DROP CONSTRAINT app_user_source_check;
        UPDATE app_user SET source = 'sso' WHERE source = 'corporate';
        ALTER TABLE app_user ADD CONSTRAINT app_user_source_check CHECK (source IN ('sso','local'));
        ALTER TABLE app_user DROP CONSTRAINT local_has_no_corporate_pwd;
        ALTER TABLE app_user ADD CONSTRAINT only_local_has_password CHECK (source = 'local' OR password_hash IS NULL);
        CREATE INDEX app_user_email_idx ON app_user (lower(email));

        CREATE TABLE user_identity (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES app_user(id),
            provider varchar(40) NOT NULL,
            subject varchar(255) NOT NULL,
            email varchar(254),
            created_at timestamptz NOT NULL DEFAULT now(),
            last_login_at timestamptz,
            UNIQUE (provider, subject)
        );
        CREATE INDEX user_identity_user_idx ON user_identity (user_id);

        CREATE TABLE user_mfa (
            user_id uuid PRIMARY KEY REFERENCES app_user(id),
            totp_secret_enc text NOT NULL,
            confirmed_at timestamptz,
            last_used_step bigint NOT NULL DEFAULT 0,
            created_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE mfa_recovery_code (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES app_user(id),
            code_hash varchar(64) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            used_at timestamptz,
            UNIQUE (user_id, code_hash)
        );

        ALTER TABLE auth_session
          ADD COLUMN stage varchar(20) NOT NULL DEFAULT 'active' CHECK (stage IN ('pending_mfa','active')),
          ADD COLUMN mfa_ticket_hash varchar(64) UNIQUE,
          ADD COLUMN mfa_attempts integer NOT NULL DEFAULT 0,
          ADD COLUMN mfa_method varchar(20),
          ADD COLUMN provider varchar(40);

        INSERT INTO setting (key, value, description) VALUES
          ('mfa.required_for_all', 'false'::jsonb,
           'Exige 2FA de todos os usuários (por padrão, só dos perfis marcados, como Gerente e Admin)');
        """
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON user_identity, mfa_recovery_code TO {APP_ROLE}")
    # DELETE em user_mfa e nos códigos: desativar/resetar o 2FA (sempre auditado).
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON user_mfa TO {APP_ROLE}")
    op.execute(f"GRANT DELETE ON mfa_recovery_code TO {APP_ROLE}")


def downgrade() -> None:
    raise RuntimeError("Sem downgrade: as tabelas de identidade são referenciadas pela auditoria.")
