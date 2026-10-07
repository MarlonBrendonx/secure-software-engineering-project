# API do Billing (FastAPI). Roda as migrations e gera as chaves na primeira subida.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
RUN useradd --system --uid 10001 --create-home nbb \
 && mkdir -p /segredos && chown nbb:nbb /segredos && chmod 700 /segredos

# Dependências primeiro: só reinstala quando o pyproject muda.
COPY pyproject.toml ./
COPY nbb ./nbb
RUN pip install .

COPY alembic.ini ./
COPY migrations ./migrations
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY docker/billing-env docker/nbb /opt/billing/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh /opt/billing/bin/nbb
# O "nbb" de /opt/billing/bin vem antes no PATH e carrega as chaves antes de rodar o comando.
ENV PATH=/opt/billing/bin:$PATH

USER nbb
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
# A API só é acessada pelo Nginx do container web: o IP real do usuário vem no X-Forwarded-For.
CMD ["uvicorn", "nbb.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
