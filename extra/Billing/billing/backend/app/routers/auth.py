"""Módulo de autenticação: login, segundo fator, renovação, status da sessão e logout."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auditoria import ip_cliente, registrar
from ..config import get_settings
from ..db import get_db
from ..deps import COOKIE_ACESSO, COOKIE_REFRESH, Contexto, contexto_atual, sessao_valida
from ..idp import get_provedor
from ..models import Sessao, TipoAcao, Usuario, agora, utc
from ..ratelimit import get_limitador
from ..seguranca import (
    TIPO_ACESSO, TIPO_DESAFIO_MFA, TokenInvalido, cifrar_segredo, decifrar_segredo,
    emitir_access_token, emitir_desafio_mfa, expiracao_sessao, hash_refresh, ler_jwt,
    novo_refresh_token, novo_segredo_mfa, uri_mfa, verificar_codigo_mfa,
)

router = APIRouter(prefix="/auth", tags=["autenticação"])

COOKIE_DESAFIO = "billing_mfa"
PATH_ACESSO = "/"
PATH_REFRESH = "/api/auth"
PATH_DESAFIO = "/api/auth/mfa"

MSG_CREDENCIAIS = "Usuário ou senha inválidos."


# ------------------------------- esquemas -----------------------------------
class LoginEntrada(BaseModel):
    login: str = Field(min_length=1, max_length=120)
    senha: str = Field(min_length=1, max_length=256)


class LoginSaida(BaseModel):
    etapa: str  # "mfa_cadastro" (primeiro acesso) ou "mfa_verificacao"


class CadastroMfaSaida(BaseModel):
    segredo: str
    uri: str


class CodigoEntrada(BaseModel):
    codigo: str = Field(min_length=6, max_length=6)


class UsuarioSaida(BaseModel):
    id: int
    login: str
    nome: str
    papel: str


class SessaoSaida(BaseModel):
    ativa: bool
    usuario: UsuarioSaida
    sessao_criada_em: str
    sessao_expira_em: str
    acesso_expira_em_segundos: int


# ------------------------------- cookies ------------------------------------
def _cookie(response: Response, nome: str, valor: str, path: str, segundos: int) -> None:
    response.set_cookie(
        nome, valor, max_age=segundos, path=path, httponly=True,
        secure=get_settings().cookie_secure, samesite="strict",
    )


def _apagar_cookies(response: Response) -> None:
    s = get_settings()
    for nome, path in ((COOKIE_ACESSO, PATH_ACESSO), (COOKIE_REFRESH, PATH_REFRESH), (COOKIE_DESAFIO, PATH_DESAFIO)):
        response.delete_cookie(nome, path=path, httponly=True, secure=s.cookie_secure, samesite="strict")


def _emitir_cookies_sessao(response: Response, usuario: Usuario, sessao: Sessao, refresh: str) -> None:
    s = get_settings()
    restante = int((utc(sessao.expira_em) - agora()).total_seconds())
    acesso = emitir_access_token(usuario.id, usuario.papel.value, sessao.id)
    _cookie(response, COOKIE_ACESSO, acesso, PATH_ACESSO, min(s.access_token_minutos * 60, restante))
    _cookie(response, COOKIE_REFRESH, refresh, PATH_REFRESH, restante)


def _usuario_saida(u: Usuario) -> UsuarioSaida:
    return UsuarioSaida(id=u.id, login=u.login, nome=u.nome, papel=u.papel.value)


# ------------------------------- limite -------------------------------------
def _aplicar_limite(db: Session, request: Request, escopo: str, login: str | None = None) -> None:
    """Conta a tentativa antes de qualquer validação de credencial."""
    permitido, restante, contagem = get_limitador().registrar(f"{escopo}:{ip_cliente(request)}")
    if permitido:
        return
    # Registra só a primeira tentativa bloqueada da janela, para um ataque não lotar a auditoria
    if contagem == get_settings().limite_login_por_minuto + 1:
        registrar(db, TipoAcao.LOGIN_BLOQUEADO, request, login=login, detalhes={"escopo": escopo})
        db.commit()
    raise HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "Muitas tentativas. Aguarde um minuto e tente novamente.",
        headers={"Retry-After": str(restante)},
    )


def _usuario_do_desafio(request: Request, db: Session) -> Usuario:
    token = request.cookies.get(COOKIE_DESAFIO)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Etapa de login expirada. Informe usuário e senha novamente.")
    try:
        payload = ler_jwt(token, TIPO_DESAFIO_MFA)
    except TokenInvalido:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Etapa de login expirada. Informe usuário e senha novamente.")
    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None or not usuario.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, MSG_CREDENCIAIS)
    return usuario


# ------------------------------- rotas --------------------------------------
@router.post("/login", response_model=LoginSaida)
def login(dados: LoginEntrada, request: Request, response: Response, db: Session = Depends(get_db)):
    """Etapa 1: limite de tentativas → validação no login corporativo → desafio do segundo fator."""
    login_normalizado = dados.login.strip().lower()
    _aplicar_limite(db, request, "login", login_normalizado)

    usuario = db.query(Usuario).filter(Usuario.login == login_normalizado).one_or_none()
    credenciais_ok = get_provedor().validar_credenciais(login_normalizado, dados.senha)

    motivo = None
    if not credenciais_ok:
        motivo = "credenciais_invalidas"
    elif usuario is None:
        motivo = "usuario_sem_cadastro_local"
    elif not usuario.ativo:
        motivo = "usuario_inativo"

    if motivo:
        registrar(db, TipoAcao.LOGIN_FALHA, request, login=login_normalizado, detalhes={"motivo": motivo})
        db.commit()
        # Mesma mensagem em todos os casos: não revela se o usuário existe
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, MSG_CREDENCIAIS)

    _cookie(response, COOKIE_DESAFIO, emitir_desafio_mfa(usuario.id), PATH_DESAFIO,
            get_settings().desafio_mfa_minutos * 60)
    return LoginSaida(etapa="mfa_verificacao" if usuario.mfa_ativo else "mfa_cadastro")


@router.post("/mfa/cadastro", response_model=CadastroMfaSaida)
def cadastrar_mfa(request: Request, db: Session = Depends(get_db)):
    """Primeiro acesso: gera o segredo para o aplicativo autenticador. Só fica ativo após a verificação."""
    usuario = _usuario_do_desafio(request, db)
    if usuario.mfa_ativo:
        raise HTTPException(status.HTTP_409_CONFLICT, "O segundo fator já está cadastrado para este usuário.")
    segredo = novo_segredo_mfa()
    usuario.mfa_segredo_cifrado = cifrar_segredo(segredo)
    db.commit()
    return CadastroMfaSaida(segredo=segredo, uri=uri_mfa(segredo, usuario.login))


@router.post("/mfa/verificar", response_model=UsuarioSaida)
def verificar_mfa(dados: CodigoEntrada, request: Request, response: Response, db: Session = Depends(get_db)):
    """Etapa 2: confere o código do aplicativo e, se correto, abre a sessão."""
    _aplicar_limite(db, request, "mfa")
    usuario = _usuario_do_desafio(request, db)
    _aplicar_limite(db, request, f"mfa-usuario-{usuario.id}", usuario.login)

    if not usuario.mfa_segredo_cifrado:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cadastre o segundo fator antes de verificar.")
    if not verificar_codigo_mfa(decifrar_segredo(usuario.mfa_segredo_cifrado), dados.codigo):
        registrar(db, TipoAcao.MFA_FALHA, request, usuario=usuario)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Código inválido.")

    if not usuario.mfa_ativo:
        usuario.mfa_ativo = True
        registrar(db, TipoAcao.MFA_CADASTRADO, request, usuario=usuario)

    refresh, refresh_hash = novo_refresh_token()
    sessao = Sessao(
        usuario_id=usuario.id, refresh_hash=refresh_hash, expira_em=expiracao_sessao(),
        ip=ip_cliente(request), user_agent=(request.headers.get("user-agent") or "")[:300],
    )
    db.add(sessao)
    db.flush()
    registrar(db, TipoAcao.LOGIN_OK, request, usuario=usuario, entidade="sessao", entidade_id=sessao.id)
    db.commit()
    db.refresh(sessao)

    response.delete_cookie(COOKIE_DESAFIO, path=PATH_DESAFIO, httponly=True,
                           secure=get_settings().cookie_secure, samesite="strict")
    _emitir_cookies_sessao(response, usuario, sessao, refresh)
    return _usuario_saida(usuario)


@router.post("/renovar", status_code=status.HTTP_204_NO_CONTENT)
def renovar(request: Request, response: Response, db: Session = Depends(get_db)):
    """Troca o token de renovação por um novo par de tokens, até o limite absoluto da sessão."""
    token = request.cookies.get(COOKIE_REFRESH)
    sessao = db.query(Sessao).filter(Sessao.refresh_hash == hash_refresh(token)).one_or_none() if token else None
    if not sessao_valida(sessao):
        negado = JSONResponse({"detail": "Sessão encerrada. Faça login novamente."}, status.HTTP_401_UNAUTHORIZED)
        _apagar_cookies(negado)
        return negado
    novo, novo_hash = novo_refresh_token()  # rotação: o token anterior deixa de valer
    sessao.refresh_hash = novo_hash
    sessao.ultimo_uso = agora()
    db.commit()
    _emitir_cookies_sessao(response, sessao.usuario, sessao, novo)
    return None


@router.get("/sessao", response_model=SessaoSaida)
def status_sessao(request: Request, ctx: Contexto = Depends(contexto_atual)):
    payload = ler_jwt(request.cookies[COOKIE_ACESSO], TIPO_ACESSO)
    restante = max(0, payload["exp"] - int(agora().timestamp()))
    return SessaoSaida(
        ativa=True,
        usuario=_usuario_saida(ctx.usuario),
        sessao_criada_em=utc(ctx.sessao.criada_em).isoformat(),
        sessao_expira_em=utc(ctx.sessao.expira_em).isoformat(),
        acesso_expira_em_segundos=restante,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """Encerra de verdade: revoga a sessão no servidor e apaga os cookies do navegador.

    Funciona mesmo com o token de acesso já expirado (usa o token de renovação para achar a sessão).
    """
    sessao = None
    token = request.cookies.get(COOKIE_ACESSO)
    if token:
        try:
            sessao = db.get(Sessao, ler_jwt(token, TIPO_ACESSO).get("sid"))
        except TokenInvalido:
            sessao = None
    if sessao is None and (refresh := request.cookies.get(COOKIE_REFRESH)):
        sessao = db.query(Sessao).filter(Sessao.refresh_hash == hash_refresh(refresh)).one_or_none()

    if sessao is not None and sessao.revogada_em is None:
        sessao.revogada_em = agora()
        sessao.motivo_revogacao = "logout"
        registrar(db, TipoAcao.LOGOUT, request, usuario=sessao.usuario, entidade="sessao", entidade_id=sessao.id)
        db.commit()

    _apagar_cookies(response)
    response.headers["Clear-Site-Data"] = '"cookies"'
    return None


def revogar_sessoes_usuario(db: Session, usuario: Usuario, motivo: str) -> int:
    """Usado na desativação de usuário, na revogação manual e na rotação emergencial de chaves."""
    sessoes = db.query(Sessao).filter(Sessao.usuario_id == usuario.id, Sessao.revogada_em.is_(None)).all()
    for s in sessoes:
        s.revogada_em = agora()
        s.motivo_revogacao = motivo
    return len(sessoes)
