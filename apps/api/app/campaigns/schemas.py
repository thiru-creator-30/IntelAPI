from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_specification_id: Optional[UUID] = None
    source_operation_id: Optional[UUID] = None
    budget_executions: int = Field(default=200, ge=1, le=2000)


class CampaignRead(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    state: str
    budget_executions: int
    executions_used: int
    source_specification_id: Optional[UUID]
    source_operation_id: Optional[UUID]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    failure_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampaignReport(BaseModel):
    campaign: CampaignRead
    tests_total: int
    executions_total: int
    findings_total: int
    assertions_passed: int
    assertions_failed: int
    events: list[dict[str, Any]]
    partial: bool
