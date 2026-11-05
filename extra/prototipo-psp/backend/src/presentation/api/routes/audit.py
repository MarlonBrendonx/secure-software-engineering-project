"""Consulta da trilha de auditoria (somente admin)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from src.presentation.api.deps import AdminUser, ContainerDep, RequestId
from src.presentation.api.schemas.common import create_response

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/events")
async def list_events(
    container: ContainerDep,
    request_id: RequestId,
    _: AdminUser,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    events = await container.audit.list_recent(limit)
    return create_response(
        [
            {
                "type": e.type,
                "user": e.user,
                "resource": e.resource,
                "resource_id": e.resource_id,
                "route": e.route,
                "detail": e.detail,
                "origin": e.origin,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
        request_id,
    )
