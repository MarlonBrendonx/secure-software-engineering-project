"""Gateways Redis do catálogo: clientes, programas e regras de serviço.

Garantias de consistência da gravação de regras (o Redis não tem transação relacional):
- bloqueio otimista: `WATCH` na chave da regra + `MULTI/EXEC`, 409 se outra gravação passou antes;
- regra e índice do cliente (`client_rules`) gravados no mesmo `MULTI/EXEC`;
- unicidade de nome + programas conferida sob `WATCH` do índice do cliente. Uma renomeação
  concorrente de OUTRA regra do mesmo cliente não é observada: a corrida é rara e fica
  registrada como limitação do protótipo (veja o README).
"""

from __future__ import annotations

import dataclasses
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import WatchError

from src.domain.entities.base import utcnow
from src.domain.entities.client import Client
from src.domain.entities.program import ClientProgram
from src.domain.entities.service_rule import ServiceRule
from src.domain.exceptions import ConflictError, NotFoundError
from src.domain.value_objects.billing_status import EntityStatus
from src.infrastructure.persistence.redis import keys
from src.infrastructure.persistence.redis.codec import (
    client_from_json,
    dumps,
    program_from_json,
    rule_from_json,
)

_VERSION_CONFLICT = (
    "O registro foi modificado por outro usuário. Recarregue os dados e tente novamente."
)
_DUPLICATE_RULE = (
    "Já existe uma regra de serviço com este nome e o mesmo conjunto de programas para o cliente"
)
# Tentativas quando o WATCH aborta por mudança alheia ao registro (ex.: outra regra criada).
_MAX_ATTEMPTS = 3


def _text(v: bytes | str) -> str:
    return v.decode() if isinstance(v, bytes) else v


def _signature(rule: ServiceRule) -> tuple[str, frozenset[UUID]]:
    """Identidade de negócio da regra dentro do cliente: nome + conjunto de programas."""
    return rule.name.strip().casefold(), frozenset(p.uuid for p in rule.programs)


class RedisServiceRuleGateway:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get_by_uuid(self, uuid: UUID) -> ServiceRule | None:
        raw = await self._redis.get(keys.rule(uuid))
        return rule_from_json(raw) if raw else None

    async def list_by_clients(self, client_uuids: list[UUID]) -> list[ServiceRule]:
        if not client_uuids:
            return []
        async with self._redis.pipeline(transaction=False) as pipe:
            for cu in client_uuids:
                pipe.smembers(keys.client_rules(cu))
            members = await pipe.execute()
        rule_keys = [keys.rule(_text(m)) for s in members for m in s]
        if not rule_keys:
            return []
        raws = await self._redis.mget(rule_keys)
        rules = [rule_from_json(r) for r in raws if r]
        return sorted(rules, key=lambda r: (str(r.client_uuid), r.code))

    async def get_names_by_uuids(self, uuids: set[UUID]) -> dict[UUID, str]:
        if not uuids:
            return {}
        ordered = list(uuids)
        raws = await self._redis.mget([keys.rule(u) for u in ordered])
        return {u: rule_from_json(r).name for u, r in zip(ordered, raws, strict=True) if r}

    async def list_by_client(
        self,
        client_uuid: UUID,
        offset: int,
        limit: int,
        *,
        program_name: str | None = None,
        service_name: str | None = None,
    ) -> tuple[list[ServiceRule], int]:
        rules = await self.list_by_clients([client_uuid])
        if service_name:
            needle = service_name.strip().casefold()
            rules = [r for r in rules if needle in r.name.casefold()]
        if program_name:
            needle = program_name.strip().casefold()
            rules = [r for r in rules if any(needle in p.name.casefold() for p in r.programs)]
        rules.sort(key=lambda r: r.code)
        return rules[offset : offset + limit], len(rules)

    async def create(self, rule: ServiceRule) -> ServiceRule:
        set_key = keys.client_rules(rule.client_uuid)
        for _ in range(_MAX_ATTEMPTS):
            async with self._redis.pipeline(transaction=True) as pipe:
                await pipe.watch(set_key)
                await self._ensure_unique(pipe, rule)
                # O número é consumido antes do MULTI: uma tentativa abortada deixa um furo
                # na sequência, o que é inofensivo (o código só precisa ser único e crescente).
                code = int(await self._redis.incr(keys.RULE_CODE_SEQ))
                saved = dataclasses.replace(rule, code=code)
                pipe.multi()
                pipe.set(keys.rule(saved.uuid), dumps(saved))
                pipe.sadd(set_key, str(saved.uuid))
                try:
                    await pipe.execute()
                except WatchError:
                    continue
                return saved
        raise ConflictError(_VERSION_CONFLICT)

    async def update(self, rule: ServiceRule, *, expected_version: int) -> ServiceRule:
        rule_key = keys.rule(rule.uuid)
        set_key = keys.client_rules(rule.client_uuid)
        for _ in range(_MAX_ATTEMPTS):
            async with self._redis.pipeline(transaction=True) as pipe:
                await pipe.watch(rule_key, set_key)
                raw = await pipe.get(rule_key)
                if raw is None:
                    raise NotFoundError("Regra de serviço não encontrada")
                if rule_from_json(raw).version != expected_version:
                    raise ConflictError(_VERSION_CONFLICT)
                await self._ensure_unique(pipe, rule)
                saved = dataclasses.replace(rule, version=expected_version + 1, updated_at=utcnow())
                pipe.multi()
                pipe.set(rule_key, dumps(saved))
                try:
                    await pipe.execute()
                except WatchError:
                    continue
                return saved
        raise ConflictError(_VERSION_CONFLICT)

    async def delete(self, rule: ServiceRule) -> None:
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.delete(keys.rule(rule.uuid))
            pipe.srem(keys.client_rules(rule.client_uuid), str(rule.uuid))
            await pipe.execute()

    async def has_billing_items(self, rule: ServiceRule) -> bool:
        # O índice cliente × período × regra existe enquanto o faturamento tem lançamento:
        # excluir o último lançamento remove o faturamento e o índice.
        pattern = keys.billing_index_pattern(rule.client_uuid, rule.uuid)
        async for _ in self._redis.scan_iter(match=pattern, count=200):
            return True
        return False

    async def _ensure_unique(self, pipe: Redis, rule: ServiceRule) -> None:
        members = await pipe.smembers(keys.client_rules(rule.client_uuid))
        rule_keys = [keys.rule(_text(m)) for m in members if _text(m) != str(rule.uuid)]
        if not rule_keys:
            return
        target = _signature(rule)
        for raw in await pipe.mget(rule_keys):
            if raw and _signature(rule_from_json(raw)) == target:
                raise ConflictError(_DUPLICATE_RULE)


