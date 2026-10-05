# Contêiner da API (backend). Construir a partir da raiz do projeto:
#   docker build -f backend/Dockerfile -t billing-api .
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates tini \
 && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY infra/api/iniciar-api.sh /usr/local/bin/iniciar-api.sh
RUN chmod +x /usr/local/bin/iniciar-api.sh \
 && useradd --system --uid 1001 --home /app billing \
 && mkdir -p /dados && chown billing /dados
USER billing

# Padrão: SQLite no volume e limite de tentativas em memória (uma instância).
# Para PostgreSQL/Redis, sobrescreva BILLING_DATABASE_URL e BILLING_LIMITADOR_TIPO=redis.
ENV BILLING_DATABASE_URL=sqlite:////dados/billing.db \
    BILLING_LIMITADOR_TIPO=memoria \
    BILLING_COOKIE_SECURE=true \
    BILLING_AMBIENTE=producao

VOLUME /dados
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python3 -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/saude/api')" || exit 1
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/iniciar-api.sh"]
