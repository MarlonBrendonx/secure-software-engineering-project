"""Lançamentos (Operacional), aprovação (Gestor) e planilha para o ERP (Operacional)."""
import csv
import io
import re
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auditoria import diferencas, registrar, snapshot
from ..db import get_db
from ..deps import Contexto, exigir_papel
from ..models import (
    Aprovacao, Cliente, Contrato, ExportacaoErp, Lancamento, Papel, RegraServico,
    StatusLancamento, TipoAcao, Usuario, agora,
)

router = APIRouter(tags=["billing"])
operacional = exigir_papel(Papel.OPERACIONAL)
gestor = exigir_papel(Papel.GESTOR)
consulta = exigir_papel(Papel.OPERACIONAL, Papel.GESTOR)

RE_PERIODO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
EDITAVEIS = (StatusLancamento.RASCUNHO, StatusLancamento.REPROVADO)
CAMPOS = ["cliente_id", "periodo", "regra_servico_id", "quantidade", "valor_unitario", "valor_total", "observacao", "status"]


def validar_periodo(v: str) -> str:
    if not RE_PERIODO.match(v):
        raise ValueError("Período deve estar no formato AAAA-MM")
    return v


class LancamentoEntrada(BaseModel):
    cliente_id: int
    periodo: str = Field(description="AAAA-MM")
    regra_servico_id: int
    quantidade: Decimal = Field(gt=0, max_digits=14, decimal_places=4)
    observacao: str | None = Field(default=None, max_length=2000)

    _periodo = field_validator("periodo")(classmethod(lambda cls, v: validar_periodo(v)))


class DecisaoEntrada(BaseModel):
    observacao: str | None = Field(default=None, max_length=2000)


class ExportacaoEntrada(BaseModel):
    periodo: str

    _periodo = field_validator("periodo")(classmethod(lambda cls, v: validar_periodo(v)))


def _saida(db: Session, l: Lancamento) -> dict:
    d = snapshot(l)
    cliente = db.get(Cliente, l.cliente_id)
    regra = db.get(RegraServico, l.regra_servico_id)
    autor = db.get(Usuario, l.criado_por)
    d.update(cliente_nome=cliente.nome if cliente else None, regra_nome=regra.nome if regra else None,
             criado_por_nome=autor.nome if autor else None)
    return d


def _buscar(db: Session, lancamento_id: int) -> Lancamento:
    l = db.get(Lancamento, lancamento_id)
    if l is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lançamento não encontrado.")
    return l


def _calcular(db: Session, dados: LancamentoEntrada) -> tuple[Decimal, Decimal]:
    """O valor é sempre calculado aqui, a partir da regra de serviço cadastrada."""
    cliente = db.get(Cliente, dados.cliente_id)
    if cliente is None or not cliente.ativo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Cliente inválido.")
    regra = db.get(RegraServico, dados.regra_servico_id)
    contrato = db.get(Contrato, regra.contrato_id) if regra else None
    if regra is None or not regra.ativo or contrato is None or not contrato.ativo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Regra de serviço inválida.")
    if contrato.cliente_id != cliente.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A regra de serviço não pertence a um contrato deste cliente.")
    unitario = Decimal(regra.valor_unitario)
    total = (dados.quantidade * unitario).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return unitario, total