class RedisProgramGateway:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get_by_uuid(self, uuid: UUID) -> ClientProgram | None:
        raw = await self._redis.get(keys.program(uuid))
        return program_from_json(raw) if raw else None

    async def list_by_client(self, client_uuid: UUID) -> list[ClientProgram]:
        members = await self._redis.smembers(keys.client_programs(client_uuid))
        if not members:
            return []
        raws = await self._redis.mget([keys.program(_text(m)) for m in members])
        return sorted((program_from_json(r) for r in raws if r), key=lambda p: p.name)


class RedisClientGateway:
    def __init__(self, redis: Redis, rules: RedisServiceRuleGateway) -> None:
        self._redis = redis
        self._rules = rules

    async def get_by_uuid(self, uuid: UUID) -> Client | None:
        raw = await self._redis.get(keys.client(uuid))
        return client_from_json(raw) if raw else None

    async def _load_active(self, name: str | None, allowed: frozenset[str] | None) -> list[Client]:
        members = await self._redis.smembers(keys.CLIENTS)
        ids = [_text(m) for m in members]
        # Escopo aplicado antes de carregar: dados de outros clientes nem saem do Redis.
        if allowed is not None:
            ids = [i for i in ids if i in allowed]
        if not ids:
            return []

        raws = await self._redis.mget([keys.client(i) for i in ids])
        clients = [client_from_json(r) for r in raws if r]
        clients = [c for c in clients if c.status == EntityStatus.ACTIVE]
        if name:
            clients = [c for c in clients if name.lower() in c.name.lower()]
        return clients

    async def list_active(
        self,
        offset: int,
        limit: int,
        *,
        name: str | None = None,
        allowed: frozenset[str] | None = None,
    ) -> tuple[list[Client], int]:
        clients = await self._load_active(name, allowed)
        # Só entram clientes com ao menos uma regra de serviço ativa.
        rules = await self._rules.list_by_clients([c.uuid for c in clients])
        with_rules = {r.client_uuid for r in rules if r.status == EntityStatus.ACTIVE}
        clients = sorted((c for c in clients if c.uuid in with_rules), key=lambda c: c.name)
        return clients[offset : offset + limit], len(clients)

    async def search_active(
        self,
        offset: int,
        limit: int,
        *,
        name: str | None = None,
        allowed: frozenset[str] | None = None,
    ) -> tuple[list[Client], int]:
        clients = sorted(await self._load_active(name, allowed), key=lambda c: c.name)
        return clients[offset : offset + limit], len(clients)

    async def get_names_by_uuids(self, uuids: set[UUID]) -> dict[UUID, str]:
        if not uuids:
            return {}
        ordered = list(uuids)
        raws = await self._redis.mget([keys.client(u) for u in ordered])
        return {u: client_from_json(r).name for u, r in zip(ordered, raws, strict=True) if r}
