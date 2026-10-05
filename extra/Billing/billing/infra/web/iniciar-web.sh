#!/bin/sh
set -e

# Certificado: usa o da empresa se montado em /certs; senão gera um autoassinado.
if [ ! -f /certs/billing.crt ] || [ ! -f /certs/billing.key ]; then
    echo "[web] Gerando certificado autoassinado (troque pelo da empresa em /certs)"
    openssl req -x509 -newkey rsa:2048 -nodes -days 825 -subj "/CN=${BILLING_HOST:-localhost}" \
        -addext "subjectAltName=DNS:${BILLING_HOST:-localhost},DNS:localhost,IP:127.0.0.1" \
        -keyout /certs/billing.key -out /certs/billing.crt 2>/dev/null
    chmod 600 /certs/billing.key
fi

# Redirecionamento HTTP → HTTPS para a porta publicada (BILLING_PORTA_HTTPS, padrão 443)
PORTA="${BILLING_PORTA_HTTPS:-443}"
[ "$PORTA" = "443" ] && SUFIXO="" || SUFIXO=":$PORTA"
API=$(printf '%s' "$BILLING_API_URL" | sed 's/[\/&|]/\\&/g')
sed -e "s|__SUFIXO_PORTA__|$SUFIXO|" -e "s|__API_URL__|$API|" \
    /etc/nginx/nginx.conf.modelo > /etc/nginx/nginx.conf

echo "[web] Encaminhando /api para $BILLING_API_URL"
exec nginx -g 'daemon off;'
