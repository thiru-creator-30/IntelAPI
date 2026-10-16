from __future__ import annotations

from typing import Any, List, TypeVar

from pydantic import BaseModel, Field

from app.core.errors import AppError, ErrorCode

DEFAULT_LIMIT = 50
MAX_LIMIT = 100

T = TypeVar("T")


class PaginationParams(BaseModel):
    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)
    offset: int = Field(default=0, ge=0)


class Page(BaseModel):
    limit: int
    offset: int
    total: int


class Paginated(BaseModel):
    items: List[Any]
    pagination: Page


def parse_pagination(limit: int = DEFAULT_LIMIT, offset: int = 0) -> PaginationParams:
    if limit < 1 or limit > MAX_LIMIT:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            f"limit must be between 1 and {MAX_LIMIT}",
            details={"limit": limit},
        )
    if offset < 0:
        raise AppError(ErrorCode.VALIDATION_ERROR, "offset must be >= 0", details={"offset": offset})
    return PaginationParams(limit=limit, offset=offset)


def paginate(items: List[T], params: PaginationParams) -> tuple[List[T], int]:
    total = len(items)
    return items[params.offset : params.offset + params.limit], total
