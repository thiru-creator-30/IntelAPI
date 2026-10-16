from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    google_sub: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(default="")
    display_name: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(unique=True, index=True)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    user_agent: Mapped[str | None] = mapped_column(nullable=True)
    ip: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class SavedRequest(Base):
    __tablename__ = "saved_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    collection_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("collections.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str]
    method: Mapped[str] = mapped_column(default="GET")
    url: Mapped[str]
    headers: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    body: Mapped[str | None] = mapped_column(nullable=True)
    environment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("environments.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Environment(Base):
    __tablename__ = "environments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    variables: Mapped[list["EnvironmentVariable"]] = relationship(
        back_populates="environment", cascade="all, delete-orphan"
    )


class EnvironmentVariable(Base):
    __tablename__ = "environment_variables"
    __table_args__ = (UniqueConstraint("environment_id", "name", name="uq_env_var_env_name"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    environment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]
    value_enc: Mapped[bytes]
    is_secret: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    environment: Mapped[Environment] = relationship(back_populates="variables")


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    saved_request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("saved_requests.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_check_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("health_check_runs.id", ondelete="SET NULL"), nullable=True)
    parent_test_case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True, index=True)
    method: Mapped[str]
    url: Mapped[str]
    request_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    outcome: Mapped[str]
    status_code: Mapped[int | None] = mapped_column(nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    response_headers: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    response_body_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    transport_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    completed_at: Mapped[datetime] = mapped_column(default=utcnow)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AssertionResult(Base):
    __tablename__ = "assertion_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("executions.id", ondelete="CASCADE"), index=True)
    assertion_type: Mapped[str]
    assertion_config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    passed: Mapped[bool]
    actual: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    message: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ApiSpecification(Base):
    __tablename__ = "api_specifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str]
    source_url: Mapped[str | None] = mapped_column(nullable=True)
    title: Mapped[str | None] = mapped_column(nullable=True)
    version: Mapped[str | None] = mapped_column(nullable=True)
    spec_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    content_hash: Mapped[str] = mapped_column(index=True)
    spec_format: Mapped[str] = mapped_column(default="openapi_3")
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class ApiOperation(Base):
    __tablename__ = "api_operations"
    __table_args__ = (UniqueConstraint("specification_id", "method", "path", name="uq_op_spec_method_path"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    specification_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_specifications.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    method: Mapped[str]
    path: Mapped[str]
    operation_id: Mapped[str | None] = mapped_column(nullable=True)
    summary: Mapped[str | None] = mapped_column(nullable=True)
    normalized: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class KnowledgeFact(Base):
    __tablename__ = "knowledge_facts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    provenance: Mapped[str]
    fact_type: Mapped[str]
    subject_type: Mapped[str | None] = mapped_column(nullable=True)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class HealthCheck(Base):
    __tablename__ = "health_checks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]
    request_definition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    assertions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class HealthCheckRun(Base):
    __tablename__ = "health_check_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    health_check_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("health_checks.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    outcome: Mapped[str]
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("executions.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]
    source_specification_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("api_specifications.id", ondelete="SET NULL"), nullable=True)
    source_operation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("api_operations.id", ondelete="SET NULL"), nullable=True)
    state: Mapped[str] = mapped_column(default="queued", index=True)
    budget_executions: Mapped[int] = mapped_column(default=200)
    executions_used: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class CampaignJob(Base):
    __tablename__ = "campaign_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), unique=True, index=True)
    lease_owner: Mapped[str | None] = mapped_column(nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(nullable=True)
    next_test_cursor: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    recovery_uncertain_execution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("executions.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class CampaignEvent(Base):
    __tablename__ = "campaign_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str]
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    source_operation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("api_operations.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str]
    request_definition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    assertions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class EvidenceReference(Base):
    __tablename__ = "evidence_references"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str]
    source_id: Mapped[uuid.UUID]
    provenance: Mapped[str]
    excerpt: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)
    category: Mapped[str]
    machine_severity: Mapped[str] = mapped_column(default="info")
    triage_status: Mapped[str] = mapped_column(default="new")
    user_severity: Mapped[str | None] = mapped_column(nullable=True)
    user_notes: Mapped[str | None] = mapped_column(nullable=True)
    title: Mapped[str]
    summary: Mapped[str]
    evidence_ids: Mapped[list[uuid.UUID]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
