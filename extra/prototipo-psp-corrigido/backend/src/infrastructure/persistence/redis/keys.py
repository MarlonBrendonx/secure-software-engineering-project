"""Convenção de chaves do Redis. Tudo sob o prefixo `psp:` para isolar o protótipo."""

from __future__ import annotations

from uuid import UUID

PREFIX = "psp"

CLIENTS = f"{PREFIX}:clients"
AUDIT = f"{PREFIX}:audit"
ALERTS = f"{PREFIX}:alerts"
SEED_FLAG = f"{PREFIX}:seed:v1"
# Sequência do `code` das regras. O seed a inicia acima dos códigos fictícios dos dados de demo.
RULE_CODE_SEQ = f"{PREFIX}:seq:rule_code"


def client(uuid: UUID | str) -> str:
    return f"{PREFIX}:client:{uuid}"


def client_rules(client_uuid: UUID | str) -> str:
    return f"{PREFIX}:client:{client_uuid}:rules"


def client_billings(client_uuid: UUID | str) -> str:
    return f"{PREFIX}:client:{client_uuid}:billings"


def rule(uuid: UUID | str) -> str:
    return f"{PREFIX}:rule:{uuid}"


def program(uuid: UUID | str) -> str:
    return f"{PREFIX}:program:{uuid}"


def client_programs(client_uuid: UUID | str) -> str:
    return f"{PREFIX}:client:{client_uuid}:programs"


def billing(uuid: UUID | str) -> str:
    return f"{PREFIX}:billing:{uuid}"


def billing_index(client_uuid: UUID | str, year: int, month: int, rule_uuid: UUID | str) -> str:
    """Índice único cliente × período × regra (equivale à constraint do relacional)."""
    return f"{PREFIX}:billing:idx:{client_uuid}:{year}-{month:02d}:{rule_uuid}"


def billing_index_pattern(client_uuid: UUID | str, rule_uuid: UUID | str) -> str:
    """Padrão (glob) de todos os índices de faturamento de uma regra, em qualquer período."""
    return f"{PREFIX}:billing:idx:{client_uuid}:*:{rule_uuid}"


def billing_items(billing_uuid: UUID | str) -> str:
    return f"{PREFIX}:billing:{billing_uuid}:items"


def billing_history(billing_uuid: UUID | str) -> str:
    return f"{PREFIX}:billing:{billing_uuid}:history"


def item(uuid: UUID | str) -> str:
    return f"{PREFIX}:item:{uuid}"


def item_history(item_uuid: UUID | str) -> str:
    return f"{PREFIX}:item:{item_uuid}:history"


def user(username: str) -> str:
    return f"{PREFIX}:user:{username}"


def session(sid: str) -> str:
    return f"{PREFIX}:session:{sid}"


def counter(name: str) -> str:
    return f"{PREFIX}:counter:{name}"
