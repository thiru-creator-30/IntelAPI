# Implementation Status

**Baseline:** 2026-10-16
**Status owner:** Developer A (integration lead). This file is updated only from verified evidence (tests passing, CI green, E2E observed).

> Legend: ✅ implemented & verified · 🚧 partial / scaffolded · ⛔ not yet implemented

## Phase 0 — Contract freeze and repo hygiene
- [x] Canonical docs committed under `docs/`
- [x] Monorepo skeleton (`apps/api`, `apps/web`, `packages/contracts`, `scripts`, `.github/workflows`)
- [x] Root README and local runbook
- [x] Secret exclusion verified (`.env`, `*.local`, local DB volumes in `.gitignore`)

## Phase 1 — Persistence foundation & intelligence harness
- [x] FastAPI app scaffold, `/health/live` returns `{"status":"alive"}`; `/health/ready`
- [x] Structured error envelope and stable error codes
- [x] Pagination helpers
- [x] Secret-safe logging and request correlation IDs
- [x] React/Vite/TypeScript web scaffold with API client and error-envelope handling
- [x] Docker Compose (api / web / worker / db), Dockerfiles, `.env.example`
- [x] CI workflow (backend tests, frontend lint/typecheck/test/build, generated-types drift)
- [x] OpenAPI export + generated TypeScript types script
- [x] SQLAlchemy 2.x base / session wiring; Alembic setup; initial baseline migration
- [x] Users / sessions (hashed opaque sessions, Google `sub` identity, server-side revocation)
- [x] Project CRUD / archive / overview + server-side ownership dependency
- [x] OpenAPI parser / normalizer / operation extraction (pure; no network)
- [x] Knowledge facts with `DECLARED`/`EXTRACTED`/`OBSERVED`/`INFERRED` provenance

## Phase 2 — Workspace + safe execution + API understanding
- [x] Shared secure outbound execution: scheme allowlist, private-IP/DNS/redirect/DNS-rebinding defenses, timeouts, size caps, secret redaction
- [x] Collections / saved requests / environments (encrypted secret values at rest, never returned in plaintext)
- [x] Execution history + immutable redacted snapshots (DB-04)
- [x] `POST /requests/execute` (single secure boundary)
- [x] Specification import (file + safe URL, bounded JSONB, hash/version metadata DB-03)
- [x] Operations listing + `POST /operations/{id}/candidates/preview` (non-persisting)
- [x] Deterministic candidate generator (positive / negative / boundary / schema / workflow) + validation + dedup
- [x] Optional LLM provider-neutral adapter (fail-closed without credentials)

## Phase 3 — Assertions / health checks / findings / evidence
- [x] Fixed five assertion types (status, latency, JSON path/value, header, schema)
- [x] Evidence-based finding classification (no auto "vulnerability" claims)
- [x] Health checks CRUD / run / run history
- [x] Evidence references with source relationship, provenance, bounded redacted excerpts (DB-10)
- [x] Findings CRUD (PATCH limited to user-managed triage fields)
- [x] Project overview aggregates

## Phase 4 — Durable campaigns & adaptive loop
- [x] Campaign state machine (`queued`/`running`/`completed`/`failed`/`cancelled`)
- [x] Durable `campaign_jobs` with PostgreSQL row-lock claim + lease + recovery (DB-08)
- [x] Atomic create-job-event returns 202 Accepted; append-only events (DB-06)
- [x] Separate worker process (shared orchestration, no second HTTP transport)
- [x] Cancel idempotent; budget exhaustion → `completed` + `budget_exhausted` event
- [x] Uncertain post-crash outcomes recorded, not blindly retried (DB-09)
- [x] Campaign tests / executions / events / partial+final reports
- [x] Adaptive scoring, follow-up selection, explainable rationale

## Phase 5 — Frontend workflows
- [x] Auth / session UX (Google sign-in, logout, current user)
- [x] Project shell + overview
- [x] API Workspace (editor / execute / response / collections / environments / history)
- [x] API Explorer (OpenAPI import, normalized operations, candidate preview)
- [x] Health Checks (definition / run / history)
- [x] Test Campaigns (create / progress / events / cancel / tests / executions / report)
- [x] Findings & Evidence (list / detail / triage)
- [x] Generated TypeScript types wired into API client; drift check in CI

## Phase 6 — Hardening & release
- [ ] Full E2E flows verified against a live Compose stack (manual verification required)
- [x] Security regression suite (SSRF/DNS/redirect/rebinding/redaction)
- [x] Migration from empty DB tested (`alembic upgrade head` on fresh Postgres)
- [ ] Production deployment checklist (TLS cookie enforcement, CORS allow-list, secrets provisioning)
