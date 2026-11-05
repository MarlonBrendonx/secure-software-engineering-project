"""Cliente (rede credenciada) faturado pelo PSP."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities.base import Entity
from src.domain.value_objects.billing_status import EntityStatus


@dataclass
class Client(Entity):
    name: str
    # CNPJ fictício no protótipo; é dado de pessoa jurídica (ativo A5 da etapa 1).
    cnpj: str
    status: EntityStatus = EntityStatus.ACTIVE
    # Resume "possui contrato com aprovação de cliente habilitada" (RF-PSP-33).
    has_client_approval_contract: bool = False
    # Código curto exibido nas telas de cadastro; o uuid continua sendo a identidade.
    code: str = ""
