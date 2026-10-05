# Contêiner único: interface (React) + API (FastAPI) + Nginx com HTTPS.
# Uso:  docker build -t billing .
#       docker run -d --name billing -p 8443:443 -v billing-dados:/dados -e BILLING_DEMO=1 billing

# ---------- Estágio 1: compila a interface ----------
FROM ubuntu:24.04 AS interface
RUN apt-get update \
 && apt-get install -y --no-install-recommends nodejs npm ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- Estágio 2: imagem final ----------
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv nginx openssl ca-certificates tini \
 && rm -rf /var/lib/apt/lists/* /etc/nginx/sites-enabled/*

RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app

COPY --from=interface /src/dist /usr/share/billing
COPY infra/unico/nginx.conf /etc/nginx/nginx.conf.modelo
COPY infra/nginx/rede-permitida.conf /etc/nginx/rede-permitida.conf
COPY infra/unico/iniciar.sh /usr/local/bin/iniciar.sh
RUN chmod +x /usr/local/bin/iniciar.sh && mkdir -p /dados

# Padrões do contêiner único: banco SQLite e limite de tentativas em memória (uma instância da API).
# Para usar PostgreSQL/Redis externos, sobrescreva BILLING_DATABASE_URL / BILLING_LIMITADOR_TIPO.
ENV BILLING_DATABASE_URL=sqlite:////dados/billing.db \
    BILLING_LIMITADOR_TIPO=memoria \
    BILLING_COOKIE_SECURE=true \
    BILLING_AMBIENTE=producao

VOLUME /dados
EXPOSE 443 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python3 -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/saude/api')" || exit 1
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/iniciar.sh"]
