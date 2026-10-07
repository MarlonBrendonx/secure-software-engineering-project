import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, FetchedValue, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from nbb.models.base import Base, uuid_pk


class AuditEvent(Base):
    """Trilha de auditoria append-only.

    `seq`, `occurred_at`, `prev_hash` e `hash` são preenchidos pelo trigger
    `audit_event_chain` no banco, que serializa as inserções e encadeia cada
    evento ao anterior por SHA-256. UPDATE, DELETE e TRUNCATE são bloqueados
    por trigger e o usuário da aplicação só tem SELECT/INSERT.
    """

    __tablename__ = "audit_event"

    id: Mapped[uuid.UUID] = uuid_pk()
    seq: Mapped[int] = mapped_column(BigInteger, server_default=FetchedValue(), unique=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
    actor_id: Mapped[uuid.UUID | None] = mapped_column()
    actor_login: Mapped[str | None] = mapped_column(String(120))
    via_delegation_id: Mapped[uuid.UUID | None] = mapped_column()
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(200))
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64))
    prev_hash: Mapped[str] = mapped_column(String(64), server_default=FetchedValue())
    hash: Mapped[str] = mapped_column(Text, server_default=FetchedValue())
