"""Envio de e-mail. Em produção, trocar por um adaptador SMTP/serviço da empresa."""
import logging
from dataclasses import dataclass, field
from typing import Protocol

log = logging.getLogger(__name__)


class Mailer(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


@dataclass
class OutboxMailer:
    """Guarda as mensagens em memória (desenvolvimento e testes)."""

    sent: list[tuple[str, str, str]] = field(default_factory=list)

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))
        log.info("E-mail para %s: %s", to, subject)
