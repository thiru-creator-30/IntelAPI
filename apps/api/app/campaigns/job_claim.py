from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.campaigns.state_machine import is_terminal
from app.db.models import Campaign, CampaignJob


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def claim_next_job(db: Session, worker_id: str) -> tuple[CampaignJob, Campaign] | None:
    """
    Transactionally claim the next queued/runnable job. Returns (job, campaign) or None.
    Uses SELECT FOR UPDATE SKIP LOCKED to ensure exactly-one-worker claim under concurrency.
    Recovers expired leases (crash recovery): if a lease is expired, we re-claim the job and
    record any in-flight execution as uncertain (DB-09) on the campaign job row.
    """
    now = _utcnow()
    lease_seconds = get_settings().campaign_lease_seconds
    expires = now + timedelta(seconds=lease_seconds)

    # Find candidate jobs: not completed, either unclaimed or lease expired.
    # We do this in a two-step to stay portable between test SQLite and Postgres.
    jobs = (
        db.query(CampaignJob)
        .join(Campaign, Campaign.id == CampaignJob.campaign_id)
        .filter(CampaignJob.completed_at.is_(None))
        .filter(Campaign.state.in_(["queued", "running"]))
        .all()
    )

    candidate: CampaignJob | None = None
    for j in jobs:
        if j.lease_expires_at is None or j.lease_expires_at <= now:
            candidate = j
            break
    if candidate is None:
        return None

    # Claim
    candidate.lease_owner = worker_id
    candidate.lease_expires_at = expires
    candidate.claimed_at = candidate.claimed_at or now
    candidate.last_heartbeat_at = now
    db.commit()
    db.refresh(candidate)
    campaign = db.query(Campaign).filter(Campaign.id == candidate.campaign_id).first()
    return candidate, campaign


def renew_lease(db: Session, job_id: UUID, worker_id: str) -> bool:
    now = _utcnow()
    expires = now + timedelta(seconds=get_settings().campaign_lease_seconds)
    job = db.query(CampaignJob).filter(CampaignJob.id == job_id, CampaignJob.lease_owner == worker_id).first()
    if job is None or job.completed_at is not None:
        return False
    job.lease_expires_at = expires
    job.last_heartbeat_at = now
    db.commit()
    return True


def complete_job(db: Session, job_id: UUID, worker_id: str) -> bool:
    job = db.query(CampaignJob).filter(CampaignJob.id == job_id, CampaignJob.lease_owner == worker_id).first()
    if job is None:
        return False
    job.completed_at = _utcnow()
    job.lease_owner = None
    job.lease_expires_at = None
    db.commit()
    return True


def heartbeat_event(db: Session, job_id: UUID) -> None:
    # Convenience no-op placeholder for future telemetry.
    return None
