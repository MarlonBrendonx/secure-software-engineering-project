"""Fundação: identidade, perfis, delegações, sessões, auditoria e configurações.

Revision ID: 0001_foundation
"""
import json
import os

from alembic import op

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None

APP_ROLE = os.environ.get("NBB_DATABASE_APP_ROLE", "nbb_app")

PERMISSIONS = {
    "access.request": "Solicitar acesso",
    "entries.read": "Consultar lançamentos e dados",
    "entries.write": "Criar e corrigir lançamentos",
    "entries.approve": "Aprovar ou devolver lançamentos",
    "reports.generate": "Gerar relatórios",
    "erp.generate": "Gerar carga para o ERP",
    "erp.download": "Baixar carga do ERP",
    "periods.close": "Fechar período",
    "periods.reopen.request": "Solicitar reabertura de período",
    "periods.reopen.approve": "Aprovar reabertura de período",
    "contracts.read": "Consultar contratos",
    "contracts.manage": "Alterar regras contratuais",
    "users.manage": "Gerir usuários e perfis",
    "delegations.manage": "Conceder substituições temporárias",
    "settings.manage": "Alterar parâmetros do sistema",
    "audit.read": "Consultar trilha de auditoria",
}

ROLES = {
    # code: (nome, exige MFA, permissões)
    "none": ("Sem perfil", False, ["access.request"]),
    "analyst": ("Analista", False, [
        "access.request", "entries.read", "entries.write", "reports.generate",
        "contracts.read", "periods.reopen.request",
    ]),
    "manager": ("Gerente / Coordenador", True, [
        "access.request", "entries.read", "entries.approve", "reports.generate",
        "erp.generate", "erp.download", "periods.close", "periods.reopen.request",
        "periods.reopen.approve", "contracts.read", "audit.read",
    ]),
    "admin": ("Administrador", True, [
        "access.request", "users.manage", "delegations.manage", "contracts.read",
        "contracts.manage", "settings.manage",
    ]),
    # Controladoria e auditoria externa: só leitura.
    "auditor": ("Auditoria / Controladoria", False, [
        "access.request", "entries.read", "contracts.read", "audit.read", "reports.generate",
    ]),
}

SETTINGS = {
    "approval.double_threshold": ("50000.00", "Valor (R$) acima do qual um lançamento exige duas aprovações"),
    "approval.deviation_pct": (30, "Desvio (%) em relação à média do cliente que dispara alerta ao aprovador"),
    "approval.deviation_window_months": (6, "Meses usados no cálculo da média do cliente"),
    "delegation.max_days": (60, "Duração máxima de uma substituição temporária, em dias"),
    "privacy.store_cpf": (False, "Guardar CPF dos responsáveis (depende de confirmação do jurídico)"),
}

