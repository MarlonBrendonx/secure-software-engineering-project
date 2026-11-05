"""Dados de demonstração. TUDO aqui é fictício: nomes, CNPJs e e-mails inventados.

Os ids são determinísticos (uuid5) para o README, os testes e o frontend poderem referenciá-los.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from redis.asyncio import Redis

from src.domain.entities.client import Client
from src.domain.entities.program import ClientProgram
from src.domain.entities.service_rule import Program, ServiceRule, ServiceRuleRange
from src.domain.entities.user import ALL, User, UserScope
from src.domain.value_objects.billing_status import RangeType, RuleType
from src.domain.value_objects.user_role import UserRole
from src.infrastructure.persistence.redis import keys
from src.infrastructure.persistence.redis.codec import dumps


def demo_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"psp-prototype/{name}")


CLIENT_ALFA = demo_id("client/alfa")
CLIENT_BETA = demo_id("client/beta")
CLIENT_GAMA = demo_id("client/gama")

# Maior `code` usado pelos dados de demo é 302; as regras criadas pela tela começam acima.
LAST_DEMO_RULE_CODE = 1000


def _rule(
    client: UUID,
    code: int,
    name: str,
    rule_type: RuleType,
    *,
    percentage: str | None = None,
    base_value: str | None = None,
    requires_client_approval: bool = False,
    program: str | None = None,
    ranges: list[ServiceRuleRange] | None = None,
) -> ServiceRule:
    rule_id = demo_id(f"rule/{client}/{code}")
    return ServiceRule(
        uuid=rule_id,
        client_uuid=client,
        name=name,
        code=code,
        rule_type=rule_type,
        percentage=Decimal(percentage) if percentage else None,
        base_value=Decimal(base_value) if base_value else None,
        requires_client_approval=requires_client_approval,
        programs=[Program(uuid=demo_id(f"program/{program}"), name=program)] if program else [],
        ranges=ranges or [],
    )


def _ranges(rule_key: str) -> list[ServiceRuleRange]:
    spec = [
        (1, 100, False, RangeType.FIXED_VALUE, "500.00"),
        (101, 500, False, RangeType.PER_UNIT_VALUE, "4.20"),
        (501, None, True, RangeType.PER_UNIT_VALUE, "3.10"),
    ]
    return [
        ServiceRuleRange(
            range_from=lo,
            range_to=hi,
            last_range=last,
            range_type=kind,
            value=Decimal(value),
            uuid=demo_id(f"range/{rule_key}/{lo}"),
        )
        for lo, hi, last, kind, value in spec
    ]


def build_clients() -> list[Client]:
    return [
        Client(
            uuid=CLIENT_ALFA,
            name="Rede Alfa Saúde",
            cnpj="00.000.001/0001-00",
            has_client_approval_contract=True,
            code="C001",
        ),
        Client(uuid=CLIENT_BETA, name="Farmácias Beta", cnpj="00.000.002/0001-00", code="C002"),
        Client(uuid=CLIENT_GAMA, name="Drogaria Gama", cnpj="00.000.003/0001-00", code="C003"),
    ]


def build_programs() -> list[ClientProgram]:
    """Catálogo de onde as regras escolhem programas. O id reaproveita o de `_rule`."""
    spec = [
        (CLIENT_ALFA, "Programa Vida+"),
        (CLIENT_ALFA, "Programa Cuidar Mais"),
        (CLIENT_BETA, "Programa Beta Saúde"),
        (CLIENT_GAMA, "Programa Gama Care"),
    ]
    return [
        ClientProgram(uuid=demo_id(f"program/{name}"), client_uuid=client, name=name)
        for client, name in spec
    ]


def build_rules() -> list[ServiceRule]:
    return [
        _rule(
            CLIENT_ALFA,
            101,
            "Taxa de Administração",
            RuleType.FIXED_VALUE,
            program="Programa Vida+",
        ),
        _rule(
            CLIENT_ALFA,
            102,
            "Serviço por Atendimento",
            RuleType.MULTIPLICATION,
            base_value="12.50",
            program="Programa Vida+",
        ),
        _rule(
            CLIENT_ALFA,
            103,
            "Comissão sobre Vendas",
            RuleType.PERCENTAGE,
            percentage="3.5",
            base_value="10000",
            requires_client_approval=True,
            program="Programa Cuidar Mais",
        ),
        _rule(
            CLIENT_ALFA,
            104,
            "Tarifa Escalonada",
            RuleType.RANGE,
            ranges=_ranges("alfa/104"),
            program="Programa Cuidar Mais",
        ),
        _rule(
            CLIENT_ALFA,
            105,
            "Serviço Variável",
            RuleType.VARIABLE_VALUE,
            program="Programa Cuidar Mais",
        ),
        _rule(
            CLIENT_BETA,
            201,
            "Taxa de Administração",
            RuleType.FIXED_VALUE,
            program="Programa Beta Saúde",
        ),
        _rule(
            CLIENT_BETA,
            202,
            "Serviço por Atendimento",
            RuleType.MULTIPLICATION,
            base_value="9.80",
            program="Programa Beta Saúde",
        ),
        _rule(
            CLIENT_GAMA,
            301,
            "Taxa de Administração",
            RuleType.FIXED_VALUE,
            program="Programa Gama Care",
        ),
        _rule(
            CLIENT_GAMA,
            302,
            "Tarifa Escalonada",
            RuleType.RANGE,
            ranges=_ranges("gama/302"),
            program="Programa Gama Care",
        ),
    ]


def build_users() -> list[User]:
    everything = UserScope(clients=frozenset({ALL}), periods=frozenset({ALL}))
    return [
        User("admin", UserRole.ADMIN, "Admin Demo", "admin@example.com", everything),
        User("manager", UserRole.MANAGER, "Gestor Demo", "gestor@example.com", everything),
        # A analista só alcança Alfa e Beta: a Gama é o cliente "de outro escopo" dos testes.
        User(
            "analyst",
            UserRole.ANALYST,
            "Analista Demo",
            "analista@example.com",
            UserScope(
                clients=frozenset({str(CLIENT_ALFA), str(CLIENT_BETA)}), periods=frozenset({ALL})
            ),
        ),
    ]


async def seed_demo_data(redis: Redis) -> bool:
    """Carrega os dados de demonstração uma única vez. Devolve `False` se já existiam."""
    if not await redis.set(keys.SEED_FLAG, "1", nx=True):
        return False

    async with redis.pipeline(transaction=True) as pipe:
        for client in build_clients():
            pipe.set(keys.client(client.uuid), dumps(client))
            pipe.sadd(keys.CLIENTS, str(client.uuid))
        for program in build_programs():
            pipe.set(keys.program(program.uuid), dumps(program))
            pipe.sadd(keys.client_programs(program.client_uuid), str(program.uuid))
        pipe.set(keys.RULE_CODE_SEQ, LAST_DEMO_RULE_CODE)
        for rule in build_rules():
            pipe.set(keys.rule(rule.uuid), dumps(rule))
            pipe.sadd(keys.client_rules(rule.client_uuid), str(rule.uuid))
        for user in build_users():
            pipe.set(keys.user(user.username), dumps(user))
        await pipe.execute()
    return True
