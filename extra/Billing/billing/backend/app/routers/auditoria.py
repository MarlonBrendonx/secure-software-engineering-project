"""Consulta da trilha de auditoria (somente leitura, perfil Auditor).

Não existem rotas para editar ou apagar registros. A remoção por prazo de retenção é
feita apenas pelo comando de manutenção `python -m app.cli limpar-logs`.
"""
import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..auditoria import snapshot
from ..db import get_db
from ..deps import Contexto, exigir_papel
from ..models import LogAuditoria, Papel, TipoAcao

router = APIRouter(prefix="/auditoria", tags=["auditoria"])
auditor = exigir_papel(Papel.AUDITOR)


def _filtrar(db: Session, usuario_id, login, papel, tipo_acao, entidade, de, ate):
    q = db.query(LogAuditoria)
    if usuario_id is not None:
        q = q.filter(LogAuditoria.usuario_id == usuario_id)
    if login:
        q = q.filter(LogAuditoria.login == login.strip().lower())
    if papel:
        q = q.filter(LogAuditoria.papel == papel.value)
    if tipo_acao:
        q = q.filter(LogAuditoria.tipo_acao.in_(tipo_acao))
    if entidade:
        q = q.filter(LogAuditoria.entidade == entidade)
    if de:
        q = q.filter(LogAuditoria.data_hora >= de)
    if ate:
        q = q.filter(LogAuditoria.data_hora <= ate)
    return q


@router.get("")
def consultar(
    usuario_id: int | None = None, login: str | None = None, papel: Papel | None = None,
    tipo_acao: list[TipoAcao] | None = Query(default=None), entidade: str | None = None,
    de: datetime | None = None, ate: datetime | None = None,
    limite: int = Query(default=50, ge=1, le=200), deslocamento: int = Query(default=0, ge=0),
    db: Session = Depends(get_db), ctx: Contexto = Depends(auditor),
):
    q = _filtrar(db, usuario_id, login, papel, tipo_acao, entidade, de, ate)
    total = q.count()
    itens = q.order_by(LogAuditoria.data_hora.desc(), LogAuditoria.id.desc()).offset(deslocamento).limit(limite).all()
    return {"total": total, "itens": [snapshot(i) for i in itens]}


@router.get("/tipos")
def tipos(ctx: Contexto = Depends(auditor)):
    return {"tipos_acao": [t.value for t in TipoAcao], "papeis": [p.value for p in Papel]}


@router.get("/exportar")
def exportar(
    usuario_id: int | None = None, login: str | None = None, papel: Papel | None = None,
    tipo_acao: list[TipoAcao] | None = Query(default=None), entidade: str | None = None,
    de: datetime | None = None, ate: datetime | None = None,
    db: Session = Depends(get_db), ctx: Contexto = Depends(auditor),
):
    """Exporta o resultado filtrado em CSV (até 50 mil linhas por arquivo)."""
    q = _filtrar(db, usuario_id, login, papel, tipo_acao, entidade, de, ate)
    buffer = io.StringIO()
    w = csv.writer(buffer, delimiter=";", lineterminator="\n")
    colunas = ["id", "data_hora", "usuario_id", "login", "papel", "ip", "tipo_acao", "entidade", "entidade_id", "detalhes"]
    w.writerow(colunas)
    for log in q.order_by(LogAuditoria.data_hora.desc()).limit(50_000).yield_per(1000):
        d = snapshot(log)
        w.writerow([d[c] if d[c] is not None else "" for c in colunas])
    return Response("﻿" + buffer.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="auditoria.csv"'})
