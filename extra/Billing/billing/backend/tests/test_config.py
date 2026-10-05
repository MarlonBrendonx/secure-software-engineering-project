import pytest

from app.config import Settings
from app.main import validar_producao


def test_producao_recusa_chaves_de_exemplo():
    with pytest.raises(RuntimeError, match="BILLING_JWT_CHAVE_ATUAL"):
        validar_producao(Settings(ambiente="producao", jwt_chave_atual="troque-esta-chave"))


def test_producao_aceita_configuracao_correta():
    forte = "x" * 40
    validar_producao(Settings(ambiente="producao", jwt_chave_atual=forte, mfa_chave_cifragem=forte, ops_token=forte))


def test_rotacao_de_chave_aceita_token_da_chave_anterior(monkeypatch):
    from datetime import timedelta

    from app import config
    from app.seguranca import TIPO_ACESSO, TokenInvalido, emitir_jwt, ler_jwt

    antiga = Settings(jwt_chave_atual="a" * 40, jwt_kid_atual="k1")
    monkeypatch.setattr(config, "get_settings", lambda: antiga)
    monkeypatch.setattr("app.seguranca.get_settings", lambda: antiga)
    token = emitir_jwt({"typ": TIPO_ACESSO}, timedelta(minutes=5))

    # Rotação programada: nova chave atual, antiga ainda aceita
    nova = Settings(jwt_chave_atual="b" * 40, jwt_kid_atual="k2", jwt_chave_anterior="a" * 40, jwt_kid_anterior="k1")
    monkeypatch.setattr("app.seguranca.get_settings", lambda: nova)
    assert ler_jwt(token, TIPO_ACESSO)["typ"] == TIPO_ACESSO

    # Rotação emergencial: a chave antiga é descartada e o token deixa de valer
    emergencia = Settings(jwt_chave_atual="c" * 40, jwt_kid_atual="k3")
    monkeypatch.setattr("app.seguranca.get_settings", lambda: emergencia)
    with pytest.raises(TokenInvalido):
        ler_jwt(token, TIPO_ACESSO)
