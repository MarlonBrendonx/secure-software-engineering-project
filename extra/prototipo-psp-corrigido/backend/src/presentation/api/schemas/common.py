"""Envelope padrão de resposta (igual ao do serviço original)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    page: int = Field(..., ge=1)
    per_page: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)
    pages: int = Field(..., ge=0)
    has_next: bool
    has_prev: bool


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    def to_meta(self, total: int) -> PaginationMeta:
        pages = (total + self.per_page - 1) // self.per_page if total > 0 else 0
        return PaginationMeta(
            page=self.page,
            per_page=self.per_page,
            total=total,
            pages=pages,
            has_next=self.page < pages,
            has_prev=self.page > 1,
        )


def _numbers(value: Any) -> Any:
    """Decimal → número JSON, como o serviço original. O frontend soma e formata esses campos.

    O FastAPI novo serializa Decimal como texto, e o frontend espera número nas linhas de serviço.
    """
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _numbers(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_numbers(v) for v in value]
    return value


def _meta(request_id: str) -> dict[str, str]:
    return {"request_id": request_id, "timestamp": datetime.now(UTC).isoformat()}


def create_response(
    data: Any, request_id: str, warnings: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    response: dict[str, Any] = {"success": True, "data": _numbers(data), "meta": _meta(request_id)}
    if warnings:
        response["warnings"] = warnings
    return response


def create_paginated_response(
    data: list[Any],
    pagination: PaginationMeta,
    request_id: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "success": True,
        "data": _numbers(data),
        "pagination": pagination.model_dump(),
        "meta": _meta(request_id),
    }
    if extra:
        response.update(_numbers(extra))
    return response
