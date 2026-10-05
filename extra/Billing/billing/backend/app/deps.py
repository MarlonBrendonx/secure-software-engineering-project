"""Dependências de autenticação e autorização usadas por todas as rotas protegidas."""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .auditoria import registrar
from .db import get_db
from .models import Papel, Sessao, TipoAcao, Usuario, agora, utc
from .seguranca import TIPO_ACESSO, TokenInvalido, ler_jwt

COOKIE_ACESSO = "billing_access"
COOKIE_REFRESH = "billing_refresh"


@dataclass
class Contexto:
    usuario: Usuario
    sessao: Sessao


def _nao_autenticado() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada. Faça login novamente.")


def sessao_valida(sessao: Sessao | None) -> bool:
    return (
        sessao is not None
        and sessao.revogada_em is None
        and utc(sessao.expira_em) > agora()
        and sessao.usuario is not None
        and sessao.usuario.ativo
    )


def contexto_atual(request: Request, db: Session = Depends(get_db)) -> Contexto:
    token = request.cookies.get(COOKIE_ACESSO)
    if not token:
        raise _nao_autenticado()
    try:
        payload = ler_jwt(token, TIPO_ACESSO)
    except TokenInvalido:
        raise _nao_autenticado()

    # A sessão é consultada a cada requisição: revogar no banco tem efeito imediato,
    # mesmo que o token ainda não tenha expirado.
    sessao = db.get(Sessao, payload.get("sid"))
    if not sessao_valida(sessao) or str(sessao.usuario_id) != payload.get("sub"):
        raise _nao_autenticado()
    return Contexto(usuario=sessao.usuario, sessao=sessao)


def exigir_papel(*papeis: Papel):
    """Libera a rota apenas para os papéis informados. Negações ficam registradas na auditoria."""

    def verificador(request: Request, ctx: Contexto = Depends(contexto_atual), db: Session = Depends(get_db)) -> Contexto:
        if ctx.usuario.papel not in papeis:
            registrar(
                db, TipoAcao.ACESSO_NEGADO, request, usuario=ctx.usuario,
                detalhes={"metodo": request.method, "rota": request.url.path,
                          "papeis_exigidos": [p.value for p in papeis]},
            )
            db.commit()
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Seu perfil não tem permissão para esta funcionalidade.")
        return ctx

    return verificador
