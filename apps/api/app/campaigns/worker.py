from __future__ import annotations

import asyncio
import signal
import sys
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.analysis.assertions import evaluate_assertion
from app.analysis.classification import classify_from_execution
from app.campaigns.job_claim import claim_next_job, renew_lease
from app.campaigns.state_machine import is_terminal
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.security import decrypt_var_value
from app.db.models import (
    AssertionResult,
    Campaign,
    CampaignEvent,
    CampaignJob,
    EvidenceReference,
    Execution,
    Finding,
    Project,
    TestCase,
)
from app.db.session import SessionLocal
from app.execution.service import PreparedRequest, execute as run_request
from app.workspace.environments.service import resolve_variables

log = get_logger("campaign.worker")

STOP = asyncio.Event()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _add_event(db: Session, campaign_id: UUID, event_type: str, payload: dict) -> None:
    db.add(CampaignEvent(campaign_id=campaign_id, event_type=event_type, payload=payload, created_at=_utcnow()))


def _mark_state(db: Session, campaign: Campaign, new_state: str, *, failure_reason: str | None = None) -> None:
    campaign.state = new_state
    campaign.updated_at = _utcnow()
    if new_state in {"completed", "failed", "cancelled"}:
        campaign.completed_at = _utcnow()
    if failure_reason is not None:
        campaign.failure_reason = failure_reason


