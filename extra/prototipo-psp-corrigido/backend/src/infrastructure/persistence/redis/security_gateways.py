"""Gateways Redis de segurança: usuários, sessões, auditoria, contadores e alertas."""

from __future__ import annotations

import logging

from redis.asyncio import Redis

from src.domain.entities.audit import AuditEvent
from src.domain.entities.session import AuthSession
from src.domain.entities.user import User, UserScope
from src.infrastructure.persistence.redis import keys
from src.infrastructure.persistence.redis.codec import (
    audit_from_json,
    dumps,
    session_from_json,
    user_from_json,
)

logger = logging.getLogger("psp.security")

# A lista de auditoria é limitada para o Redis do protótipo não crescer sem controle.
# Em produção a trilha iria para uma tabela append-only (RS05 e C6 da etapa 3).
_AUDIT_MAX_ENTRIES = 5000


def queue_audit(pipe: Redis, event: AuditEvent) -> None:
    """Enfileira o evento de auditoria em uma transação já aberta (RS05).

    Quem grava a operação de negócio chama isto dentro do mesmo `MULTI/EXEC`: ou a
    operação e o registro entram juntos, ou nenhum dos dois entra.
    """
    pipe.lpush(keys.AUDIT, dumps(event))
    pipe.ltrim(keys.AUDIT, 0, _AUDIT_MAX_ENTRIES - 1)


class RedisUserGateway:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get_by_username(self, username: str) -> User | None:
        raw = await self._redis.get(keys.user(username))
        return user_from_json(raw) if raw else None

    async def get_scope(self, username: str) -> UserScope:
        user = await self.get_by_username(username)
        # Sem cadastro, o escopo é vazio e nada é liberado.
        return user.scope if user else UserScope()


class RedisSessionGateway:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def create(self, session: AuthSession, ttl_seconds: int) -> None:
        await self._redis.set(keys.session(session.sid), dumps(session), ex=ttl_seconds)

    async def get(self, sid: str) -> AuthSession | None:
        raw = await self._redis.get(keys.session(sid))
        return session_from_json(raw) if raw else None

    async def revoke(self, sid: str) -> None:
        await self._redis.delete(keys.session(sid))


class RedisAuditLogGateway:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def record(self, event: AuditEvent) -> None:
        async with self._redis.pipeline(transaction=True) as pipe:
            queue_audit(pipe, event)
            await pipe.execute()

    async def list_recent(self, limit: int = 50) -> list[AuditEvent]:
        raws = await self._redis.lrange(keys.AUDIT, 0, limit - 1)
        return [audit_from_json(r) for r in raws]


class RedisCounterGateway:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def increment(self, key: str, window_seconds: int) -> int:
        redis_key = keys.counter(key)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(redis_key)
            # NX: a janela começa no primeiro evento e não é renovada pelos seguintes.
            pipe.expire(redis_key, window_seconds, nx=True)
            total, _ = await pipe.execute()
        return int(total)


class RedisAlertGateway:
    """Alerta do protótipo: log estruturado + lista no Redis (em produção, o SIEM)."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def fire(self, name: str, **context: object) -> None:
        logger.warning("ALERTA de segurança: %s %s", name, context)
        await self._redis.lpush(keys.ALERTS, dumps({"alert": name, **context}))
        await self._redis.ltrim(keys.ALERTS, 0, 999)
