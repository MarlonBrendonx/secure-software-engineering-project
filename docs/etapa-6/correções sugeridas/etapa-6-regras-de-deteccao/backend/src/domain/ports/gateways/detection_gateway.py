"""Porta do armazenamento usado pelas regras de detecção (etapa 6).

O `CounterGateway` já conta eventos por chave em uma janela. As regras D03, D04, D06 e D12
precisam também de contagem de valores distintos, de marcas temporárias e do histórico de
origens por usuário.
"""

from __future__ import annotations

from typing import Protocol


class DetectionStateGateway(Protocol):
    async def count_distinct(self, key: str, member: str, window_seconds: int) -> int:
        """Acrescenta `member` ao conjunto da janela e devolve quantos valores distintos há."""
        ...

    async def mark(self, key: str, ttl_seconds: int) -> None:
        """Deixa uma marca que expira sozinha (ex.: "D03 disparou para esta conta")."""
        ...

    async def is_marked(self, key: str) -> bool: ...

    async def remember_origin(
        self, username: str, origin: str, lookback_seconds: int
    ) -> tuple[bool, int]:
        """Registra a origem do login e devolve (já vista antes?, origens no histórico antes).

        Só contam as origens vistas dentro de `lookback_seconds`.
        """
        ...
