import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base declarativa.

    Modelos com ``__audited__ = True`` têm toda inserção, alteração e exclusão
    registrada automaticamente na trilha de auditoria (ver nbb.core.audit).
    Campos listados em ``__audit_redact__`` aparecem como "[redacted]".
    """

    __audited__: bool = False
    __audit_redact__: frozenset[str] = frozenset()


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def created_at_col() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
