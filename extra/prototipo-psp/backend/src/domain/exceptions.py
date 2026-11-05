"""Exceções de domínio — desacopladas do framework HTTP."""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    def __init__(self, detail: str | list[Any]) -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(DomainError):
    """Recurso inexistente ou fora do escopo do usuário (→ 404)."""


class ConflictError(DomainError):
    """Conflito de versão (bloqueio otimista) ou de estado (→ 409)."""


class BusinessValidationError(DomainError):
    """Violação de regra de negócio (→ 422)."""


class ForbiddenError(DomainError):
    """Perfil sem permissão para a ação (→ 403)."""


class UnauthenticatedError(DomainError):
    """Credencial ausente, inválida ou sem os requisitos exigidos (→ 401).

    `reason` é um código estável (ex.: `mfa_necessario`) que o cliente pode
    tratar sem depender do texto da mensagem.
    """

    def __init__(self, detail: str, reason: str = "nao_autenticado") -> None:
        self.reason = reason
        super().__init__(detail)
