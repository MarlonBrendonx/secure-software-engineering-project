"""Quem executa a operação — resolvido pela camada de apresentação após autenticar."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Actor:
    username: str
    role: str
