"""Evento de auditoria."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.base import utcnow


@dataclass(frozen=True)
class AuditEvent:
    type: str
    user: str | None
    resource: str | None = None
    resource_id: str | None = None
    route: str | None = None
    detail: str | None = None
    origin: str | None = None
    created_at: datetime = field(default_factory=utcnow)
