"""Porta do provedor de identidade (no protótipo, um mock; em produção, o SSO)."""

from __future__ import annotations

from typing import Protocol


class IdentityProvider(Protocol):
    def check_password(self, username: str, password: str) -> bool:
        """Confere a senha em tempo constante, mesmo para usuário inexistente."""
        ...

    def check_second_factor(self, username: str, code: str) -> bool: ...