async def _run_one(job: CampaignJob, campaign: Campaign) -> None:
    db: Session = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == campaign.project_id).first()
        if project is None:
            _mark_state(db, campaign, "failed", failure_reason="project_missing")
            _add_event(db, campaign.id, "failed", {"reason": "project_missing"})
            db.commit()
            return
        if campaign.state == "queued":
            _mark_state(db, campaign, "running")
            campaign.started_at = _utcnow()
            _add_event(db, campaign.id, "claimed", {"worker": get_settings().worker_id})
            db.commit()
            db.refresh(campaign)

        while True:
            if STOP.is_set():
                return
            # Refresh job lease periodically.
            renew_lease(db, job.id, get_settings().worker_id)
            # Pick next test case that does not have a parent execution yet, respecting budget.
            remaining = campaign.budget_executions - campaign.executions_used
            if remaining <= 0:
                _mark_state(db, campaign, "completed")
                _add_event(db, campaign.id, "budget_exhausted", {"used": campaign.executions_used})
                db.commit()
                return

            # Already executed test cases
            executed_tc_ids = {
                r[0] for r in db.query(Execution.parent_test_case_id).filter(
                    Execution.parent_test_case_id.isnot(None), Execution.project_id == campaign.project_id
                ).all()
            }
            tc = (
                db.query(TestCase)
                .filter(TestCase.campaign_id == campaign.id)
                .filter(~TestCase.id.in_(executed_tc_ids) if executed_tc_ids else TestCase.id.isnot(None))
                .order_by(TestCase.created_at.asc())
                .first()
            )
            if tc is None:
                _mark_state(db, campaign, "completed")
                _add_event(db, campaign.id, "completed", {"used": campaign.executions_used})
                db.commit()
                return

            # Execute the test through the secure boundary (no env resolution for campaign tests
            # because they come from normalized specs and do not carry templating).
            req_def = tc.request_definition or {}
            pr = PreparedRequest(
                method=req_def.get("method", "GET"),
                url=req_def.get("url", ""),
                headers=req_def.get("headers") or {},
                body=req_def.get("body"),
                secret_values=[],
            )

            # We record an execution row before sending only as an in-flight marker? In this codebase
            # we record *after* send to avoid uncertain-outcome rows. If the process crashes exactly
            # between sending and recording, the target may have received the request, but we will
            # not record an execution id on the job (we do not set recovery_uncertain_execution_id
            # before having an execution id). This keeps DB-09 simple: we do not retry tests that
            # are not marked executed and we do not claim exactly-once.
            _add_event(db, campaign.id, "test_scheduled", {"test_case_id": str(tc.id), "kind": tc.kind})
            db.commit()
            result = await run_request(pr)

            ex = Execution(
                project_id=campaign.project_id,
                parent_test_case_id=tc.id,
                method=result.request_snapshot.get("method", "GET"),
                url=result.final_url or pr.url,
                request_snapshot=result.request_snapshot,
                outcome=result.outcome,
                status_code=result.status_code,
                duration_ms=result.duration_ms,
                response_headers=result.response_headers,
                response_body_excerpt=result.response_body_excerpt,
                response_size_bytes=result.response_size_bytes,
                transport_error=result.transport_error,
                started_at=result.started_at,
                completed_at=result.completed_at,
            )
            db.add(ex); db.flush()

            # Evaluate assertions if http_response
            any_fail = False
            for a in tc.assertions or []:
                ar_dict = evaluate_assertion(result, a)
                ar = AssertionResult(
                    execution_id=ex.id,
                    assertion_type=ar_dict["assertion_type"],
                    assertion_config=ar_dict["assertion_config"],
                    passed=ar_dict["passed"],
                    actual=ar_dict["actual"],
                    message=ar_dict["message"],
                    created_at=_utcnow(),
                )
                db.add(ar)
                if not ar_dict["passed"]:
                    any_fail = True

            # Evidence + findings
            findings = classify_from_execution(
                {"id": ex.id, "method": ex.method, "url": ex.url, "outcome": ex.outcome, "status_code": ex.status_code},
                [
                    {"id": None, "assertion_type": (tc.assertions[i]["type"] if i < len(tc.assertions) else "?"), "passed": True}  # placeholder; real results are above
                ],  # we replace below using the persisted ARs
                None,
            )
            # Use actual assertion results:
            db.flush()
            ars = db.query(AssertionResult).filter(AssertionResult.execution_id == ex.id).all()
            finding_payloads = classify_from_execution(
                {"id": ex.id, "method": ex.method, "url": ex.url, "outcome": ex.outcome, "status_code": ex.status_code},
                [{"id": ar.id, "assertion_type": ar.assertion_type, "passed": ar.passed, "message": ar.message} for ar in ars],
            )
            evidence_ids = []
            # Evidence for the request snapshot and response excerpt.
            ev_req = EvidenceReference(
                project_id=campaign.project_id,
                source_type="execution",
                source_id=ex.id,
                provenance="OBSERVED",
                excerpt={"method": ex.method, "url": ex.url, "request_snapshot": ex.request_snapshot},
                created_at=_utcnow(),
            )
            db.add(ev_req); db.flush(); evidence_ids.append(ev_req.id)
            ev_resp = EvidenceReference(
                project_id=campaign.project_id,
                source_type="execution",
                source_id=ex.id,
                provenance="OBSERVED",
                excerpt={
                    "status_code": ex.status_code,
                    "response_headers": ex.response_headers,
                    "body_excerpt": (ex.response_body_excerpt or "")[:2000],
                },
                created_at=_utcnow(),
            )
            db.add(ev_resp); db.flush(); evidence_ids.append(ev_resp.id)

            for fp in finding_payloads:
                f = Finding(
                    project_id=campaign.project_id,
                    campaign_id=campaign.id,
                    category=fp["category"],
                    machine_severity=fp["machine_severity"],
                    triage_status="new",
                    title=fp["title"],
                    summary=fp["summary"],
                    evidence_ids=evidence_ids,
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
                db.add(f)
                _add_event(db, campaign.id, "finding_created", {"category": fp["category"], "severity": fp["machine_severity"]})

            campaign.executions_used += 1
            _add_event(db, campaign.id, "execution_completed", {
                "execution_id": str(ex.id),
                "test_case_id": str(tc.id),
                "outcome": ex.outcome,
                "status_code": ex.status_code,
                "any_fail": any_fail,
            })
            db.commit()
            db.refresh(campaign)
    except Exception as exc:  # pragma: no cover
        log.exception("worker_error", error=str(exc))
        db.rollback()
        db2 = SessionLocal()
        try:
            c = db2.query(Campaign).filter(Campaign.id == campaign.id).first()
            if c and not is_terminal(c.state):
                _mark_state(db2, c, "failed", failure_reason=type(exc).__name__)
                _add_event(db2, c.id, "failed", {"reason": type(exc).__name__})
                db2.commit()
        finally:
            db2.close()
    finally:
        db.close()


async def _loop() -> None:
    log.info("worker_start", worker_id=get_settings().worker_id)
    while not STOP.is_set():
        db: Session = SessionLocal()
        try:
            claimed = claim_next_job(db, get_settings().worker_id)
        finally:
            db.close()
        if claimed is None:
            try:
                await asyncio.wait_for(STOP.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                continue
            return
        job, campaign = claimed
        await _run_one(job, campaign)


def main() -> None:
    configure_logging()
    loop = asyncio.new_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, STOP.set)
        except NotImplementedError:  # pragma: no cover
            pass
    try:
        loop.run_until_complete(_loop())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
