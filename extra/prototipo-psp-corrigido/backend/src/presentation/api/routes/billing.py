"""Rotas de faturamento PSP: lançamentos, status e timeline."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from src.application.use_cases.billing.commands import (
    ChangeItemStatusCommand,
    CreateBillingItemCommand,
    DeleteBillingItemCommand,
    ReplicateItemsCommand,
    UpdateBillingItemCommand,
)
from src.presentation.api.deps import (
    BillingUser,
    ContainerDep,
    Pagination,
    RequestId,
    rate_limit,
)
from src.presentation.api.schemas.billing import (
    BillingBatchStatusUpdate,
    BillingHistoryResponse,
    BillingItemCreate,
    BillingItemHistoryResponse,
    BillingItemReplicateRequest,
    BillingItemResponse,
    BillingItemUpdate,
    BillingStatusUpdate,
)
from src.presentation.api.schemas.common import create_paginated_response, create_response

router = APIRouter(tags=["Billing"])


def _item(item: Any) -> dict[str, Any]:
    return BillingItemResponse.model_validate(item).model_dump(mode="json")


# ── Listagem ─────────────────────────────────────────────────────────


@router.get("")
async def list_billings(
    container: ContainerDep,
    pagination: Pagination,
    request_id: RequestId,
    auth: BillingUser,
    year: int = Query(..., ge=2026),
    month: int = Query(..., ge=1, le=12),
    client_name: str | None = Query(default=None, min_length=2),
) -> dict[str, Any]:
    items, total, summary = await container.list_billings.execute(
        auth.actor, year, month, pagination.offset, pagination.per_page, client_name=client_name
    )
    return create_paginated_response(
        items, pagination.to_meta(total), request_id, extra={"status_summary": summary}
    )


@router.get("/clients/{client_uuid}/services")
async def list_services_with_items(
    client_uuid: UUID,
    container: ContainerDep,
    request_id: RequestId,
    auth: BillingUser,
    year: int = Query(..., ge=2026),
    month: int = Query(..., ge=1, le=12),
) -> dict[str, Any]:
    rows = await container.list_services.execute(auth.actor, client_uuid, year, month)
    return create_response(rows, request_id)


@router.get("/clients/{client_uuid}/average")
async def get_average(
    client_uuid: UUID,
    container: ContainerDep,
    request_id: RequestId,
    auth: BillingUser,
    year: int = Query(..., ge=2026),
    month: int = Query(..., ge=1, le=12),
) -> dict[str, Any]:
    averages = await container.get_average.execute(auth.actor, client_uuid, year, month)
    return create_response({str(k): float(v) for k, v in averages.items()}, request_id)


# ── Lançamentos ──────────────────────────────────────────────────────


@router.post(
    "/items",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("create_item", 30))],
)
async def create_billing_item(
    data: BillingItemCreate, container: ContainerDep, request_id: RequestId, auth: BillingUser
) -> dict[str, Any]:
    # Os valores enviados são só uma sugestão: o caso de uso recalcula pela regra de serviço.
    item, warnings = await container.create_item.execute(
        CreateBillingItemCommand(actor=auth.actor, **data.model_dump())
    )
    return create_response(_item(item), request_id, warnings=warnings or None)


@router.post(
    "/items/replicate",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("replicate", 10))],
)
async def replicate_billing_items(
    data: BillingItemReplicateRequest,
    container: ContainerDep,
    request_id: RequestId,
    auth: BillingUser,
) -> dict[str, Any]:
    items, warnings = await container.replicate_items.execute(
        ReplicateItemsCommand(actor=auth.actor, **data.model_dump())
    )
    return create_response([_item(i) for i in items], request_id, warnings=warnings or None)


@router.post("/items/batch-status", dependencies=[Depends(rate_limit("batch_status", 10))])
async def change_item_status_batch(
    data: BillingBatchStatusUpdate,
    container: ContainerDep,
    request_id: RequestId,
    auth: BillingUser,
) -> dict[str, Any]:
    items = await container.change_status.execute_batch(
        ChangeItemStatusCommand(
            actor=auth.actor,
            new_status=data.new_status,
            item_uuids=data.item_uuids,
            rejection_reason=data.rejection_reason,
        )
    )
    return create_response(
        {"updated_count": len(items), "items": [_item(i) for i in items]}, request_id
    )


@router.get("/items/{item_uuid}")
async def get_billing_item(
    item_uuid: UUID, container: ContainerDep, request_id: RequestId, auth: BillingUser
) -> dict[str, Any]:
    item = await container.get_item.execute(auth.actor, item_uuid)
    return create_response(_item(item), request_id)


@router.patch("/items/{item_uuid}")
async def update_billing_item(
    item_uuid: UUID,
    data: BillingItemUpdate,
    container: ContainerDep,
    request_id: RequestId,
    auth: BillingUser,
) -> dict[str, Any]:
    item, warnings = await container.update_item.execute(
        UpdateBillingItemCommand(actor=auth.actor, item_uuid=item_uuid, **data.model_dump())
    )
    return create_response(_item(item), request_id, warnings=warnings or None)


@router.delete("/items/{item_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_billing_item(
    item_uuid: UUID, container: ContainerDep, auth: BillingUser
) -> Response:
    await container.delete_item.execute(DeleteBillingItemCommand(auth.actor, item_uuid))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/items/{item_uuid}/status", dependencies=[Depends(rate_limit("change_status", 20))])
async def change_item_status(
    item_uuid: UUID,
    data: BillingStatusUpdate,
    container: ContainerDep,
    request_id: RequestId,
    auth: BillingUser,
) -> dict[str, Any]:
    item = await container.change_status.execute(
        ChangeItemStatusCommand(
            actor=auth.actor,
            new_status=data.new_status,
            item_uuids=[item_uuid],
            rejection_reason=data.rejection_reason,
        )
    )
    return create_response(_item(item), request_id)


# ── Timeline ─────────────────────────────────────────────────────────


@router.get("/{billing_uuid}/history")
async def get_billing_history(
    billing_uuid: UUID, container: ContainerDep, request_id: RequestId, auth: BillingUser
) -> dict[str, Any]:
    history = await container.get_billing_history.execute(auth.actor, billing_uuid)
    return create_response(
        [BillingHistoryResponse.model_validate(h).model_dump(mode="json") for h in history],
        request_id,
    )


@router.get("/items/{item_uuid}/history")
async def get_item_history(
    item_uuid: UUID,
    container: ContainerDep,
    request_id: RequestId,
    auth: BillingUser,
    status: str | None = Query(default=None),
) -> dict[str, Any]:
    history = await container.get_item_history.execute(auth.actor, item_uuid, status=status)
    return create_response(
        [BillingItemHistoryResponse.model_validate(h).model_dump(mode="json") for h in history],
        request_id,
    )
