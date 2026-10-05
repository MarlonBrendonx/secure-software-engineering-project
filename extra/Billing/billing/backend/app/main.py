from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .config import get_settings
from .routers import auditoria, auth, billing, cadastros, saude, usuarios


def validar_producao(s) -> None:
    """Em produção, não sobe com chaves de exemplo nem cookies sem a flag Secure."""
    if not s.producao:
        return
    problemas = []
    for nome in ("jwt_chave_atual", "mfa_chave_cifragem", "ops_token"):
        valor = getattr(s, nome)
        if valor.startswith("troque") or len(valor) < 32:
            problemas.append(f"BILLING_{nome.upper()} precisa ser um valor aleatório com 32+ caracteres")
    if not s.cookie_secure:
        problemas.append("BILLING_COOKIE_SECURE deve ser true em produção")
    if s.idp_tipo != "ldap":
        problemas.append("BILLING_IDP_TIPO deve ser 'ldap' em produção")
    if problemas:
        raise RuntimeError("Configuração insegura para produção:\n- " + "\n- ".join(problemas))


def criar_app() -> FastAPI:
    s = get_settings()
    validar_producao(s)
    app = FastAPI(
        title="Billing — API",
        version="1.0.0",
        # Em produção a documentação interativa fica desligada
        docs_url=None if s.producao else "/api/docs",
        redoc_url=None,
        openapi_url=None if s.producao else "/api/openapi.json",
    )
    @app.exception_handler(ValidationError)
    async def erro_validacao(request, exc: ValidationError):
        # Validações feitas dentro das rotas (ex.: cadastros genéricos) viram 422, não 500
        return JSONResponse({"detail": exc.errors(include_url=False, include_context=False)}, status_code=422)

    for r in (auth.router, saude.router, usuarios.router, cadastros.router, billing.router, auditoria.router):
        app.include_router(r, prefix="/api")

    @app.middleware("http")
    async def cabecalhos(request, call_next):
        resposta = await call_next(request)
        # Respostas da API nunca devem ficar em cache (contêm dados e sessão)
        resposta.headers.setdefault("Cache-Control", "no-store")
        return resposta

    return app


app = criar_app()
