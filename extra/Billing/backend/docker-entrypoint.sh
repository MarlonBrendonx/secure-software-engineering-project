#!/bin/sh
# Prepara a API antes de subir: carrega/gera as chaves, espera o Postgres e aplica as migrations.
set -e
. /opt/billing/bin/billing-env

echo "[billing] aguardando o Postgres"
python - <<'PY'
import sys, time
import psycopg
from nbb.config import get_settings
url = get_settings().database_owner_url.replace("postgresql+psycopg://", "postgresql://")
for i in range(60):
    try:
        psycopg.connect(url, connect_timeout=2).close()
        sys.exit(0)
    except psycopg.OperationalError as exc:
        if i % 5 == 0:
            print(f"[billing] banco ainda indisponível: {str(exc).splitlines()[0]}", file=sys.stderr)
        time.sleep(2)
print("[billing] banco indisponível depois de 2 minutos; desistindo", file=sys.stderr)
sys.exit(1)
PY

echo "[billing] aplicando migrations"
alembic upgrade head

exec "$@"
