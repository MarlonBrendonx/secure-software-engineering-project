#!/usr/bin/env bash
# Prepara e sobe o ambiente de desenvolvimento. Pode rodar quantas vezes quiser:
# não sobrescreve o .env, só preenche chaves que ainda estão com o texto de exemplo.
#
# Uso:  ./dev-setup.sh LOGIN "NOME" EMAIL
#  ex.: ./dev-setup.sh lucas "Lucas A. Martins" lucas@gmail.com
#
# Precisa de: Docker, Python 3.12+ e Node.js 18+.
set -euo pipefail
cd "$(dirname "$0")"

LOGIN="${1:-}"; NOME="${2:-}"; EMAIL="${3:-}"

echo "==> Postgres e Redis (docker compose)"
docker compose up -d postgres redis

cd backend
echo "==> Dependências Python"
pip install -q -e ".[dev]"

if [ ! -f .env ]; then
  echo "==> Criando backend/.env a partir do modelo"
  cp ../.env.example .env
fi
# Chaves: se faltarem no .env (ou estiverem com o texto de exemplo), reaproveita as que o
# contêiner da API já gerou no volume "segredos". Assim os dois modos (contêineres e
# desenvolvimento) usam as mesmas chaves e o 2FA cadastrado continua valendo nos dois.
falta_chave() {  # $1 = nome da variável
  ! grep -q "^$1=" .env || grep -q "^$1=.*cole-aqui" .env
}
chave_do_volume() {  # $1 = jwt_key | data_key
  [ -n "$(cd .. && docker compose ps -a -q api 2>/dev/null)" ] || return 0
  (cd .. && docker compose run --rm --no-deps -T --entrypoint cat api "/segredos/$1" 2>/dev/null) || true
}
grava() {  # $1 = variável, $2 = valor
  sed -i "/^$1=/d" .env
  echo "$1=$2" >> .env
}
if falta_chave NBB_JWT_KEYS; then
  JWT=$(chave_do_volume jwt_key)
  if [ -n "$JWT" ]; then echo "==> Usando a chave do JWT dos contêineres"; KID=vol1
  else echo "==> Gerando chave do JWT"; JWT=$(nbb generate-key); KID=k1; fi
  grava NBB_JWT_KEYS "{\"$KID\":\"$JWT\"}"
  grava NBB_JWT_ACTIVE_KID "$KID"
fi
if falta_chave NBB_DATA_ENCRYPTION_KEYS; then
  DATA=$(chave_do_volume data_key)
  if [ -n "$DATA" ]; then echo "==> Usando a chave do 2FA dos contêineres"
  else echo "==> Gerando chave de criptografia do 2FA"; DATA=$(nbb generate-data-key); fi
  grava NBB_DATA_ENCRYPTION_KEYS "[\"$DATA\"]"
fi
chmod 600 .env

echo "==> Aguardando o Postgres"
for _ in $(seq 1 30); do
  docker compose exec -T postgres pg_isready -q -U nbb_owner && break
  sleep 1
done

echo "==> Migrations"
alembic upgrade head

if [ -n "$EMAIL" ]; then
  echo "==> Administrador inicial"
  nbb bootstrap-admin "$LOGIN" "$NOME" "$EMAIL" || echo "    (administrador já existe, seguindo)"
fi

echo "==> Servidor em segundo plano (log em backend/uvicorn.log)"
[ -f uvicorn.pid ] && kill "$(cat uvicorn.pid)" 2>/dev/null || true
pkill -f "uvicorn nbb.main" 2>/dev/null || true   # servidores iniciados à mão antes do script
sleep 1
nohup uvicorn nbb.main:create_app --factory --reload > uvicorn.log 2>&1 &
echo $! > uvicorn.pid
for _ in $(seq 1 15); do
  curl -sf http://127.0.0.1:8000/health/live >/dev/null && break
  sleep 1
done
if ! curl -sf http://127.0.0.1:8000/health/live >/dev/null; then
  echo "!!  A API não respondeu. Últimas linhas do log:"
  tail -20 uvicorn.log
  exit 1
fi

cd ../frontend
echo "==> Frontend (npm)"
[ -d node_modules ] || npm install --no-audit --no-fund
[ -f vite.pid ] && kill "$(cat vite.pid)" 2>/dev/null || true
sleep 1
nohup npx vite > vite.log 2>&1 &
echo $! > vite.pid
for _ in $(seq 1 20); do
  curl -sf http://localhost:5173/ >/dev/null && break
  sleep 1
done
echo
echo "==> Pronto"
echo "    Sistema:          http://localhost:5173"
echo "    API (Swagger):    http://localhost:8000/api/v1/docs"
echo "    Logs:             tail -f backend/uvicorn.log   |   tail -f frontend/vite.log"
echo "    Parar:            ./dev-stop.sh"
