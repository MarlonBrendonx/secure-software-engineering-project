"""Limite de tentativas de login por endereço de rede.

Janela deslizante em Redis (compartilhada entre as instâncias). Se o Redis
cair, o limite continua valendo por instância, em memória: o login não
fica nem liberado sem limite nem bloqueado para todos.
"""
import logging
import threading
import time
import uuid
from collections import defaultdict, deque

import redis

log = logging.getLogger(__name__)


class LoginRateLimiter:
    def __init__(self, redis_url: str, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._redis = redis.Redis.from_url(redis_url, socket_timeout=0.5, socket_connect_timeout=0.5)
        self._local: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, ip: str) -> tuple[bool, int]:
        """Conta uma tentativa. Devolve (permitido, segundos até liberar)."""
        try:
            return self._hit_redis(ip)
        except redis.RedisError as exc:
            log.warning("Redis indisponível para rate limit, usando limite local: %s", exc)
            return self._hit_local(ip)

    def blocked(self, key: str) -> tuple[bool, int]:
        """Só consulta, sem contar. Use com `hit` registrando apenas as falhas."""
        now = time.time()
        try:
            rkey = f"nbb:login:{key}"
            self._redis.zremrangebyscore(rkey, 0, now - self.window)
            items = self._redis.zrange(rkey, 0, -1, withscores=True)
            stamps = [score for _, score in items]
        except redis.RedisError:
            with self._lock:
                stamps = [t for t in self._local[key] if t > now - self.window]
        if len(stamps) >= self.limit:
            return True, max(int(self.window - (now - min(stamps))) + 1, 1)
        return False, 0

    def _hit_redis(self, ip: str) -> tuple[bool, int]:
        key = f"nbb:login:{ip}"
        now = time.time()
        member = f"{now}:{uuid.uuid4().hex}"
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - self.window)
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.zrange(key, 0, 0, withscores=True)
        pipe.expire(key, self.window + 1)
        _, _, count, oldest, _ = pipe.execute()
        if count > self.limit:
            retry = int(self.window - (now - oldest[0][1])) + 1 if oldest else self.window
            return False, max(retry, 1)
        return True, 0

    def _hit_local(self, ip: str) -> tuple[bool, int]:
        now = time.time()
        with self._lock:
            q = self._local[ip]
            while q and q[0] <= now - self.window:
                q.popleft()
            q.append(now)
            if len(q) > self.limit:
                return False, max(int(self.window - (now - q[0])) + 1, 1)
            return True, 0
