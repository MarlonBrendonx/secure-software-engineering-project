# Contêiner da interface (frontend + Nginx com HTTPS). Construir a partir da raiz do projeto:
#   docker build -f frontend/Dockerfile -t billing-web .

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

# ---------- Estágio 2: Nginx ----------
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends nginx openssl ca-certificates tini \
 && rm -rf /var/lib/apt/lists/* /etc/nginx/sites-enabled/*
COPY --from=interface /src/dist /usr/share/billing
COPY infra/web/nginx.conf.modelo /etc/nginx/nginx.conf.modelo
COPY infra/nginx/rede-permitida.conf /etc/nginx/rede-permitida.conf
COPY infra/web/iniciar-web.sh /usr/local/bin/iniciar-web.sh
RUN chmod +x /usr/local/bin/iniciar-web.sh && mkdir -p /certs

# Endereço da API dentro da rede Docker
ENV BILLING_API_URL=http://billing-api:8000
VOLUME /certs
EXPOSE 443 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD kill -0 "$(cat /run/nginx.pid)" || exit 1
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/iniciar-web.sh"]
