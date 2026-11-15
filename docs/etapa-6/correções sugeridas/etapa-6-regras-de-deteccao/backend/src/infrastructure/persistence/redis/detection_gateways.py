"""Gateway Redis do estado das regras de detecção (etapa 6)."""

from __future__ import annotations

import time

from redis.asyncio import Redis

from src.infrastructure.persistence.redis import keys


def _key(name: str) -> str:
    return f"{keys.PREFIX}:detect:{name}"


class RedisDetectionStateGateway:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def count_distinct(self, key: str, member: str, window_seconds: int) -> int:
        redis_key = _key(f"distinct:{key}")
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.sadd(redis_key, member)
            # NX: como no CounterGateway, a janela começa no primeiro valor e não é renovada.
            pipe.expire(redis_key, window_seconds, nx=True)
            pipe.scard(redis_key)
            _, _, total = await pipe.execute()
        return int(total)

    async def mark(self, key: str, ttl_seconds: int) -> None:
        await self._redis.set(_key(f"mark:{key}"), "1", ex=ttl_seconds)

    async def is_marked(self, key: str) -> bool:
        return bool(await self._redis.exists(_key(f"mark:{key}")))

    async def remember_origin(
        self, username: str, origin: str, lookback_seconds: int
    ) -> tuple[bool, int]:
        # Conjunto ordenado: o score é o horário do último login a partir de cada origem.
        redis_key = _key(f"origins:{username}")
        now = time.time()
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(redis_key, "-inf", now - lookback_seconds)
            pipe.zscore(redis_key, origin)
            pipe.zcard(redis_key)
            pipe.zadd(redis_key, {origin: now})
            pipe.expire(redis_key, lookback_seconds)
            _, score, total, _, _ = await pipe.execute()
        return score is not None, int(total)
