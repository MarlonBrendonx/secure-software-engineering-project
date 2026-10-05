"""Base local de usuários: quem pode entrar e com qual perfil (somente Administrador).

A senha não fica aqui: ela é do login corporativo. Este cadastro define o vínculo do
login corporativo com o sistema e o papel do usuário.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auditoria import diferencas, registrar, snapshot
from ..db import get_db
from ..deps import Contexto, exigir_papel
from ..models import Papel, Sessao, TipoAcao, Usuario, agora, utc
from .auth import revogar_sessoes_usuario

router = APIRouter(prefix="/usuarios", tags=["usuários"])
admin = exigir_papel(Papel.ADMINISTRADOR)

CAMPOS_AUDITADOS = ["login", "nome", "email", "papel", "ativo", "mfa_ativo"]


class UsuarioEntrada(BaseModel):
    login: str = Field(min_length=1, max_length=120)
    nome: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    papel: Papel


class UsuarioEdicao(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    papel: Papel | None = None
    ativo: bool | None = None


class UsuarioSaida(BaseModel):
    id: int
    login: str
    nome: str
    email: str | None
    papel: Papel
    ativo: bool
    mfa_ativo: bool
    sessoes_ativas: int = 0


def _saida(db: Session, u: Usuario) -> UsuarioSaida:
    ativas = db.query(Sessao).filter(Sessao.usuario_id == u.id, Sessao.revogada_em.is_(None)).all()
    n = sum(1 for s in ativas if utc(s.expira_em) > agora())
    return UsuarioSaida(id=u.id, login=u.login, nome=u.nome, email=u.email, papel=u.papel,
                        ativo=u.ativo, mfa_ativo=u.mfa_ativo, sessoes_ativas=n)


def _buscar(db: Session, usuario_id: int) -> Usuario:
    u = db.get(Usuario, usuario_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado.")
    return u


@router.get("", response_model=list[UsuarioSaida])
def listar(db: Session = Depends(get_db), ctx: Contexto = Depends(admin)):
    return [_saida(db, u) for u in db.query(Usuario).order_by(Usuario.nome).all()]


@router.post("", response_model=UsuarioSaida, status_code=status.HTTP_201_CREATED)
def criar(dados: UsuarioEntrada, request: Request, db: Session = Depends(get_db), ctx: Contexto = Depends(admin)):
    login = dados.login.strip().lower()
    if db.query(Usuario).filter(Usuario.login == login).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um usuário com esse login.")
    u = Usuario(login=login, nome=dados.nome, email=dados.email, papel=dados.papel)
    db.add(u)
    db.flush()
    registrar(db, TipoAcao.CRIACAO, request, ctx.usuario, entidade="usuarios", entidade_id=u.id,
              detalhes={"novo": snapshot(u, CAMPOS_AUDITADOS)})
    db.commit()
    return _saida(db, u)


@router.put("/{usuario_id}", response_model=UsuarioSaida)
def editar(usuario_id: int, dados: UsuarioEdicao, request: Request,
           db: Session = Depends(get_db), ctx: Contexto = Depends(admin)):
    u = _buscar(db, usuario_id)
    if u.id == ctx.usuario.id and (dados.papel not in (None, u.papel) or dados.ativo is False):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Você não pode alterar o próprio perfil nem se desativar.")
    antes = snapshot(u, CAMPOS_AUDITADOS)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(u, campo, valor)
    revogadas = 0
    # Mudar o papel ou desativar encerra as sessões abertas: o acesso antigo não pode continuar valendo
    if antes["papel"] != u.papel.value or (antes["ativo"] and not u.ativo):
        revogadas = revogar_sessoes_usuario(db, u, "alteracao_de_acesso")
    mudancas = diferencas(antes, snapshot(u, CAMPOS_AUDITADOS))
    if mudancas:
        registrar(db, TipoAcao.EDICAO, request, ctx.usuario, entidade="usuarios", entidade_id=u.id,
                  detalhes={"alteracoes": mudancas, "sessoes_revogadas": revogadas})
    db.commit()
    return _saida(db, u)


@router.post("/{usuario_id}/revogar-sessoes")
def revogar_sessoes(usuario_id: int, request: Request, db: Session = Depends(get_db), ctx: Contexto = Depends(admin)):
    u = _buscar(db, usuario_id)
    n = revogar_sessoes_usuario(db, u, "revogacao_manual")
    registrar(db, TipoAcao.SESSAO_REVOGADA, request, ctx.usuario, entidade="usuarios", entidade_id=u.id,
              detalhes={"sessoes_revogadas": n})
    db.commit()
    return {"sessoes_revogadas": n}


@router.post("/{usuario_id}/redefinir-mfa")
def redefinir_mfa(usuario_id: int, request: Request, db: Session = Depends(get_db), ctx: Contexto = Depends(admin)):
    """Para quando o usuário perde o celular: no próximo login ele cadastra o segundo fator de novo."""
    u = _buscar(db, usuario_id)
    u.mfa_ativo = False
    u.mfa_segredo_cifrado = None
    n = revogar_sessoes_usuario(db, u, "redefinicao_mfa")
    registrar(db, TipoAcao.EDICAO, request, ctx.usuario, entidade="usuarios", entidade_id=u.id,
              detalhes={"acao": "redefinir_mfa", "sessoes_revogadas": n})
    db.commit()
    return {"ok": True}
