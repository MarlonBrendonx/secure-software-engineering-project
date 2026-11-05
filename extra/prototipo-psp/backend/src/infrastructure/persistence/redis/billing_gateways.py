"""Gateways Redis do agregado de faturamento (Billing e BillingItem).

Garantias de consistência usadas aqui (o Redis não tem transação relacional):
- bloqueio otimista: `WATCH` na chave do item + `MULTI/EXEC`, 409 se outra gravação passou antes;
- lote tudo-ou-nada: `WATCH` em todas as chaves e uma única `MULTI/EXEC`;
- item e timeline gravados no mesmo `MULTI/EXEC`, para não existir mudança sem rastro.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import WatchError

from src.domain.entities.base import utcnow
from src.domain.entities.billing import (
    Billing,
    BillingHistory,
    BillingItem,
    BillingItemHistory,
)
from src.domain.exceptions import ConflictError, NotFoundError
from src.domain.ports.gateways.billing_gateway import ServiceRowRecord
from src.domain.value_objects.billing_status import BillingStatus, EntityStatus
from src.infrastructure.persistence.redis import keys
from src.infrastructure.persistence.redis.catalog_gateways import (
    RedisClientGateway,
    RedisServiceRuleGateway,
)
from src.infrastructure.persistence.redis.codec import (
    billing_from_json,
    billing_history_from_json,
    dumps,
    item_from_json,
    item_history_from_json,
    item_to_json,
)

_VERSION_CONFLICT = (
    "O registro foi modificado por outro usuário. Recarregue os dados e tente novamente."
)


def _text(v: bytes | str) -> str:
    return v.decode() if isinstance(v, bytes) else v


class RedisBillingItemGateway:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get_by_uuid(self, uuid: UUID) -> BillingItem | None:
        raw = await self._redis.get(keys.item(uuid))
        return item_from_json(raw) if raw else None

    async def get_by_uuids(self, uuids: list[UUID]) -> list[BillingItem]:
        if not uuids:
            return []
        raws = await self._redis.mget([keys.item(u) for u in dict.fromkeys(uuids)])
        return [item_from_json(r) for r in raws if r]

    async def list_by_billing(self, billing_uuid: UUID) -> list[BillingItem]:
        members = await self._redis.smembers(keys.billing_items(billing_uuid))
        if not members:
            return []
        raws = await self._redis.mget([keys.item(_text(m)) for m in members])
        return sorted(
            (item_from_json(r) for r in raws if r), key=lambda i: (i.created_at, str(i.uuid))
        )

    async def create(
        self, entity: BillingItem, *, history: BillingItemHistory | None = None
    ) -> BillingItem:
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(keys.item(entity.uuid), item_to_json(entity))
            pipe.sadd(keys.billing_items(entity.billing_uuid), str(entity.uuid))
            if history:
                pipe.rpush(keys.item_history(entity.uuid), dumps(history))
            await pipe.execute()
        return entity

    async def update(
        self,
        entity: BillingItem,
        data: dict[str, object],
        *,
        expected_version: int,
        history: BillingItemHistory | None = None,
    ) -> BillingItem:
        (updated,) = await self.update_many(
            [(dataclasses.replace(entity, version=expected_version), data, history)]
        )
        return updated

    async def update_many(
        self, updates: list[tuple[BillingItem, dict[str, object], BillingItemHistory | None]]
    ) -> list[BillingItem]:
        item_keys = [keys.item(i.uuid) for i, _, _ in updates]
        async with self._redis.pipeline(transaction=True) as pipe:
            await pipe.watch(*item_keys)
            raws = await pipe.mget(item_keys)
            result: list[BillingItem] = []
            writes: list[tuple[str, str, BillingItemHistory | None]] = []
            for (item, data, history), raw in zip(updates, raws, strict=True):
                if raw is None:
                    raise NotFoundError("Lançamento não encontrado")
                current = item_from_json(raw)
                if current.version != item.version:
                    raise ConflictError(_VERSION_CONFLICT)
                changes: dict[str, Any] = dict(data)
                updated = dataclasses.replace(
                    current, **changes, version=current.version + 1, updated_at=utcnow()
                )
                result.append(updated)
                writes.append((keys.item(updated.uuid), item_to_json(updated), history))

            pipe.multi()
            for key, payload, history in writes:
                pipe.set(key, payload)
                if history:
                    pipe.rpush(keys.item_history(history.billing_item_uuid), dumps(history))
            try:
                await pipe.execute()
            except WatchError:
                raise ConflictError(_VERSION_CONFLICT) from None
        return result

    async def delete(
        self, entity: BillingItem, *, history: BillingItemHistory | None = None
    ) -> None:
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.delete(keys.item(entity.uuid))
            pipe.srem(keys.billing_items(entity.billing_uuid), str(entity.uuid))
            if history:
                pipe.rpush(keys.item_history(entity.uuid), dumps(history))
            await pipe.execute()

    async def get_average_by_service(
        self, client_uuid: UUID, year: int, month: int, n_months: int = 3
    ) -> dict[UUID, Decimal]:
        periods: set[tuple[int, int]] = set()
        y, m = year, month
        for _ in range(n_months):
            m -= 1
            if m == 0:
                m, y = 12, y - 1
            periods.add((y, m))

        billing_ids = await self._redis.smembers(keys.client_billings(client_uuid))
        if not billing_ids:
            return {}
        raws = await self._redis.mget([keys.billing(_text(b)) for b in billing_ids])
        billings = [
            b
            for b in (billing_from_json(r) for r in raws if r)
            if (b.reference_year, b.reference_month) in periods
        ]

        totals: dict[UUID, list[Decimal]] = {}
        for b in billings:
            for item in await self.list_by_billing(b.uuid):
                totals.setdefault(item.service_rule_uuid, []).append(item.total_value)
        return {rule: sum(vals, Decimal("0")) / len(vals) for rule, vals in totals.items()}

    async def get_history(
        self, billing_item_uuid: UUID, *, status: str | None = None
    ) -> list[BillingItemHistory]:
        raws = await self._redis.lrange(keys.item_history(billing_item_uuid), 0, -1)
        entries = [item_history_from_json(r) for r in raws]
        if status:
            entries = [e for e in entries if status in (e.previous_status, e.new_status)]
        return entries


class RedisBillingGateway:
    def __init__(
        self,
        redis: Redis,
        items: RedisBillingItemGateway,
        rules: RedisServiceRuleGateway,
        clients: RedisClientGateway,
    ) -> None:
        self._redis = redis
        self._items = items
        self._rules = rules
        self._clients = clients

    async def get_by_uuid(self, uuid: UUID) -> Billing | None:
        raw = await self._redis.get(keys.billing(uuid))
        return billing_from_json(raw) if raw else None

    async def get_by_uuids(self, uuids: list[UUID]) -> list[Billing]:
        if not uuids:
            return []
        raws = await self._redis.mget([keys.billing(u) for u in dict.fromkeys(uuids)])
        return [billing_from_json(r) for r in raws if r]

    async def get_by_client_and_period(
        self, client_uuid: UUID, year: int, month: int, service_rule_uuid: UUID
    ) -> Billing | None:
        found = await self._redis.get(
            keys.billing_index(client_uuid, year, month, service_rule_uuid)
        )
        return await self.get_by_uuid(UUID(_text(found))) if found else None

    async def create(self, entity: Billing, *, history: BillingHistory | None = None) -> Billing:
        index = keys.billing_index(
            entity.client_uuid,
            entity.reference_year,
            entity.reference_month,
            entity.service_rule_uuid,
        )
        # SET NX é o equivalente à constraint única: só uma requisição cria o faturamento.
        if not await self._redis.set(index, str(entity.uuid), nx=True):
            raise ConflictError("Faturamento já existe para o cliente, período e regra")
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(keys.billing(entity.uuid), dumps(entity))
            pipe.sadd(keys.client_billings(entity.client_uuid), str(entity.uuid))
            if history:
                pipe.rpush(keys.billing_history(entity.uuid), dumps(history))
            await pipe.execute()
        return entity

    async def delete(self, entity: Billing) -> None:
        index = keys.billing_index(
            entity.client_uuid,
            entity.reference_year,
            entity.reference_month,
            entity.service_rule_uuid,
        )
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.delete(
                keys.billing(entity.uuid),
                index,
                keys.billing_items(entity.uuid),
                keys.billing_history(entity.uuid),
            )
            pipe.srem(keys.client_billings(entity.client_uuid), str(entity.uuid))
            await pipe.execute()

    async def recalculate_total(self, billing: Billing) -> Billing:
        items = await self._items.list_by_billing(billing.uuid)
        total = sum((i.total_value for i in items), Decimal("0"))
        current = await self.get_by_uuid(billing.uuid) or billing
        updated = dataclasses.replace(
            current, total_value=total, version=current.version + 1, updated_at=utcnow()
        )
        await self._redis.set(keys.billing(updated.uuid), dumps(updated))
        return updated

    async def list_services_with_items(
        self, client_uuids: list[UUID], year: int, month: int
    ) -> list[ServiceRowRecord]:
        """Equivale ao LEFT JOIN regra × faturamento × lançamento do relacional."""
        rules = await self._rules.list_by_clients(client_uuids)
        if not rules:
            return []

        idx_keys = [keys.billing_index(r.client_uuid, year, month, r.uuid) for r in rules]
        billing_ids = await self._redis.mget(idx_keys)
        billings: dict[UUID, Billing] = {}
        found_ids = [_text(b) for b in billing_ids if b]
        if found_ids:
            for raw in await self._redis.mget([keys.billing(b) for b in found_ids]):
                if raw:
                    b = billing_from_json(raw)
                    billings[b.uuid] = b

        records: list[ServiceRowRecord] = []
        for rule, billing_id in zip(rules, billing_ids, strict=True):
            billing = billings.get(UUID(_text(billing_id))) if billing_id else None
            items = (
                [
                    i
                    for i in await self._items.list_by_billing(billing.uuid)
                    if i.service_rule_uuid == rule.uuid
                ]
                if billing
                else []
            )
            if items:
                records.extend(ServiceRowRecord(rule.client_uuid, rule, i, billing) for i in items)
            elif rule.status == EntityStatus.ACTIVE:
                # Regra ativa sem lançamento é NoEntry; inativa só aparece se tiver lançamento.
                records.append(ServiceRowRecord(rule.client_uuid, rule, None, billing))
        return records

    async def get_status_summary(
        self,
        year: int,
        month: int,
        *,
        client_name: str | None = None,
        allowed: frozenset[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Totais por status; devolve sempre todos os status mais a linha `Total`."""
        clients, _ = await self._clients.list_active(0, 10_000, name=client_name, allowed=allowed)
        records = await self.list_services_with_items([c.uuid for c in clients], year, month)

        stats: dict[str, dict[str, Any]] = {
            s.value: {"count": 0, "total_value": Decimal("0")} for s in BillingStatus
        }
        for rec in records:
            status = rec.item.status.value if rec.item else BillingStatus.NO_ENTRY.value
            stats[status]["count"] += 1
            if rec.item:
                stats[status]["total_value"] += rec.item.total_value

        summary = [{"status": s, **v} for s, v in stats.items()]
        summary.append(
            {
                "status": "Total",
                "count": sum(v["count"] for v in stats.values()),
                "total_value": sum((v["total_value"] for v in stats.values()), Decimal("0")),
            }
        )
        return summary

    async def get_history(self, billing_uuid: UUID) -> list[BillingHistory]:
        raws = await self._redis.lrange(keys.billing_history(billing_uuid), 0, -1)
        return [billing_history_from_json(r) for r in raws]
