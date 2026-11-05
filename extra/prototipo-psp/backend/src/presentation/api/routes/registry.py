"""Cadastros: regras de serviço (CRUD), clientes e programas.

Leitura: qualquer perfil do PSP, dentro do escopo de clientes. Escrita: só `admin`.
Os caminhos seguem o serviço original (`/registry/clients/...`) para o front funcionar igual.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.presentation.api.deps import (
    AdminUser,
    BillingUser,
    ContainerDep,
    Pagination,
    RequestId,
    rate_limit,
)
from src.presentation.api.schemas.common import create_paginated_response, create_response
from src.presentation.api.schemas.registry import (
    ServiceRuleCreate,
    ServiceRuleUpdate,
    client_response,
    client_summary_response,
    program_response,
    rule_response,
)

router = APIRouter(prefix="/registry", tags=["Registry"])

_write_limit = Depends(rate_limit("service_rule_write", 30))
SearchTerm = Annotated[str | None, Query(max_length=100)]


@router.get("/clients/summary")
async def list_clients_summary(
    container: ContainerDep, request_id: RequestId, auth: BillingUser, pagination: Pagination
) -> dict[str, Any]:
    clients, total = await container.list_registry_clients.execute(
        auth.actor, pagination.offset, pagination.per_page
    )
    return create_paginated_response(
        [client_summary_response(c) for c in clients], pagination.to_meta(total), request_id
    )


@router.get("/clients")
async def list_clients(
    container: ContainerDep,
    request_id: RequestId,
    auth: BillingUser,
    pagination: Pagination,
    search: SearchTerm = None,
) -> dict[str, Any]:
    clients, total = await container.list_registry_clients.execute(
        auth.actor, pagination.offset, pagination.per_page, search=search
    )
    return create_paginated_response(
        [client_response(c) for c in clients], pagination.to_meta(total), request_id
    )


@router.get("/clients/{client_uuid}/programs")
async def list_client_programs(
    client_uuid: UUID, container: ContainerDep, request_id: RequestId, auth: BillingUser
) -> dict[str, Any]:
    programs = await container.list_client_programs.execute(auth.actor, client_uuid)
    return create_response([program_response(p) for p in programs], request_id)


@router.get("/clients/{client_uuid}/service-rules")
async def list_service_rules(
    client_uuid: UUID,
    container: ContainerDep,
    request_id: RequestId,
    auth: BillingUser,
    pagination: Pagination,
    program_name: SearchTerm = None,
    service_name: SearchTerm = None,
) -> dict[str, Any]:
    views, total = await container.list_service_rules.execute(
        auth.actor,
        client_uuid,
        pagination.offset,
        pagination.per_page,
        program_name=program_name,
        service_name=service_name,
    )
    return create_paginated_response(
        [rule_response(v) for v in views], pagination.to_meta(total), request_id
    )


@router.post(
    "/clients/{client_uuid}/service-rules",
    status_code=status.HTTP_201_CREATED,
    dependencies=[_write_limit],
)
async def create_service_rule(
    client_uuid: UUID,
    data: ServiceRuleCreate,
    container: ContainerDep,
    request_id: RequestId,
    auth: AdminUser,
) -> dict[str, Any]:
    view = await container.create_service_rule.execute(data.to_command(auth.actor, client_uuid))
    return create_response(rule_response(view), request_id)


@router.get("/clients/{client_uuid}/service-rules/{service_rule_uuid}")
async def get_service_rule(
    client_uuid: UUID,
    service_rule_uuid: UUID,
    container: ContainerDep,
    request_id: RequestId,
    auth: BillingUser,
) -> dict[str, Any]:
    view = await container.get_service_rule.execute(auth.actor, client_uuid, service_rule_uuid)
    return create_response(rule_response(view), request_id)


@router.patch(
    "/clients/{client_uuid}/service-rules/{service_rule_uuid}", dependencies=[_write_limit]
)
async def update_service_rule(
    client_uuid: UUID,
    service_rule_uuid: UUID,
    data: ServiceRuleUpdate,
    container: ContainerDep,
    request_id: RequestId,
    auth: AdminUser,
) -> dict[str, Any]:
    view = await container.update_service_rule.execute(
        data.to_command(auth.actor, client_uuid, service_rule_uuid)
    )
    return create_response(rule_response(view), request_id)


@router.delete(
    "/clients/{client_uuid}/service-rules/{service_rule_uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_write_limit],
)
async def delete_service_rule(
    client_uuid: UUID, service_rule_uuid: UUID, container: ContainerDep, auth: AdminUser
) -> None:
    await container.delete_service_rule.execute(auth.actor, client_uuid, service_rule_uuid)
