#!/bin/sh
# Sobe a API e o Nginx no mesmo contêiner. Se um dos dois parar, o contêiner para
# (e o Docker o reinicia, se configurado com --restart).
set -e

mkdir -p /dados/certs

# 1. Certificado: usa o da empresa se montado em /dados/certs; senão gera um autoassinado.
if [ ! -f /dados/certs/billing.crt ] || [ ! -f /dados/certs/billing.key ]; then
    echo "[iniciar] Gerando certificado autoassinado (troque pelo da empresa em /dados/certs)"
    openssl req -x509 -newkey rsa:2048 -nodes -days 825 -subj "/CN=${BILLING_HOST:-localhost}" \
        -addext "subjectAltName=DNS:${BILLING_HOST:-localhost},DNS:localhost,IP:127.0.0.1" \
        -keyout /dados/certs/billing.key -out /dados/certs/billing.crt 2>/dev/null
    chmod 600 /dados/certs/billing.key
fi

# 2. Chaves: as informadas por variável de ambiente têm prioridade; senão são geradas
#    uma única vez e guardadas no volume (perder a chave de cifragem obriga a recadastrar o 2FA).
if [ ! -f /dados/segredos.env ]; then
    echo "[iniciar] Gerando chaves em /dados/segredos.env"
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

# 3. Modo demonstração: login simulado (sem LDAP) com usuários de teste. NUNCA usar em produção.
if [ "${BILLING_DEMO:-0}" = "1" ]; then
    echo "[iniciar] *** MODO DEMONSTRAÇÃO: login simulado, senha de todos os usuários = demo123 ***"
    export BILLING_AMBIENTE=demonstracao BILLING_IDP_TIPO=fake
    export BILLING_FAKE_USUARIOS='{"admin":"demo123","operacional":"demo123","gestor":"demo123","auditor":"demo123"}'
fi

# 4. Banco
python3 -m app.cli iniciar-banco
if [ "${BILLING_DEMO:-0}" = "1" ]; then
    python3 -m app.cli criar-usuario admin "Administrador Demo" ADMINISTRADOR 2>/dev/null || true
    python3 -m app.cli criar-usuario operacional "Operacional Demo" OPERACIONAL 2>/dev/null || true
    python3 -m app.cli criar-usuario gestor "Gestor Demo" GESTOR 2>/dev/null || true
    python3 -m app.cli criar-usuario auditor "Auditor Demo" AUDITOR 2>/dev/null || true
fi

# 5. Redirecionamento HTTP → HTTPS para a porta publicada (BILLING_PORTA_HTTPS, padrão 443)
PORTA="${BILLING_PORTA_HTTPS:-443}"
[ "$PORTA" = "443" ] && SUFIXO="" || SUFIXO=":$PORTA"
sed "s/__SUFIXO_PORTA__/$SUFIXO/" /etc/nginx/nginx.conf.modelo > /etc/nginx/nginx.conf

# 6. API (só escuta dentro do contêiner) e Nginx (porta pública)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 \
    --proxy-headers --forwarded-allow-ips 127.0.0.1 &
API=$!

for i in $(seq 1 30); do
    python3 -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/saude/api')" 2>/dev/null && break
    kill -0 $API 2>/dev/null || { echo "[iniciar] A API não subiu"; exit 1; }
    sleep 1
done

nginx -g 'daemon off;' &
WEB=$!
echo "[iniciar] Billing no ar: https://localhost (porta publicada no docker run)"

trap 'kill -TERM $API $WEB 2>/dev/null' TERM INT
# Encerra assim que qualquer um dos dois processos parar
while kill -0 $API 2>/dev/null && kill -0 $WEB 2>/dev/null; do sleep 2; done
kill -TERM $API $WEB 2>/dev/null || true
wait
exit 1
