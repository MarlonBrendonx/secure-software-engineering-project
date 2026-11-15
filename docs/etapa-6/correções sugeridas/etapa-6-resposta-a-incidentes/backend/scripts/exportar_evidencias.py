"""Copia a auditoria e os alertas do Redis para um arquivo com hash (resposta, passo 1).

A lista `psp:audit` guarda só os 5.000 eventos mais recentes. Ao receber um alerta, a cópia tem
de ser feita antes que os eventos do período saiam da lista. O script só lê o Redis.

Uso, a partir de `backend/`:

    .venv/bin/python scripts/exportar_evidencias.py --saida /caminho/fora/do/servidor \\
        --incidente INC-2026-001 [--usuario manager] [--origem 10.0.0.9] [--request-id abc...]

Sem filtros, exporta tudo o que está na lista. Com filtros, exporta os eventos que atendem a
qualquer um deles e mantém todos os alertas. O endereço do Redis vem de `REDIS_URL`.

Gera dois arquivos na pasta de saída:

- `<incidente>-<horário UTC>.json`: eventos, alertas, filtros usados e horário da cópia;
- o mesmo nome com `.sha256`: hash SHA-256 do JSON, no formato do `sha256sum`.

Guarde os dois fora do ambiente afetado. Para conferir depois: `sha256sum -c <arquivo>.sha256`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from redis import Redis

AUDIT_KEY = "psp:audit"
ALERTS_KEY = "psp:alerts"


def _decode(raw: bytes | str) -> Any:
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        # Entrada fora do formato esperado vai como texto, para não perder nada da evidência.
        return {"bruto": raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw}


def _matches(event: Any, filters: dict[str, str]) -> bool:
    if not filters:
        return True
    if not isinstance(event, dict):
        return True
    return any(event.get(field) == value for field, value in filters.items())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--saida", required=True, type=Path, help="pasta de destino")
    parser.add_argument("--incidente", required=True, help="número do registro do incidente")
    parser.add_argument("--usuario", help="filtra eventos pelo campo user")
    parser.add_argument("--origem", help="filtra eventos pelo campo origin")
    parser.add_argument("--request-id", dest="request_id", help="filtra pelo request_id")
    args = parser.parse_args()

    filters = {
        field: value
        for field, value in (
            ("user", args.usuario),
            ("origin", args.origem),
            ("request_id", args.request_id),
        )
        if value
    }

    redis = Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    # Lê as duas listas de uma vez, para a cópia representar um mesmo instante.
    with redis.pipeline(transaction=True) as pipe:
        pipe.lrange(AUDIT_KEY, 0, -1)
        pipe.lrange(ALERTS_KEY, 0, -1)
        raw_events, raw_alerts = pipe.execute()

    events = [e for e in (_decode(r) for r in raw_events) if _matches(e, filters)]
    alerts = [_decode(r) for r in raw_alerts]
    copied_at = datetime.now(UTC)

    document = {
        "incidente": args.incidente,
        "copiado_em_utc": copied_at.isoformat(),
        "filtros": filters,
        "total_eventos_na_lista": len(raw_events),
        "eventos": events,
        "alertas": alerts,
    }
    payload = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()

    args.saida.mkdir(parents=True, exist_ok=True)
    name = f"{args.incidente}-{copied_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    target = args.saida / name
    if target.exists():
        print(f"Já existe {target}; nada foi sobrescrito.", file=sys.stderr)
        return 1
    target.write_bytes(payload)
    (args.saida / f"{name}.sha256").write_text(f"{digest}  {name}\n", encoding="utf-8")

    print(f"{len(events)} eventos e {len(alerts)} alertas copiados para {target}")
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
