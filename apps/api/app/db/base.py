from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models here so Alembic autogenerate picks them up.
from app.db.models import (  # noqa: E402,F401
    ApiOperation,
    ApiSpecification,
    AssertionResult,
    Campaign,
    CampaignEvent,
    CampaignJob,
    Collection,
    Environment,
    EnvironmentVariable,
    EvidenceReference,
    Execution,
    Finding,
    HealthCheck,
    HealthCheckRun,
    KnowledgeFact,
    Project,
    SavedRequest,
    Session,
    TestCase,
    User,
)
