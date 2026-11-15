"""Contexto da requisição em andamento, usado para completar os eventos de auditoria.

O middleware abre o contexto com `request_id`, origem, método e rota. Depois que o token é
validado, o `Authenticator` acrescenta usuário, sessão (`sid`) e perfil. O `AuditEvent` lê
esses valores ao ser criado, então nenhum caso de uso precisa repassá-los.

Fora de uma requisição (seed, scripts, leitura da auditoria) o contexto fica vazio e os campos
ficam `None`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class RequestContext:
    request_id: str | None = None
    origin: str | None = None
    method: str | None = None
    route: str | None = None
    user: str | None = None
    sid: str | None = None
    role: str | None = None


_EMPTY = RequestContext()
_current: ContextVar[RequestContext] = ContextVar("psp_request_context", default=_EMPTY)


def current() -> RequestContext:
    return _current.get()


def start(*, request_id: str, origin: str | None, method: str, route: str) -> Token[RequestContext]:
    """Abre o contexto de uma requisição. Devolve o token para `finish`."""
    return _current.set(
        RequestContext(request_id=request_id, origin=origin, method=method, route=route)
    )


def finish(token: Token[RequestContext]) -> None:
    _current.reset(token)


def bind_session(*, user: str, sid: str | None, role: str | None) -> None:
    """Registra quem está agindo, depois que o token e a sessão foram validados."""
    _current.set(replace(_current.get(), user=user, sid=sid, role=role))


@contextmanager
def detached() -> Iterator[None]:
    """Suspende o contexto por um trecho.

    Usado ao ler eventos já gravados: um evento antigo não pode receber o `request_id` nem a
    origem de quem está consultando a auditoria.
    """
    token = _current.set(_EMPTY)
    try:
        yield
    finally:
        _current.reset(token)
