#!/usr/bin/env bash
# Para a API e o frontend iniciados pelo dev-setup.sh (Postgres e Redis continuam no Docker).
cd "$(dirname "$0")"
for f in backend/uvicorn.pid frontend/vite.pid; do
  if [ -f "$f" ]; then
    kill "$(cat "$f")" 2>/dev/null && echo "parado: $f"
    rm -f "$f"
  fi
done
pkill -f "uvicorn nbb.main" 2>/dev/null || true
echo "Para parar também o banco: docker compose stop"
