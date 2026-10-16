from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class CollectionRead(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RequestDefinitionIn(BaseModel):
    method: str = Field(pattern="^(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)$")
    url: str = Field(min_length=1, max_length=8192)
    headers: dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    environment_id: Optional[UUID] = None
    collection_id: Optional[UUID] = None
    name: str = Field(min_length=1, max_length=200)


class SavedRequestRead(BaseModel):
    id: UUID
    project_id: UUID
    collection_id: Optional[UUID]
    environment_id: Optional[UUID]
    name: str
    method: str
    url: str
    headers: dict[str, str]
    body: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EnvironmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class EnvironmentVariableIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    value: str
    is_secret: bool = True


class EnvironmentVariableRead(BaseModel):
    id: UUID
    name: str
    value: str  # redacted: "••••••••" when secret
    is_secret: bool
    created_at: datetime
    updated_at: datetime


class EnvironmentRead(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    variables: list[EnvironmentVariableRead]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExecuteRequestIn(BaseModel):
    method: str = Field(pattern="^(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)$")
    url: str = Field(min_length=1, max_length=8192)
    headers: dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    environment_id: Optional[UUID] = None
    saved_request_id: Optional[UUID] = None


class ExecutionOut(BaseModel):
    id: UUID
    outcome: str
    status_code: Optional[int]
    duration_ms: Optional[int]
    response_headers: dict[str, Any]
    response_body_excerpt: Optional[str]
    response_size_bytes: int
    url: str
    method: str
    started_at: datetime
    completed_at: datetime

    class Config:
        from_attributes = True
