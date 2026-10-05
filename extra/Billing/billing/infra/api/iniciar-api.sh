#!/bin/sh
# Inicia a API. Não publique a porta 8000: o acesso deve passar pelo contêiner web (HTTPS).
set -e

# Chaves: as informadas por variável de ambiente têm prioridade; senão são geradas uma
# única vez e guardadas no volume (perder a chave de cifragem obriga a recadastrar o 2FA).
if [ ! -f /dados/segredos.env ]; then
    echo "[api] Gerando chaves em /dados/segredos.env"
    gerar() { python3 -c "import secrets;print(secrets.token_urlsafe(48))"; }
    umask 077
    {
        echo "GERADO_JWT=$(gerar)"
        echo "GERADO_MFA=$(gerar)"
        echo "GERADO_OPS=$(gerar)"
    } > /dados/segredos.env
fi
. /dados/segredos.env
export BILLING_JWT_CHAVE_ATUAL="${BILLING_JWT_CHAVE_ATUAL:-$GERADO_JWT}"
export BILLING_MFA_CHAVE_CIFRAGEM="${BILLING_MFA_CHAVE_CIFRAGEM:-$GERADO_MFA}"
export BILLING_OPS_TOKEN="${BILLING_OPS_TOKEN:-$GERADO_OPS}"

# Modo demonstração: login simulado (sem LDAP). NUNCA usar em produção.
if [ "${BILLING_DEMO:-0}" = "1" ]; then
    echo "[api] *** MODO DEMONSTRAÇÃO: login simulado, senha de todos os usuários = demo123 ***"
    export BILLING_AMBIENTE=demonstracao BILLING_IDP_TIPO=fake
    export BILLING_FAKE_USUARIOS='{"admin":"demo123","operacional":"demo123","gestor":"demo123","auditor":"demo123"}'
fi

python3 -m app.cli iniciar-banco
if [ "${BILLING_DEMO:-0}" = "1" ]; then
    python3 -m app.cli criar-usuario admin "Administrador Demo" ADMINISTRADOR 2>/dev/null || true
    python3 -m app.cli criar-usuario operacional "Operacional Demo" OPERACIONAL 2>/dev/null || true
    python3 -m app.cli criar-usuario gestor "Gestor Demo" GESTOR 2>/dev/null || true
    python3 -m app.cli criar-usuario auditor "Auditor Demo" AUDITOR 2>/dev/null || true
fi

# Com SQLite/limite em memória, uma única instância (workers=1). Com PostgreSQL+Redis, pode aumentar.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${BILLING_WORKERS:-1}" \
    --proxy-headers --forwarded-allow-ips "${BILLING_PROXY_CONFIAVEL:-*}"
