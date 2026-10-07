import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from nbb.models.base import Base, utcnow


class Setting(Base):
    """Parâmetros de negócio configuráveis (limite de dupla aprovação,
    limiar do alerta de desvio etc.). Toda alteração vai para a auditoria."""

    __tablename__ = "setting"
    __audited__ = True

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[object] = mapped_column(JSONB, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
