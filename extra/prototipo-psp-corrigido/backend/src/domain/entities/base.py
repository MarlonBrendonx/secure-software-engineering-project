"""Entidade base do DDD."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(kw_only=True)
class Entity:
    uuid: UUID = field(default_factory=uuid4)
    # Usada no bloqueio otimista: cada gravação confirmada incrementa a versão.
    version: int = 1
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(kw_only=True)
class AggregateRoot(Entity):
    """Raiz de agregado: ponto único de entrada para mudanças no agregado."""
