"""Evento de auditoria.

Além do tipo e do usuário, o evento guarda os campos que permitem correlacionar a ação com a
sessão, a requisição e a origem (etapa 6, "Eventos mínimos a registrar"). Os campos que o caso
de uso não informa são preenchidos pelo contexto da requisição (`src.core.request_context`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.core import request_context
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
    # Campos de correlação (etapa 6).
    method: str | None = None
    role: str | None = None
    sid: str | None = None
    request_id: str | None = None
    # "sucesso", "negado" ou "falha". Fica `None` quando o tipo do evento já diz o resultado.
    result: str | None = None

    def __post_init__(self) -> None:
        ctx = request_context.current()
        fill: dict[str, str | None] = {
            "request_id": self.request_id or ctx.request_id,
            "origin": self.origin or ctx.origin,
            "method": self.method or ctx.method,
            "route": self.route or ctx.route,
        }
        # Perfil e sessão só valem se o evento for do próprio usuário autenticado. Um evento
        # sobre outra conta (ex.: login recusado de terceiro) não herda a sessão de ninguém.
        if self.user is not None and self.user == ctx.user:
            fill["role"] = self.role or ctx.role
            fill["sid"] = self.sid or ctx.sid
        for name, value in fill.items():
            object.__setattr__(self, name, value)
