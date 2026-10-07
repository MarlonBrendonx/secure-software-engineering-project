"""Leitura e validação dos parâmetros configuráveis (tabela `setting`)."""
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from sqlalchemy.orm import Session

from nbb.models import Setting


def _money(v: Any) -> str:
    try:
        d = Decimal(str(v))
    except InvalidOperation as exc:
        raise ValueError("valor monetário inválido") from exc
    if d <= 0 or d != d.quantize(Decimal("0.01")):
        raise ValueError("use um valor positivo com até 2 casas decimais")
    return str(d.quantize(Decimal("0.01")))


def _int_range(lo: int, hi: int) -> Callable[[Any], int]:
    def check(v: Any) -> int:
        if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
            raise ValueError(f"use um inteiro entre {lo} e {hi}")
        return v
    return check


def _bool(v: Any) -> bool:
    if not isinstance(v, bool):
        raise ValueError("use true ou false")
    return v


VALIDATORS: dict[str, Callable[[Any], Any]] = {
    "approval.double_threshold": _money,
    "approval.deviation_pct": _int_range(1, 1000),
    "approval.deviation_window_months": _int_range(1, 36),
    "delegation.max_days": _int_range(1, 365),
    "privacy.store_cpf": _bool,
    "mfa.required_for_all": _bool,
}


def get_value(db: Session, key: str) -> Any:
    row = db.get(Setting, key)
    if row is None:
        raise KeyError(key)
    return row.value


def get_decimal(db: Session, key: str) -> Decimal:
    return Decimal(str(get_value(db, key)))


def set_value(db: Session, key: str, value: Any, user_id) -> Setting:
    if key not in VALIDATORS:
        raise KeyError(key)
    row = db.get(Setting, key)
    if row is None:
        raise KeyError(key)
    row.value = VALIDATORS[key](value)
    row.updated_by = user_id
    return row
