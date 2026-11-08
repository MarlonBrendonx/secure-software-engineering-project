"""Porta de aviso de mudanças no faturamento (tempo real)."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class BillingEventPublisher(Protocol):
    async def billing_changed(self, client_uuid: UUID, year: int, month: int) -> None:
        """Avisa que o faturamento do cliente no período mudou.

        Deve ser chamado depois de gravar. Nunca levanta exceção: a alteração já foi
        persistida e uma falha na entrega não pode transformá-la em erro para o usuário.
        """
        ...
