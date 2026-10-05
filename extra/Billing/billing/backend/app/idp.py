"""Adaptador do Provedor de Identidade corporativo.

O sistema não guarda senhas: usuário e senha são validados no login corporativo.
A implementação padrão faz bind LDAP/AD. Para trocar por outro SSO, basta criar
outra classe com os mesmos dois métodos e registrá-la em `get_provedor`.
"""
from dataclasses import dataclass
from typing import Protocol

from .config import get_settings


@dataclass
class SaudeProvedor:
    saudavel: bool
    detalhe: str
    latencia_ms: float | None = None


class ProvedorIdentidade(Protocol):
    def validar_credenciais(self, login: str, senha: str) -> bool: ...
    def verificar_saude(self) -> SaudeProvedor: ...


class ProvedorLDAP:
    def __init__(self, url: str, dominio: str, timeout: int):
        self.url, self.dominio, self.timeout = url, dominio, timeout

    def _servidor(self):
        from ldap3 import Server

        return Server(self.url, connect_timeout=self.timeout)

    def validar_credenciais(self, login: str, senha: str) -> bool:
        from ldap3 import NTLM, Connection
        from ldap3.core.exceptions import LDAPException

        # Senha vazia faria um "bind anônimo" bem-sucedido em muitos servidores
        if not login or not senha:
            return False
        try:
            conn = Connection(
                self._servidor(), user=f"{self.dominio}\\{login}", password=senha,
                authentication=NTLM, receive_timeout=self.timeout,
            )
            ok = conn.bind()
            conn.unbind()
            return bool(ok)
        except LDAPException:
            return False

    def verificar_saude(self) -> SaudeProvedor:
        import time

        from ldap3 import Connection
        from ldap3.core.exceptions import LDAPException

        inicio = time.perf_counter()
        try:
            conn = Connection(self._servidor(), receive_timeout=self.timeout)
            conn.open()
            conn.unbind()
            ms = (time.perf_counter() - inicio) * 1000
            return SaudeProvedor(True, "Conexão com o provedor de identidade estabelecida", round(ms, 1))
        except LDAPException as exc:
            return SaudeProvedor(False, f"Falha ao conectar: {type(exc).__name__}")


class ProvedorFake:
    """Somente para testes e desenvolvimento local. Bloqueado em produção."""

    def __init__(self, usuarios: dict[str, str] | None = None, saudavel: bool = True):
        self.usuarios = usuarios or {}
        self.saudavel = saudavel

    def validar_credenciais(self, login: str, senha: str) -> bool:
        return bool(senha) and self.usuarios.get(login) == senha

    def verificar_saude(self) -> SaudeProvedor:
        if self.saudavel:
            return SaudeProvedor(True, "Provedor fake disponível", 0.1)
        return SaudeProvedor(False, "Provedor fake indisponível")


_provedor: ProvedorIdentidade | None = None


def definir_provedor(provedor: ProvedorIdentidade) -> None:
    global _provedor
    _provedor = provedor


def get_provedor() -> ProvedorIdentidade:
    global _provedor
    if _provedor is None:
        s = get_settings()
        if s.idp_tipo == "fake":
            if s.producao:
                raise RuntimeError("O provedor fake não pode ser usado em produção")
            import json
            import os

            _provedor = ProvedorFake(json.loads(os.getenv("BILLING_FAKE_USUARIOS", "{}")))
        else:
            _provedor = ProvedorLDAP(s.ldap_url, s.ldap_dominio, s.ldap_timeout_segundos)
    return _provedor
