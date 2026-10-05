"""Cadastros de base. Escrita: somente Administrador. Leitura: Administrador, Operacional e Gestor
(o operacional precisa ver clientes e regras para lançar, e o gestor para validar).

Remoção é lógica (ativo = falso): os lançamentos antigos continuam apontando para o cadastro.
"""
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, create_model
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auditoria import diferencas, registrar, snapshot
from ..db import get_db
from ..deps import Contexto, exigir_papel
from ..models import (
    CentroCusto, Cliente, Contrato, Empresa, Fornecedor, GrupoEconomico, Papel, Programa,
    RegraServico, Segmento, TipoAcao, UnidadeNegocio,
)

router = APIRouter(prefix="/cadastros", tags=["cadastros"])
leitura = exigir_papel(Papel.ADMINISTRADOR, Papel.OPERACIONAL, Papel.GESTOR)
escrita = exigir_papel(Papel.ADMINISTRADOR)

Nome = (str, Field(min_length=1, max_length=200))
Cnpj = (str | None, Field(default=None, max_length=18))
IdOpcional = (int | None, None)

# slug da URL → (modelo, campos editáveis, rótulo para a tela)
ENTIDADES: dict[str, tuple[type, dict, str]] = {
    "empresas": (Empresa, {"nome": Nome, "cnpj": Cnpj}, "Empresas"),
    "segmentos": (Segmento, {"nome": Nome}, "Segmentos"),
    "programas": (Programa, {"nome": Nome}, "Programas"),
    "grupos-economicos": (GrupoEconomico, {"nome": Nome}, "Grupos econômicos"),
    "centros-custo": (CentroCusto, {"nome": Nome, "codigo": (str, Field(min_length=1, max_length=40))}, "Centros de custo"),
    "unidades-negocio": (UnidadeNegocio, {"nome": Nome}, "Unidades de negócio"),
    "fornecedores": (Fornecedor, {"nome": Nome, "cnpj": Cnpj}, "Fornecedores"),
    "clientes": (Cliente, {
        "nome": Nome, "cnpj": Cnpj, "empresa_id": (int, ...),
        "grupo_economico_id": IdOpcional, "segmento_id": IdOpcional,
    }, "Clientes"),
    "contratos": (Contrato, {
        "nome": Nome, "numero": (str, Field(min_length=1, max_length=60)), "cliente_id": (int, ...),
        "programa_id": IdOpcional, "centro_custo_id": IdOpcional, "unidade_negocio_id": IdOpcional,
        "fornecedor_id": IdOpcional, "vigencia_inicio": (date | None, None), "vigencia_fim": (date | None, None),
    }, "Contratos"),
    "regras-servico": (RegraServico, {
        "nome": Nome, "contrato_id": (int, ...),
        "unidade_medida": (str, Field(default="unidade", max_length=40)),
        "valor_unitario": (Decimal, Field(ge=0, max_digits=14, decimal_places=4)),
    }, "Regras de serviço"),
}

# chave estrangeira → modelo referenciado
REFERENCIAS = {
    "empresa_id": Empresa, "grupo_economico_id": GrupoEconomico, "segmento_id": Segmento,
    "cliente_id": Cliente, "programa_id": Programa, "centro_custo_id": CentroCusto,
    "unidade_negocio_id": UnidadeNegocio, "fornecedor_id": Fornecedor, "contrato_id": Contrato,
}

_config = ConfigDict(extra="forbid")  # campos desconhecidos (ex.: "id", "ativo") são recusados
ESQUEMAS = {slug: create_model(f"Entrada_{slug}", __config__=_config, **campos)
            for slug, (_, campos, _r) in ENTIDADES.items()}


def _entidade(slug: str):
    if slug not in ENTIDADES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cadastro inexistente.")
    return ENTIDADES[slug]


def _validar_referencias(db: Session, dados: dict) -> None:
    for campo, valor in dados.items():
        if campo in REFERENCIAS and valor is not None:
            ref = db.get(REFERENCIAS[campo], valor)
            if ref is None or not ref.ativo:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Referência inválida em '{campo}'.")
    if dados.get("vigencia_inicio") and dados.get("vigencia_fim") and dados["vigencia_fim"] < dados["vigencia_inicio"]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "O fim da vigência é anterior ao início.")


