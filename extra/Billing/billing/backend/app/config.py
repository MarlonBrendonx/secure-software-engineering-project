"""Configuração central. Todos os valores vêm de variáveis de ambiente (prefixo BILLING_)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BILLING_", env_file=".env", extra="ignore")

    ambiente: str = "desenvolvimento"  # desenvolvimento | producao

    # Banco e cache
    database_url: str = "postgresql+psycopg://billing:billing@db:5432/billing"
    redis_url: str = "redis://redis:6379/0"

    # Tokens
    jwt_chave_atual: str = "troque-esta-chave-em-producao-com-32-bytes-ou-mais"
    jwt_kid_atual: str = "k1"
    # Chave anterior, aceita apenas para validação durante a rotação programada
    jwt_chave_anterior: str | None = None
    jwt_kid_anterior: str | None = None
    jwt_algoritmo: str = "HS256"
    access_token_minutos: int = 15
    sessao_maxima_horas: int = 8          # renovação permitida até esse limite absoluto
    desafio_mfa_minutos: int = 5          # tempo para concluir a etapa do segundo fator

    # Limite de tentativas (login e verificação do segundo fator)
    limite_login_por_minuto: int = 10
    limitador_tipo: str = "redis"          # redis | memoria (memoria só vale para uma instância)

    # Segundo fator
    mfa_emissor: str = "Billing"
    # Chave usada para cifrar os segredos TOTP no banco (qualquer texto longo e aleatório)
    mfa_chave_cifragem: str = "troque-esta-chave-de-cifragem-do-segundo-fator"

    # Provedor de identidade
    idp_tipo: str = "ldap"                 # ldap | fake (somente testes/desenvolvimento)
    ldap_url: str = "ldaps://ldap.empresa.local:636"
    ldap_dominio: str = "EMPRESA"          # bind como DOMINIO\\usuario
    ldap_timeout_segundos: int = 5

    # Token estático para o time de Operação/SRE consultar a saúde do IdP
    ops_token: str = "troque-este-token-de-operacao"

    # Cookies
    cookie_secure: bool = True

    # Auditoria
    retencao_logs_anos: int = 5

    @property
    def producao(self) -> bool:
        return self.ambiente == "producao"


@lru_cache
def get_settings() -> Settings:
    return Settings()
