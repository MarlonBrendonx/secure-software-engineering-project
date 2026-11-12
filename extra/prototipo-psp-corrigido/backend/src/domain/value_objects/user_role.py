"""Perfis de usuário."""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    NONE = "none"


# Perfis que controlam aprovações: exigem MFA concluído (RS02 / risco R02).
PRIVILEGED_ROLES = frozenset({UserRole.ADMIN, UserRole.MANAGER})
