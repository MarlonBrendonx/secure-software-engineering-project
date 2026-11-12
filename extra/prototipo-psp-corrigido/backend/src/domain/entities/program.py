"""Programa do cliente: o catálogo de onde as regras de serviço escolhem os seus programas."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.base import Entity
from src.domain.value_objects.billing_status import EntityStatus


@dataclass
class ClientProgram(Entity):
    client_uuid: UUID
    name: str
    status: EntityStatus = EntityStatus.ACTIVE