def _gravar(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um registro com esse identificador (CNPJ, código ou número).")


@router.get("")
def listar_tipos(ctx: Contexto = Depends(leitura)):
    """Lista os cadastros disponíveis e seus campos, para a tela montar os formulários."""
    saida = []
    for slug, (_, campos, rotulo) in ENTIDADES.items():
        esquema = ESQUEMAS[slug].model_json_schema()
        saida.append({"slug": slug, "rotulo": rotulo, "campos": list(campos),
                      "obrigatorios": esquema.get("required", []), "esquema": esquema["properties"]})
    return saida


@router.get("/{slug}")
def listar(slug: str, incluir_inativos: bool = False, busca: str | None = Query(default=None, max_length=100),
           limite: int = Query(default=100, ge=1, le=500), deslocamento: int = Query(default=0, ge=0),
           db: Session = Depends(get_db), ctx: Contexto = Depends(leitura)):
    modelo, _, _ = _entidade(slug)
    q = db.query(modelo)
    if not incluir_inativos:
        q = q.filter(modelo.ativo.is_(True))
    if busca:
        q = q.filter(modelo.nome.ilike(f"%{busca}%"))  # parâmetro ligado pelo SQLAlchemy, não concatenado
    total = q.count()
    itens = q.order_by(modelo.nome).offset(deslocamento).limit(limite).all()
    return {"total": total, "itens": [snapshot(i) for i in itens]}


@router.get("/{slug}/{item_id}")
def obter(slug: str, item_id: int, db: Session = Depends(get_db), ctx: Contexto = Depends(leitura)):
    modelo, _, _ = _entidade(slug)
    item = db.get(modelo, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro não encontrado.")
    return snapshot(item)


@router.post("/{slug}", status_code=status.HTTP_201_CREATED)
def criar(slug: str, corpo: dict, request: Request, db: Session = Depends(get_db), ctx: Contexto = Depends(escrita)):
    modelo, _, _ = _entidade(slug)
    dados = ESQUEMAS[slug].model_validate(corpo).model_dump()
    _validar_referencias(db, dados)
    item = modelo(**dados)
    db.add(item)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um registro com esse identificador (CNPJ, código ou número).")
    registrar(db, TipoAcao.CRIACAO, request, ctx.usuario, entidade=slug, entidade_id=item.id,
              detalhes={"novo": snapshot(item, list(dados))})
    _gravar(db)
    return snapshot(item)


@router.put("/{slug}/{item_id}")
def editar(slug: str, item_id: int, corpo: dict, request: Request,
           db: Session = Depends(get_db), ctx: Contexto = Depends(escrita)):
    modelo, campos, _ = _entidade(slug)
    item = db.get(modelo, item_id)
    if item is None or not item.ativo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro não encontrado.")
    dados = ESQUEMAS[slug].model_validate(corpo).model_dump()
    _validar_referencias(db, dados)
    antes = snapshot(item, list(campos))
    for campo, valor in dados.items():
        setattr(item, campo, valor)
    mudancas = diferencas(antes, snapshot(item, list(campos)))
    if mudancas:
        registrar(db, TipoAcao.EDICAO, request, ctx.usuario, entidade=slug, entidade_id=item.id,
                  detalhes={"alteracoes": mudancas})
    _gravar(db)
    return snapshot(item)


@router.delete("/{slug}/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover(slug: str, item_id: int, request: Request, db: Session = Depends(get_db), ctx: Contexto = Depends(escrita)):
    modelo, _, _ = _entidade(slug)
    item = db.get(modelo, item_id)
    if item is None or not item.ativo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro não encontrado.")
    item.ativo = False
    registrar(db, TipoAcao.REMOCAO, request, ctx.usuario, entidade=slug, entidade_id=item.id,
              detalhes={"registro": snapshot(item)})
    _gravar(db)
