"""Registro da trilha de auditoria.

`registrar` só adiciona o registro à transação: quem chama faz o commit, de modo que
a alteração do dado e o seu registro de auditoria são gravados juntos (ou nenhum dos dois).
"""
from decimal import Decimal
from datetime import date, datetime

from fastapi import Request
from sqlalchemy.orm import Session

from .models import LogAuditoria, TipoAcao, Usuario


def ip_cliente(request: Request) -> str | None:
    # Atrás do Nginx, o uvicorn roda com --proxy-headers e já preenche request.client
    return request.client.host if request.client else None


def _serializavel(valor):
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if hasattr(valor, "value"):
        return valor.value
    return valor


def snapshot(obj, campos: list[str] | None = None) -> dict:
    """Foto dos campos de um registro, usada para guardar valores antes/depois."""
    campos = campos or [c.key for c in obj.__table__.columns]
    return {c: _serializavel(getattr(obj, c)) for c in campos}


def diferencas(antes: dict, depois: dict) -> dict:
    return {k: {"antes": antes.get(k), "depois": v} for k, v in depois.items() if antes.get(k) != v}


def registrar(
    db: Session,
    tipo: TipoAcao,
    request: Request | None = None,
    usuario: Usuario | None = None,
    login: str | None = None,
    entidade: str | None = None,
    entidade_id=None,
    detalhes: dict | None = None,
) -> LogAuditoria:
    log = LogAuditoria(
        tipo_acao=tipo,
        usuario_id=usuario.id if usuario else None,
        login=usuario.login if usuario else login,
        papel=usuario.papel.value if usuario else None,
        ip=ip_cliente(request) if request else None,
        entidade=entidade,
        entidade_id=str(entidade_id) if entidade_id is not None else None,
        detalhes=detalhes,
    )
    db.add(log)
    return log