# Tabelas cujo conteúdo nunca muda depois de gravado.
IMMUTABLE_TABLES = ["audit_event"]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE app_user (
            id uuid PRIMARY KEY,
            login varchar(120) NOT NULL,
            name varchar(200) NOT NULL,
            email varchar(254),
            source varchar(20) NOT NULL CHECK (source IN ('corporate','local')),
            password_hash text,
            status varchar(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','terminated')),
            token_version integer NOT NULL DEFAULT 1,
            created_at timestamptz NOT NULL DEFAULT now(),
            terminated_at timestamptz,
            terminated_by uuid REFERENCES app_user(id),
            CONSTRAINT local_has_no_corporate_pwd CHECK (source = 'local' OR password_hash IS NULL)
        );
        CREATE UNIQUE INDEX app_user_login_uq ON app_user (lower(login));

        CREATE TABLE permission (
            code varchar(60) PRIMARY KEY,
            description varchar(200) NOT NULL
        );

        CREATE TABLE role (
            code varchar(40) PRIMARY KEY,
            name varchar(100) NOT NULL,
            requires_mfa boolean NOT NULL DEFAULT false
        );

        CREATE TABLE role_permission (
            role_code varchar(40) REFERENCES role(code),
            permission_code varchar(60) REFERENCES permission(code),
            PRIMARY KEY (role_code, permission_code)
        );

        CREATE TABLE user_role (
            user_id uuid REFERENCES app_user(id),
            role_code varchar(40) REFERENCES role(code),
            granted_by uuid REFERENCES app_user(id),
            granted_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, role_code)
        );

        CREATE TABLE delegation (
            id uuid PRIMARY KEY,
            titular_id uuid NOT NULL REFERENCES app_user(id),
            substitute_id uuid NOT NULL REFERENCES app_user(id),
            role_code varchar(40) NOT NULL REFERENCES role(code),
            starts_at timestamptz NOT NULL,
            ends_at timestamptz NOT NULL,
            justification text NOT NULL,
            document_ref varchar(200),
            granted_by uuid NOT NULL REFERENCES app_user(id),
            created_at timestamptz NOT NULL DEFAULT now(),
            revoked_at timestamptz,
            revoked_by uuid REFERENCES app_user(id),
            CHECK (ends_at > starts_at),
            CHECK (titular_id <> substitute_id),
            CHECK (granted_by <> substitute_id)
        );
        CREATE INDEX delegation_substitute_idx ON delegation (substitute_id) WHERE revoked_at IS NULL;

        CREATE TABLE access_request (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES app_user(id),
            role_code varchar(40) NOT NULL REFERENCES role(code),
            justification text NOT NULL,
            status varchar(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
            created_at timestamptz NOT NULL DEFAULT now(),
            decided_by uuid REFERENCES app_user(id),
            decided_at timestamptz,
            decision_comment text,
            CHECK (decided_by IS NULL OR decided_by <> user_id)
        );

        CREATE TABLE auth_session (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES app_user(id),
            auth_method varchar(20) NOT NULL,
            mfa boolean NOT NULL DEFAULT false,
            refresh_hash varchar(64) NOT NULL,
            prev_refresh_hash varchar(64),
            created_at timestamptz NOT NULL DEFAULT now(),
            last_used_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL,
            revoked_at timestamptz,
            revoke_reason varchar(60),
            ip varchar(64),
            user_agent varchar(300)
        );
        CREATE INDEX auth_session_user_idx ON auth_session (user_id) WHERE revoked_at IS NULL;

        CREATE TABLE password_reset (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES app_user(id),
            token_hash varchar(64) NOT NULL UNIQUE,
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL,
            used_at timestamptz
        );

        CREATE TABLE setting (
            key varchar(80) PRIMARY KEY,
            value jsonb NOT NULL,
            description text NOT NULL,
            updated_at timestamptz NOT NULL DEFAULT now(),
            updated_by uuid REFERENCES app_user(id)
        );
        """
    )

    # ------------------------------------------------------------------
    # Trilha de auditoria: append-only e encadeada por hash.
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE audit_event (
            id uuid PRIMARY KEY,
            seq bigint NOT NULL UNIQUE,
            occurred_at timestamptz NOT NULL,
            actor_id uuid,
            actor_login varchar(120),
            via_delegation_id uuid,
            action varchar(80) NOT NULL,
            entity varchar(80),
            entity_id varchar(200),
            before jsonb,
            after jsonb,
            ip varchar(64),
            request_id varchar(64),
            prev_hash varchar(64) NOT NULL,
            hash text NOT NULL
        );
        CREATE INDEX audit_event_entity_idx ON audit_event (entity, entity_id);
        CREATE INDEX audit_event_actor_idx ON audit_event (actor_id, occurred_at);
        CREATE INDEX audit_event_time_idx ON audit_event (occurred_at);

        -- Serialização canônica e sem ambiguidade (array JSON) de um evento.
        CREATE FUNCTION audit_event_digest(e audit_event) RETURNS text
        LANGUAGE sql STABLE AS $$
          SELECT encode(sha256(convert_to(jsonb_build_array(
              e.seq,
              to_char(e.occurred_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'),
              e.actor_id, e.actor_login, e.via_delegation_id, e.action, e.entity, e.entity_id,
              e.before, e.after, e.ip, e.request_id, e.prev_hash
          )::text, 'UTF8')), 'hex')
        $$;

        CREATE FUNCTION audit_event_chain() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
          last_seq bigint;
          last_hash text;
        BEGIN
          -- Serializa os inserts para manter a cadeia linear.
          PERFORM pg_advisory_xact_lock(746100001);
          SELECT seq, hash INTO last_seq, last_hash FROM audit_event ORDER BY seq DESC LIMIT 1;
          NEW.seq := COALESCE(last_seq, 0) + 1;
          NEW.prev_hash := COALESCE(last_hash, repeat('0', 64));
          NEW.occurred_at := date_trunc('microseconds', clock_timestamp());
          NEW.hash := audit_event_digest(NEW);
          RETURN NEW;
        END $$;

        CREATE TRIGGER audit_event_chain BEFORE INSERT ON audit_event
          FOR EACH ROW EXECUTE FUNCTION audit_event_chain();

        -- Verifica a cadeia inteira (ou a partir de from_seq). Devolve a
        -- primeira quebra encontrada ou nenhuma linha se estiver íntegra.
        CREATE FUNCTION audit_verify_chain(from_seq bigint DEFAULT 1)
        RETURNS TABLE (broken_seq bigint, reason text)
        LANGUAGE plpgsql STABLE AS $$
        DECLARE
          r audit_event;
          expected_seq bigint := from_seq;
          expected_prev text;
        BEGIN
          IF from_seq <= 1 THEN
            expected_prev := repeat('0', 64);
          ELSE
            SELECT hash INTO expected_prev FROM audit_event WHERE seq = from_seq - 1;
            IF expected_prev IS NULL THEN
              broken_seq := from_seq - 1; reason := 'missing'; RETURN NEXT; RETURN;
            END IF;
          END IF;
          FOR r IN SELECT * FROM audit_event WHERE seq >= from_seq ORDER BY seq LOOP
            IF r.seq <> expected_seq THEN
              broken_seq := expected_seq; reason := 'missing'; RETURN NEXT; RETURN;
            END IF;
            IF r.prev_hash <> expected_prev THEN
              broken_seq := r.seq; reason := 'prev_hash_mismatch'; RETURN NEXT; RETURN;
            END IF;
            IF r.hash <> audit_event_digest(r) THEN
              broken_seq := r.seq; reason := 'content_altered'; RETURN NEXT; RETURN;
            END IF;
            expected_prev := r.hash;
            expected_seq := expected_seq + 1;
          END LOOP;
        END $$;

        -- Bloqueio genérico de alteração, reutilizado pelas tabelas imutáveis
        -- dos próximos módulos (lançamentos aprovados, fechamento, cargas ERP).
        CREATE FUNCTION forbid_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'tabela % é somente-acréscimo: % não permitido', TG_TABLE_NAME, TG_OP
            USING ERRCODE = 'NB001';
        END $$;
        """
    )
    for table in IMMUTABLE_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_no_update_delete BEFORE UPDATE OR DELETE ON {table}
              FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
            CREATE TRIGGER {table}_no_truncate BEFORE TRUNCATE ON {table}
              FOR EACH STATEMENT EXECUTE FUNCTION forbid_mutation();
            """
        )

    # ------------------------------------------------------------------
    # Dados iniciais
    # ------------------------------------------------------------------
    for code, desc in PERMISSIONS.items():
        op.execute(f"INSERT INTO permission (code, description) VALUES ('{code}', '{desc}')")
    for code, (name, mfa, perms) in ROLES.items():
        op.execute(f"INSERT INTO role (code, name, requires_mfa) VALUES ('{code}', '{name}', {str(mfa).lower()})")
        for p in perms:
            op.execute(f"INSERT INTO role_permission VALUES ('{code}', '{p}')")
    for key, (value, desc) in SETTINGS.items():
        op.execute(
            "INSERT INTO setting (key, value, description) VALUES "
            f"('{key}', '{json.dumps(value)}'::jsonb, '{desc}')"
        )

    # ------------------------------------------------------------------
    # Permissões do usuário de conexão da aplicação
    # ------------------------------------------------------------------
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE ON app_user, user_role, delegation, access_request, "
        f"auth_session, password_reset, setting TO {APP_ROLE}"
    )
    # Remoção de perfil de um usuário é DELETE em user_role.
    op.execute(f"GRANT DELETE ON user_role TO {APP_ROLE}")
    op.execute(f"GRANT SELECT ON permission, role, role_permission TO {APP_ROLE}")
    # Auditoria: só leitura e acréscimo.
    op.execute(f"GRANT SELECT, INSERT ON audit_event TO {APP_ROLE}")
    op.execute(f"GRANT EXECUTE ON FUNCTION audit_verify_chain(bigint) TO {APP_ROLE}")


def downgrade() -> None:
    raise RuntimeError("Migration de fundação não tem downgrade: a trilha de auditoria não pode ser apagada.")
