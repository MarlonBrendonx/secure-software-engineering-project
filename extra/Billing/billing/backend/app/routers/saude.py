"""Verificação de saúde para o time de Operação/SRE.

Não exige login de usuário final: o acesso é por um token de operação enviado no
cabeçalho X-Ops-Token, configurado em BILLING_OPS_TOKEN.
"""
import hmac

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import JSONResponse

from ..config import get_settings
from ..idp import get_provedor

router = APIRouter(prefix="/saude", tags=["saúde"])


def _checar_token(token: str | None) -> None:
    esperado = get_settings().ops_token
    if not token or not hmac.compare_digest(token.encode(), esperado.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de operação inválido.")


@router.get("/provedor-identidade")
def saude_provedor(x_ops_token: str | None = Header(default=None)):
    _checar_token(x_ops_token)
    saude = get_provedor().verificar_saude()
    corpo = {"saudavel": saude.saudavel, "detalhe": saude.detalhe, "latencia_ms": saude.latencia_ms}
    return JSONResponse(corpo, status_code=200 if saude.saudavel else 503)


@router.get("/api")
def saude_api():
    """Usado pelo healthcheck do contêiner. Não expõe nenhum dado."""
    return {"ok": True}
