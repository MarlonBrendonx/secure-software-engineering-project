"""Raiz de composição: liga portas a adaptadores e monta os casos de uso."""

from __future__ import annotations

from redis.asyncio import Redis

from src.application.access_guard import ResourceAccessGuard
from src.application.authenticator import Authenticator
from src.application.security_monitor import SecurityMonitor
from src.application.use_cases.auth.login import LoginUseCase, LogoutUseCase, RefreshSessionUseCase
from src.application.use_cases.billing.change_item_status import ChangeItemStatusUseCase
from src.application.use_cases.billing.create_billing_item import CreateBillingItemUseCase
from src.application.use_cases.billing.delete_billing_item import DeleteBillingItemUseCase
from src.application.use_cases.billing.queries import (
    GetBillingAverageUseCase,
    GetBillingHistoryUseCase,
    GetBillingItemUseCase,
    GetItemHistoryUseCase,
    ListBillingsByPeriodUseCase,
    ListServicesWithItemsUseCase,
)
from src.application.use_cases.billing.replicate_items import ReplicateItemsUseCase
from src.application.use_cases.billing.update_billing_item import UpdateBillingItemUseCase
from src.application.use_cases.registry.queries import (
    ListClientProgramsUseCase,
    ListRegistryClientsUseCase,
)
from src.application.use_cases.registry.service_rules import (
    CreateServiceRuleUseCase,
    DeleteServiceRuleUseCase,
    GetServiceRuleUseCase,
    ListServiceRulesUseCase,
    UpdateServiceRuleUseCase,
)
from src.core.config import Settings
from src.infrastructure.auth.jwt_token_service import JwtTokenService
from src.infrastructure.auth.mock_identity_provider import MockIdentityProvider
from src.infrastructure.persistence.redis.billing_gateways import (
    RedisBillingGateway,
    RedisBillingItemGateway,
)
from src.infrastructure.persistence.redis.catalog_gateways import (
    RedisClientGateway,
    RedisProgramGateway,
    RedisServiceRuleGateway,
)
from src.infrastructure.persistence.redis.security_gateways import (
    RedisAlertGateway,
    RedisAuditLogGateway,
    RedisCounterGateway,
    RedisSessionGateway,
    RedisUserGateway,
)
from src.infrastructure.realtime.hub import RealtimeHub


class Container:
    def __init__(self, settings: Settings, redis: Redis) -> None:
        self.settings = settings
        self.redis = redis

        # Persistência
        rules = RedisServiceRuleGateway(redis)
        clients = RedisClientGateway(redis, rules)
        programs = RedisProgramGateway(redis)
        items = RedisBillingItemGateway(redis)
        billings = RedisBillingGateway(redis, items, rules, clients)
        self.users = RedisUserGateway(redis)
        self.sessions = RedisSessionGateway(redis)
        self.audit = RedisAuditLogGateway(redis)
        self.counters = RedisCounterGateway(redis)
        alerts = RedisAlertGateway(redis)

        # Segurança
        tokens = JwtTokenService(
            secret=settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            access_ttl_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            refresh_ttl_minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES,
        )
        identity = MockIdentityProvider(settings.MOCK_LOGIN_PASSWORD, settings.MOCK_OTP_CODE)
        monitor = SecurityMonitor(self.audit, self.counters, alerts)
        guard = ResourceAccessGuard(self.users, monitor)
        self.authenticator = Authenticator(tokens, self.users, self.sessions, monitor)

        # Casos de uso de autenticação
        self.login = LoginUseCase(self.users, self.sessions, tokens, identity, self.audit, monitor)
        self.refresh = RefreshSessionUseCase(self.users, self.sessions, tokens)
        self.logout = LogoutUseCase(self.sessions, self.audit)

        # Tempo real: um hub por aplicação (não por módulo), para cada app de teste ter o seu.
        self.realtime = RealtimeHub(self.sessions, self.users)

        # Casos de uso de billing
        self.list_billings = ListBillingsByPeriodUseCase(billings, clients, guard, self.audit)
        self.list_services = ListServicesWithItemsUseCase(billings, clients, guard)
        self.get_item = GetBillingItemUseCase(billings, items, rules, guard)
        self.get_billing_history = GetBillingHistoryUseCase(billings, guard)
        self.get_item_history = GetItemHistoryUseCase(billings, items, guard)
        self.get_average = GetBillingAverageUseCase(items, clients, guard)
        self.create_item = CreateBillingItemUseCase(
            billings, items, clients, rules, guard, self.audit, self.realtime
        )
        self.update_item = UpdateBillingItemUseCase(
            billings, items, rules, guard, self.audit, self.realtime
        )
        self.delete_item = DeleteBillingItemUseCase(
            billings, items, rules, guard, self.audit, self.realtime
        )
        self.replicate_items = ReplicateItemsUseCase(
            billings, items, clients, rules, guard, self.audit, self.realtime
        )
        self.change_status = ChangeItemStatusUseCase(
            billings, items, clients, rules, guard, self.audit, self.realtime
        )

        # Casos de uso do cadastro de regras de serviço
        self.list_registry_clients = ListRegistryClientsUseCase(clients, guard)
        self.list_client_programs = ListClientProgramsUseCase(clients, programs, guard)
        self.list_service_rules = ListServiceRulesUseCase(rules, clients, guard)
        self.get_service_rule = GetServiceRuleUseCase(rules, clients, guard)
        self.create_service_rule = CreateServiceRuleUseCase(
            rules, clients, programs, guard, self.audit
        )
        self.update_service_rule = UpdateServiceRuleUseCase(
            rules, clients, programs, guard, self.audit
        )
        self.delete_service_rule = DeleteServiceRuleUseCase(rules, clients, guard, self.audit)