def _gravar(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe lançamento para este cliente, período e regra de serviço.")


# ------------------------------- lançamentos --------------------------------
@router.get("/lancamentos")
def listar(periodo: str | None = None, situacao: StatusLancamento | None = Query(default=None, alias="status"),
           cliente_id: int | None = None, limite: int = Query(default=100, ge=1, le=500),
           deslocamento: int = Query(default=0, ge=0),
           db: Session = Depends(get_db), ctx: Contexto = Depends(consulta)):
    q = db.query(Lancamento)
    if periodo:
        q = q.filter(Lancamento.periodo == periodo)
    if situacao:
        q = q.filter(Lancamento.status == situacao)
    if cliente_id:
        q = q.filter(Lancamento.cliente_id == cliente_id)
    total = q.count()
    itens = q.order_by(Lancamento.periodo.desc(), Lancamento.id.desc()).offset(deslocamento).limit(limite).all()
    return {"total": total, "itens": [_saida(db, l) for l in itens]}


@router.get("/lancamentos/{lancamento_id}")
def obter(lancamento_id: int, db: Session = Depends(get_db), ctx: Contexto = Depends(consulta)):
    l = _buscar(db, lancamento_id)
    historico = db.query(Aprovacao).filter(Aprovacao.lancamento_id == l.id).order_by(Aprovacao.data_hora).all()
    return {**_saida(db, l), "historico": [snapshot(a) for a in historico]}


@router.post("/lancamentos", status_code=status.HTTP_201_CREATED)
def criar(dados: LancamentoEntrada, request: Request, db: Session = Depends(get_db), ctx: Contexto = Depends(operacional)):
    unitario, total = _calcular(db, dados)
    l = Lancamento(**dados.model_dump(), valor_unitario=unitario, valor_total=total, criado_por=ctx.usuario.id,
                   status=StatusLancamento.RASCUNHO)
    db.add(l)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe lançamento para este cliente, período e regra de serviço.")
    registrar(db, TipoAcao.CRIACAO, request, ctx.usuario, entidade="lancamentos", entidade_id=l.id,
              detalhes={"novo": snapshot(l, CAMPOS)})
    _gravar(db)
    return _saida(db, l)


@router.put("/lancamentos/{lancamento_id}")
def editar(lancamento_id: int, dados: LancamentoEntrada, request: Request,
           db: Session = Depends(get_db), ctx: Contexto = Depends(operacional)):
    l = _buscar(db, lancamento_id)
    if l.status not in EDITAVEIS:
        raise HTTPException(status.HTTP_409_CONFLICT, "Só é possível editar lançamentos em rascunho ou reprovados.")
    antes = snapshot(l, CAMPOS)
    unitario, total = _calcular(db, dados)
    for campo, valor in dados.model_dump().items():
        setattr(l, campo, valor)
    l.valor_unitario, l.valor_total, l.status = unitario, total, StatusLancamento.RASCUNHO
    mudancas = diferencas(antes, snapshot(l, CAMPOS))
    if mudancas:
        registrar(db, TipoAcao.EDICAO, request, ctx.usuario, entidade="lancamentos", entidade_id=l.id,
                  detalhes={"alteracoes": mudancas})
    _gravar(db)
    return _saida(db, l)


@router.delete("/lancamentos/{lancamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover(lancamento_id: int, request: Request, db: Session = Depends(get_db), ctx: Contexto = Depends(operacional)):
    l = _buscar(db, lancamento_id)
    if l.status not in EDITAVEIS:
        raise HTTPException(status.HTTP_409_CONFLICT, "Só é possível remover lançamentos em rascunho ou reprovados.")
    registrar(db, TipoAcao.REMOCAO, request, ctx.usuario, entidade="lancamentos", entidade_id=l.id,
              detalhes={"registro": snapshot(l, CAMPOS)})
    db.query(Aprovacao).filter(Aprovacao.lancamento_id == l.id).delete()
    db.delete(l)
    db.commit()


@router.post("/lancamentos/{lancamento_id}/submeter")
def submeter(lancamento_id: int, request: Request, db: Session = Depends(get_db), ctx: Contexto = Depends(operacional)):
    l = _buscar(db, lancamento_id)
    if l.status not in EDITAVEIS:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este lançamento não pode ser submetido no estado atual.")
    l.status, l.submetido_em = StatusLancamento.SUBMETIDO, agora()
    registrar(db, TipoAcao.SUBMISSAO, request, ctx.usuario, entidade="lancamentos", entidade_id=l.id)
    db.commit()
    return _saida(db, l)


# ------------------------------- aprovação ----------------------------------
@router.get("/aprovacoes/pendentes")
def pendentes(periodo: str | None = None, db: Session = Depends(get_db), ctx: Contexto = Depends(gestor)):
    q = db.query(Lancamento).filter(Lancamento.status == StatusLancamento.SUBMETIDO)
    if periodo:
        q = q.filter(Lancamento.periodo == periodo)
    return [_saida(db, l) for l in q.order_by(Lancamento.submetido_em).all()]


def _decidir(lancamento_id: int, decisao: StatusLancamento, dados: DecisaoEntrada, request: Request,
             db: Session, ctx: Contexto):
    l = _buscar(db, lancamento_id)
    if l.status != StatusLancamento.SUBMETIDO:
        raise HTTPException(status.HTTP_409_CONFLICT, "Só lançamentos submetidos podem ser validados.")
    if decisao == StatusLancamento.REPROVADO and not (dados.observacao or "").strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe o motivo da reprovação.")
    l.status = decisao
    db.add(Aprovacao(lancamento_id=l.id, gestor_id=ctx.usuario.id, decisao=decisao, observacao=dados.observacao))
    tipo = TipoAcao.APROVACAO if decisao == StatusLancamento.APROVADO else TipoAcao.REPROVACAO
    registrar(db, tipo, request, ctx.usuario, entidade="lancamentos", entidade_id=l.id,
              detalhes={"observacao": dados.observacao, "valor_total": str(l.valor_total)})
    db.commit()
    return _saida(db, l)


@router.post("/lancamentos/{lancamento_id}/aprovar")
def aprovar(lancamento_id: int, request: Request, dados: DecisaoEntrada | None = None,
            db: Session = Depends(get_db), ctx: Contexto = Depends(gestor)):
    return _decidir(lancamento_id, StatusLancamento.APROVADO, dados or DecisaoEntrada(), request, db, ctx)


@router.post("/lancamentos/{lancamento_id}/reprovar")
def reprovar(lancamento_id: int, dados: DecisaoEntrada, request: Request,
             db: Session = Depends(get_db), ctx: Contexto = Depends(gestor)):
    return _decidir(lancamento_id, StatusLancamento.REPROVADO, dados, request, db, ctx)


# ------------------------------- planilha ERP -------------------------------
COLUNAS_ERP = ["lancamento_id", "periodo", "cliente_id", "cliente", "cnpj_cliente", "contrato", "centro_custo_id",
               "unidade_negocio_id", "regra_servico", "quantidade", "valor_unitario", "valor_total"]


@router.post("/exportacoes-erp", status_code=status.HTTP_201_CREATED)
def gerar_exportacao(dados: ExportacaoEntrada, request: Request,
                     db: Session = Depends(get_db), ctx: Contexto = Depends(operacional)):
    aprovados = (db.query(Lancamento)
                 .filter(Lancamento.periodo == dados.periodo, Lancamento.status == StatusLancamento.APROVADO)
                 .order_by(Lancamento.cliente_id, Lancamento.id).all())
    if not aprovados:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Não há lançamentos aprovados neste período.")

    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";", lineterminator="\n")
    escritor.writerow(COLUNAS_ERP)
    total = Decimal("0")
    for l in aprovados:
        cliente = db.get(Cliente, l.cliente_id)
        regra = db.get(RegraServico, l.regra_servico_id)
        contrato = db.get(Contrato, regra.contrato_id)
        escritor.writerow([l.id, l.periodo, cliente.id, cliente.nome, cliente.cnpj or "", contrato.numero,
                           contrato.centro_custo_id or "", contrato.unidade_negocio_id or "", regra.nome,
                           l.quantidade, l.valor_unitario, l.valor_total])
        total += Decimal(l.valor_total)

    exp = ExportacaoErp(periodo=dados.periodo, gerada_por=ctx.usuario.id, quantidade_lancamentos=len(aprovados),
                        valor_total=total, conteudo_csv=buffer.getvalue())
    db.add(exp)
    db.flush()
    registrar(db, TipoAcao.EXPORTACAO_ERP, request, ctx.usuario, entidade="exportacoes_erp", entidade_id=exp.id,
              detalhes={"periodo": dados.periodo, "lancamentos": len(aprovados), "valor_total": str(total)})
    db.commit()
    return {k: v for k, v in snapshot(exp).items() if k != "conteudo_csv"}


@router.get("/exportacoes-erp")
def listar_exportacoes(db: Session = Depends(get_db), ctx: Contexto = Depends(operacional)):
    itens = db.query(ExportacaoErp).order_by(ExportacaoErp.gerada_em.desc()).limit(200).all()
    return [{k: v for k, v in snapshot(e).items() if k != "conteudo_csv"} for e in itens]


@router.get("/exportacoes-erp/{exportacao_id}/arquivo")
def baixar_exportacao(exportacao_id: int, request: Request, db: Session = Depends(get_db),
                      ctx: Contexto = Depends(operacional)):
    exp = db.get(ExportacaoErp, exportacao_id)
    if exp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exportação não encontrada.")
    registrar(db, TipoAcao.DOWNLOAD_ERP, request, ctx.usuario, entidade="exportacoes_erp", entidade_id=exp.id)
    db.commit()
    nome = f"erp_{exp.periodo}_{exp.id}.csv"
    # BOM para o Excel abrir acentos corretamente
    return Response("﻿" + exp.conteudo_csv, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@router.get("/resumo")
def resumo(periodo: str, db: Session = Depends(get_db), ctx: Contexto = Depends(consulta)):
    """Totais do período por situação, para a tela inicial."""
    linhas = (db.query(Lancamento.status, func.count(Lancamento.id), func.coalesce(func.sum(Lancamento.valor_total), 0))
              .filter(Lancamento.periodo == periodo).group_by(Lancamento.status).all())
    return {s.value if hasattr(s, "value") else s: {"quantidade": n, "valor": str(v)} for s, n, v in linhas}
