"""Limite de tentativas por IP em janela fixa de 1 minuto.

Em produção o contador fica no Redis, para valer entre todas as instâncias da API.
"""
import threading
import time
from typing import Protocol

from .config import get_settings


class Limitador(Protocol):
    def registrar(self, chave: str) -> tuple[bool, int, int]:
        """Conta uma tentativa. Retorna (permitido, segundos até liberar, contagem na janela)."""
        ...


def _janela() -> tuple[int, int]:
    agora = int(time.time())
    return agora // 60, 60 - (agora % 60)


class LimitadorRedis:
    def __init__(self, url: str, limite: int):
        import redis

        self.cliente = redis.Redis.from_url(url)
        self.limite = limite

    def registrar(self, chave: str) -> tuple[bool, int, int]:
        janela, restante = _janela()
        k = f"rl:{chave}:{janela}"
        pipe = self.cliente.pipeline()
        pipe.incr(k)
        pipe.expire(k, 61)
        contagem, _ = pipe.execute()
        return contagem <= self.limite, restante, contagem


class LimitadorMemoria:
    """Para testes e para rodar sem Redis em desenvolvimento."""

    def __init__(self, limite: int):
        self.limite = limite
        self._contagens: dict[str, int] = {}
        self._lock = threading.Lock()

    def registrar(self, chave: str) -> tuple[bool, int, int]:
        janela, restante = _janela()
        k = f"{chave}:{janela}"
        with self._lock:
            self._contagens = {c: v for c, v in self._contagens.items() if c.endswith(f":{janela}")}
            self._contagens[k] = self._contagens.get(k, 0) + 1
            return self._contagens[k] <= self.limite, restante, self._contagens[k]


_limitador: Limitador | None = None


def definir_limitador(limitador: Limitador) -> None:
    global _limitador
    _limitador = limitador


def get_limitador() -> Limitador:
    global _limitador
    if _limitador is None:
        s = get_settings()
        if s.limitador_tipo == "memoria":
            _limitador = LimitadorMemoria(s.limite_login_por_minuto)
        else:
            _limitador = LimitadorRedis(s.redis_url, s.limite_login_por_minuto)
    return _limitador
