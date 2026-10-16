# IntelAPI — Repository Audit & Implementation Plan

**Audit date:** 2026-10-16
**Auditor:** Senior engineer (Agent Mode session, branch `arena/60d8618c-intelapi`)
**Scope:** Non-destructive inspection only. No dependencies installed, no files written except this report. No database/auth work performed, per your instruction.

---

## 1. Repository state (verified, not assumed)

| Check | Command | Result |
|---|---|---|
| Current branch | `git branch --show-current` | `arena/60d8618c-intelapi` |
| Current commit (HEAD) | `git log --oneline -5` | `7f34eee Initial commit` (single commit) |
| `main` ref | `git show origin/main --stat` | Same commit `7f34eee` — branch is even with origin/main |
| Working tree | `git status --short` | Clean (no modified, staged, or untracked files) |
| Tracked files | `git ls-files` | **Only `.gitignore`** (220 lines, generic Python/Node template) |
| Remotes | `git remote -v` | `origin https://github.com/thiru-creator-30/IntelAPI.git` |

### 1.1 Filesystem layout (actual)

```
IntelAPI/
├── .git/            # standard git metadata
└── .gitignore       # generic Python/Node ignore; no project-specific rules yet
```

There is **no** `docs/`, `apps/`, `packages/`, `scripts/`, `alembic/`, `tests/`, `web/`, `frontend/`, `backend/`, or `api/` directory. There are no manifests: no `pyproject.toml`, `requirements*.txt`, `package.json`, `pnpm-workspace.yaml`, `turbo.json`, `Dockerfile`, `docker-compose*.yml`, `Makefile`, `.github/workflows/`, `.env.example`, or `README.md`.

### 1.2 Local toolchain observed (non-destructive probe; nothing installed)

| Tool | Status |
|---|---|
| `python3` (3.11.2), `node` (22.22.3), `npm` | present |
| `docker`, `docker-compose` | **not installed** in sandbox |
| `psql`, `alembic`, `pytest` | **not installed** in sandbox |
| FastAPI / SQLAlchemy / Vite / TypeScript | cannot be probed — no manifests and no install performed |
| PostgreSQL server | not reachable from sandbox (and not required to be) |

> Because the sandbox lacks Docker and the project has no dependency manifests yet, Compose-up, pytest, Alembic, frontend build, and CI checks **cannot be executed** in this session. Per standing restrictions (no installs, no DB/auth touching), I did not attempt to work around this. All "passed" claims below require the gate to have actually run.

---

## 2. Documentation index reconciliation

The seven canonical documents named in your brief were checked against the repo **and** the attachments you supplied:

| Canonical document | Path per docs index | In repo? | Attachment? |
|---|---|---|---|
| `SOURCE_OF_TRUTH.md` | `docs/SOURCE_OF_TRUTH.md` | **Missing** | ✅ provided (`/tmp/arena-coding-uploads/SOURCE_OF_TRUTH.md`, v1.0, 2026-10-16) |
| `api_contracts.md` | `docs/api_contracts.md` | **Missing** | **Not provided** |
| `DATABASE_SCHEMA.md` | `docs/DATABASE_SCHEMA.md` | **Missing** | **Not provided** |
| `IMPLEMENTATION_PLAN_AND_OWNERSHIP.md` | `docs/IMPLEMENTATION_PLAN_AND_OWNERSHIP.md` | **Missing** | ✅ provided (`/tmp/arena-coding-uploads/IMPLEMENTATION_PLAN_AND_OWNERSHIP.md`, v1.0) |
| `IMPLEMENTATION_STATUS.md` | `docs/IMPLEMENTATION_STATUS.md` | **Missing** | **Not provided** |
| `LOCAL_RUNBOOK.md` | `docs/LOCAL_RUNBOOK.md` | **Missing** | **Not provided** |
| `README.md` | `docs/README.md` (also project root convention) | **Missing** | **Not provided** |

### Discrepancies vs. the plan document

1. **Phase 0 ("Commit the four-document canonical set") has not been executed.** The two attached documents live only in the upload staging area (`/tmp/arena-coding-uploads/`), not in the repository, and the other five documents do not exist anywhere.
2. **`docs/README.md` is an unusual location.** Conventions expect a top-level `README.md`. The ownership matrix lists `README.md` at project root as A-owned. Recommend a top-level `README.md` that points into `docs/` rather than burying the entry point under `docs/`.
3. **No `.env.example`, no `compose.yml`, no CI workflows** exist despite being referenced by the plan/ownership matrix.

**Smallest correction I propose:**
- Create `docs/` directory and commit both attached documents under their canonical paths.
- Add stub placeholders for the remaining five docs with a clear "Not yet drafted — see Source of Truth §N for authoritative contract" header, so nothing drifts silently.
- Add a root `README.md` that points to `docs/SOURCE_OF_TRUTH.md`, `docs/IMPLEMENTATION_PLAN_AND_OWNERSHIP.md`, and (when written) `docs/LOCAL_RUNBOOK.md`.

This is flagged as Decision #1 (see §8).

---

## 3. Non-destructive checks that were run, and results

| # | Command | Outcome | Meaning |
|---|---|---|---|
| C1 | `git branch --show-current` | `arena/60d8618c-intelapi` | On the assigned working branch. |
| C2 | `git status --short` | empty | Working tree clean; nothing to stash or overwrite. |
| C3 | `git ls-files` | `.gitignore` only | Repository is pre-scaffold. |
| C4 | `git log --oneline -5` | single initial commit | No history of implementation exists to contradict docs. |
| C5 | `git diff main arena/... --stat` | empty | The working branch has no commits ahead of `main` — no WIP to preserve. |
| C6 | `find . -type f -not -path './.git/*'` | only `.gitignore` | Confirms no hidden source/config files. |
| C7 | Tool probes (`which python3 node docker ...`) | Python/Node present; Docker/psql/alembic/pytest absent | Local environment check only; not a defect of the repo. |
| C8 | `git ls-tree -r HEAD` | same as C3 | No surprise submodules, LFS, or binary blobs. |

### Checks that cannot run (and why)

- `docker compose up/build`: docker not installed in sandbox, and no Compose file exists.
- `pytest`, `ruff`, `mypy`: no Python source, no `pyproject.toml`, not installed per restriction #7 ("Do not install or upgrade dependencies during this audit").
- `npm install` / `npm run build` / `tsc --noEmit` / `vitest`: no `package.json`, not installed per restriction.
- `alembic current` / `alembic history`: no `alembic.ini`, no `alembic/versions/`, not installed per restriction.
- `psql` connectivity / migration test: no DB, no `psql` client, and you asked not to touch database work in this session.
- `gh workflow run` / CI: no `.github/workflows/` exists.
- OpenAPI / generated TypeScript drift check: no FastAPI app, no OpenAPI, no `apps/web`.

---

## 4. Evidence-based feature matrix (Implemented / Partial / Missing)

Every feature in the canonical inventory (SoT §6, §8) is evaluated only against the evidence in the repository — **not against the plan documents**.

### 4.1 Project foundation & operations

| Area | Status | Evidence |
|---|---|---|
| Monorepo directory skeleton (`apps/api`, `apps/web`, `packages/contracts`) | **Missing** | No such directories exist. |
| Python project manifest / dependency lock | **Missing** | No `pyproject.toml`, `requirements*.txt`, `uv.lock`, `poetry.lock`. |
| Node/frontend manifest / workspace config | **Missing** | No `package.json`, `pnpm-lock.yaml`, `package-lock.json`, `turbo.json`. |
| Docker Compose local orchestration | **Missing** | No `compose*.yml`. |
| Dockerfiles (api, web, worker) | **Missing** | No `Dockerfile*`. |
| `.env.example` | **Missing** | Not present; `.env` is correctly in `.gitignore`. |
| CI workflows (lint/test/build/migration/type-drift) | **Missing** | No `.github/workflows/`. |
| Top-level README / docs directory | **Missing** | Not present. |
| Root FastAPI app (`apps/api/app/main.py`, `api.py`) | **Missing** | Not present. |
| Health probes (`GET /health/live` → `{"status":"alive"}`, `/health/ready`) | **Missing** | No FastAPI app. Note: SoT §12.1 says canonical response is `"alive"`. |
| Structured error envelope / error codes | **Missing** | No `core/errors.py`. |
| Pagination helper | **Missing** | No `core/pagination.py`. |
| Structured logging / secret-safe logging | **Missing** | No `core/logging.py`. |
| Configuration / settings loader | **Missing** | No `core/config.py`. |
| Alembic setup (`alembic.ini`, `env.py`, `versions/`) | **Missing** | No Alembic directory; no initial revision. *(De-prioritized per your "no DB/auth" note; still a foundation prerequisite A owns.)* |

### 4.2 Identity & projects (Auth) — *explicitly out of scope per your note*

All routes under `/api/v1/auth/*`, Google ID-token verification, hashed opaque sessions, CSRF/cookies, project CRUD/archive/ownership, project overview — **Missing** (entire `auth/` and `projects/` packages absent). Recorded as prerequisite foundation work owned by A, but not expanded in this plan because you asked to not touch DB/auth.

### 4.3 API Workspace (collections, requests, environments, execution, history)

| Area | Status | Evidence |
|---|---|---|
| Collections & saved-requests models/routes | **Missing** | No `workspace/` directory. |
| Environment + secret encryption + resolver | **Missing** | No `workspace/environments/`. Decision DB-02 requires server-side encryption of secrets. |
| Shared outbound execution service (HTTPX) | **Missing** | No `execution/` directory. This is **security-critical (A-owned)** and a hard blocker for almost every other feature. |
| SSRF/private-IP/DNS-rebinding/redirect revalidation | **Missing** | No policy module — the single most important security gap. |
| Request/response size caps, timeouts, budgets, redirect limit | **Missing** | No execution policy config. |
| Header/body/secret redaction for logs/snapshots/evidence | **Missing** | No redactor. |
| Immutable resolved-execution snapshot (SoT DB-04) | **Missing** | No execution model. |
| History listing + execution detail | **Missing** | No `history/` directory. |
| `POST /requests/execute` + response viewer contract | **Missing** | No routes. |

### 4.4 API understanding / Explorer / OpenAPI (B-owned behind A's safe boundary)

| Area | Status | Evidence |
|---|---|---|
| OpenAPI parser (JSON/YAML, size/version validation) | **Missing** | No `api_understanding/`. |
| Normalizer → `NormalizedOperation` | **Missing** | No module; DTO not yet agreed in code. |
| Operation extraction & schema-ref resolution | **Missing** | Absent. |
| Knowledge facts with provenance (DECLARED/EXTRACTED/OBSERVED/INFERRED) | **Missing** | No `knowledge/`. |
| File upload spec import | **Missing** | No route, no storage (JSONB, hash/version metadata per DB-03). |
| URL spec import via safe fetch boundary | **Missing** | Blocked on shared execution service (A-owned). SoT §6.3: parser must NOT do its own networking. |
| Candidate preview endpoint (`POST /operations/{id}/candidates/preview`, non-persisting) | **Missing** | No route, no preview service. |

### 4.5 Test generation & intelligence (B-owned)

| Area | Status | Evidence |
|---|---|---|
| Deterministic candidate generator (positive/negative/boundary/schema/workflow) | **Missing** | No `test_generation/`. |
| Candidate validation and deduplication | **Missing** | Absent. |
| LLM provider-neutral interface + adapter (optional) | **Missing** | No `integrations/llm/`. |
| Deterministic fallback without LLM credentials | **Missing** (N/A until generator exists). | — |

### 4.6 Execution analysis / assertions / classification (B-owned)

| Area | Status | Evidence |
|---|---|---|
| Five fixed assertion types (status, latency, JSON path/value, header, schema) | **Missing** | No `analysis/assertions.py`. |
| Schema comparison engine | **Missing** | Absent. |
| Evidence-based finding classification (no automatic defect claims) | **Missing** | No `analysis/classification`; no `findings/` persistence. |
| Adaptive scoring / next-test selection / rationale | **Missing** | No `adaptive/`. |

### 4.7 Health checks (A-owned persistence + B-owned assertion semantics)

| Area | Status | Evidence |
|---|---|---|
| Health-check CRUD, run endpoint, run history | **Missing** | No `health_checks/`. |
| Integration of five fixed assertion types into runs | **Missing** | Blocked on assertions and execution service. |

### 4.8 Campaigns / durable jobs (A-owned)

| Area | Status | Evidence |
|---|---|---|
| Campaign state machine (`queued/running/completed/failed/cancelled`) | **Missing** | No `campaigns/`. |
| Durable `campaign_jobs` with row-lock claim + lease + recovery (DB-08) | **Missing** | Absent. |
| Separate worker process (shared orchestration, no second HTTP transport) | **Missing** | No worker entrypoint; no Compose service for it. |
| Atomic create-job-event on campaign creation (returns 202 Accepted) | **Missing** | Absent. |
| Cancel idempotency (terminal stays terminal, returns 200) | **Missing** | Absent. |
| "Retry only pre-send failures; uncertain post-crash outcome recorded, not retried" (DB-09) | **Missing** | Critical correctness invariant; not implemented. |
| Budget exhaustion → `completed` + `budget_exhausted` event | **Missing** | Absent. |
| Events timeline, tests list, executions list, partial/final report | **Missing** | Absent. |

### 4.9 Findings, evidence, reports, overview (A-owned persistence + B-owned classifier)

| Area | Status | Evidence |
|---|---|---|
| Findings list/detail/PATCH (user triage fields only) | **Missing** | No `findings/`. |
| Evidence references with source relationship + provenance + bounded redacted excerpts (DB-10) | **Missing** | No `evidence/`. |
| Campaign reports / project overview aggregates | **Missing** | No `reports/`, `overview/`. |
| Append-only `campaign_events` (DB-06) | **Missing** | Absent. |

### 4.10 Frontend (`apps/web`, A-owned)

| Area | Status | Evidence |
|---|---|---|
| Vite + React + TS scaffold | **Missing** | No `apps/web`. |
| Auth/session flow, project shell/overview | **Missing** | Absent. |
| Workspace, Explorer preview, Health checks, Campaigns, Findings UI | **Missing** | Absent. |
| Generated TypeScript API types at `apps/web/src/services/generated/api-schema.ts` | **Missing** | No generator scripts; no `scripts/export_openapi.py` or `scripts/generate_api_types.py`. |
| Frontend tests, E2E tests | **Missing** | No test infra. |

### 4.11 Tests

**Entirely missing** — no `tests/`, no conftest, no fixtures, no security test suite for SSRF/DNS/redirects/redaction, no migration-from-empty test, no frontend/E2E tests.

---

## 5. Blocking & high-priority risks (evidence-backed)

Ordered by severity.

1. **No shared secure outbound execution service exists (SSRF / open-proxy risk).** Every feature that touches the network (request sending, health-check runs, campaign execution, URL-based OpenAPI import) must flow through one A-owned boundary that enforces scheme allowlist, private/loopback/link-local/multicast/reserved IP rejection, pre-connect DNS validation, redirect revalidation, DNS-rebinding defenses, timeouts, size caps, redirect limits, concurrency caps, header/secret redaction, and `TARGET_BLOCKED`/`TARGET_TIMEOUT` errors. Because nothing exists yet, any parallel work that performs HTTP requests (e.g., an OpenAPI URL importer or campaign worker) will silently invent a second HTTP client and reintroduce SSRF. **This is the single highest-risk item.**
2. **Repository is pre-scaffold — no dependency manifests, no lockfiles, no Docker/CI.** There is nothing for CI to run and nothing for a second developer to build against. Phase 0 has not been executed.
3. **Canonical documentation set incomplete and not committed.** SoT and the Plan exist as uploads only; the five other required docs are absent. This creates drift risk the moment code is written.
4. **No Alembic revision graph exists.** The plan calls for groups `0002_identity_projects.py` through `0006_findings_evidence.py` but there is no `0001` baseline. A real initial revision (e.g., `0001_init`) must exist before any of those numbered groups are added, and numbering must follow actual ancestry, not the plan's suggestive names. *(Foundation / A-owned; de-prioritized here per your "no DB/auth" instruction, but noted as a hard prerequisite.)*
5. **No project ownership enforcement exists.** SoT §3.1 is clear: every query must enforce project ownership, frontend route guards are not authorization. Until A implements the ownership dependency, any data layer risks cross-tenant access. *(De-prioritized per your note.)*
6. **No secret redaction / encryption exists.** Environment secrets must be encrypted at rest (DB-02) and never appear in DTOs/logs/snapshots/evidence. Without the A-owned redactor, B's intelligence modules cannot safely log or surface evidence.
7. **Uncertain-execution-outcome handling not yet designed.** DB-09 is easy to get wrong. The worker must not retry a request whose send state is ambiguous after a crash. Implementing campaigns without this designed up front will produce duplicate target calls.
8. **Candidate preview non-persistence contract is easy to violate.** The preview endpoint must never write candidates/test_cases. Needs explicit routing + a service boundary in front of any candidate generator B writes.
9. **Liveness response contract subtlety.** SoT §12.1 canonizes existing `{"status":"alive"}` (not `"ok"`). When the FastAPI app is scaffolded, this must match exactly — flagged so it isn't "fixed" to `"ok"` by mistake.
10. **Documentation path oddity: `docs/README.md`.** This will confuse contributors; root `README.md` is the conventional entry point. (Small correction, not a technical risk.)
11. **Environment mismatch in sandbox.** Docker, psql, alembic, pytest unavailable locally for this audit. Any "it works on my machine" claim will need CI verification — make CI the source of truth early.

---

## 6. Dependency-ordered implementation backlog (split into reviewable PRs)

Principles applied:
- Vertical slices where possible; never "generate all planned files."
- One owner per PR; cross-owner PRs get both reviews plus A's integration approval.
- Scope bounded so each PR is independently reviewable.
- DB and Auth work are listed with a note honoring your request not to start them in this session — they remain prerequisite foundation (A-owned) and I've marked them as "pre-MVP foundation (deferred by request)" rather than expanding them into tasks for this round.
- Security-critical items (outbound execution + policy) come before any feature that touches the network.
- PR sequence respects the ownership matrix and the phase gates in the plan doc.

> Legend: **[A]** Developer A · **[B]** Developer B · **[A→review]** B-authored but A must approve protected integration points.

### PR-0 — Phase 0: docs committed & repo skeleton (A)
**Owner:** A
**Scope:**
- Create `docs/` directory; commit the two attached canonical docs verbatim under `docs/SOURCE_OF_TRUTH.md` and `docs/IMPLEMENTATION_PLAN_AND_OWNERSHIP.md`.
- Create stubs for `docs/api_contracts.md`, `docs/DATABASE_SCHEMA.md`, `docs/IMPLEMENTATION_STATUS.md`, `docs/LOCAL_RUNBOOK.md`, each pointing to the authoritative SoT section and marked "Draft, not yet normative".
- Add top-level `README.md` pointing to docs.
- Add minimal repo skeleton directories **without placeholder source files**: `apps/api/app/`, `apps/web/src/`, `packages/contracts/`, `scripts/`, `.github/workflows/`, `apps/api/tests/`.
- Add `.gitignore` extensions for project-specific artifacts (alembic `versions/__pycache__`, node_modules cross-workspace, dist/build, `.env`, `.env.*` except `.env.example`, pgdata, IDE dirs).
**Prereqs:** none.
**Files:** `docs/**`, `README.md`, `.gitignore`, empty directory markers (`.gitkeep` where needed).
**Tests:** `git ls-files | grep docs/` confirms docs present; no code tests yet.
**Acceptance:** docs committed on a feature branch; README renders; no secrets or empty placeholder code added.
**Separate PR:** yes — this is a docs/skeleton PR with no functional code.

### PR-1 — Phase 1a: Python project scaffold + FastAPI app skeleton + /health/live (A)
**Owner:** A
**Scope:**
- `apps/api/pyproject.toml` (FastAPI, Uvicorn, Pydantic v2, HTTPX, SQLAlchemy 2.x, Alembic, structured logging, pytest dependencies pinned) + lockfile.
- `apps/api/app/main.py`, `apps/api/app/api.py`, `apps/api/app/core/{config,errors,logging,pagination}.py`.
- Structured error envelope and the 8 stable error codes from SoT §5.2.
- `GET /health/live` returning `{"status":"alive"}` (matching SoT §12.1) and `GET /health/ready` (stub → 503 until DB ready in later PR).
- Router registration skeleton at `/api/v1` prefix.
- Request ID / correlation ID middleware; secret-safe logging config (authorization headers/cookies redacted at log-filter level).
**Prereqs:** PR-0.
**Files:** `apps/api/**` (excluding auth/db modules), `apps/api/tests/test_health.py`, `apps/api/tests/test_errors.py`.
**Tests:** pytest unit tests for liveness response body exactly `{"status":"alive"}`, error envelope shape, pagination validation (negative/oversized limit).
**Acceptance:** `uvicorn app.main:app` boots; `/health/live` returns exact body; `/api/v1` returns 404 with structured error; tests pass; no DB required to boot.
**Separate PR:** yes.

### PR-2 — Phase 1b: Node/Vite/React/TS frontend scaffold (A)
**Owner:** A
**Owner:** A (B may provide UI feedback, not edit)
**Scope:**
- Root workspace: `pnpm-workspace.yaml` (or npm workspaces — decision needed, see §8) + root `package.json`.
- `apps/web/package.json`: React 18, Vite, TypeScript, a test runner (Vitest), ESLint, API client (fetch wrapper with error-envelope handling).
- Minimal `apps/web/src/main.tsx`, router skeleton with auth-guard stub (no real auth), ErrorBoundary, loading/empty/error UI primitives.
- Proxy `/api/v1` → `http://api:8000` in Vite dev config for Compose preview; bind dev server to `0.0.0.0` and permit the e2b preview host (per sandbox requirements if surfaced).
**Prereqs:** PR-0 (PR-1 helpful but not strictly dependent).
**Files:** `package.json`, `pnpm-lock.yaml` (or `package-lock.json`), `apps/web/**`, `apps/web/src/services/api-client.ts`.
**Tests:** `npm run typecheck`, `npm run lint`, `npm run test` (basic render/smoke), `npm run build`.
**Acceptance:** Vite dev server boots against a stub backend; typecheck/build are green; no demo fixtures that masquerade as real persisted data.
**Separate PR:** yes.

### PR-3 — Phase 1c: Docker Compose + CI baseline (A)
**Owner:** A
**Scope:**
- `Dockerfile.api`, `Dockerfile.web` (multi-stage), `Dockerfile.worker` (initially identical base to api).
- `compose.yml` with services: `api`, `web`, `postgres` (volume-mounted, password via `.env.example` — defaults must be non-production and clearly labeled). Worker service added but initially a no-op loop or wait until PR-11.
- `.env.example` with every documented setting and safe local defaults.
- `.github/workflows/ci.yml`: backend lint+test (fast → no DB), frontend lint+typecheck+test+build. Migration/generated-type checks added once Alembic and scripts exist.
- `scripts/export_openapi.py` (initially dumps FastAPI schema to `apps/api/openapi.json`) and `scripts/generate_api_types.py` (initially stubbed; enabled in CI once web can consume it).
**Prereqs:** PR-1, PR-2.
**Files:** `Dockerfile*`, `compose.yml`, `.env.example`, `.github/workflows/ci.yml`, `scripts/**`.
**Tests:** `docker compose config` validates; CI runs on PR; no secret values in repo; `.env` is gitignored.
**Acceptance:** A new contributor can `cp .env.example .env && docker compose up --build` and reach the API health endpoint and web UI; CI is green on the branch.
**Separate PR:** yes.

### PR-4 — Phase 2a: Secure outbound execution service (SSRF policy + HTTPX transport + redaction) (A)
**Owner:** A  *(security-critical; B must not directly edit)*
**Scope:**
- New package `apps/api/app/execution/`: `policy.py`, `transport.py`, `redactor.py`, `service.py`, `models.py` (for `ExecutionResult` DTO, agreed jointly).
- Policy enforces: scheme allowlist (http/https), private/loopback/link-local/multicast/reserved IP rejection, pre-connect DNS resolution of every address, redirect revalidation (each hop re-checked against policy, DNS re-resolved), DNS-rebinding defense (transport binds to the validated IP set), connect/read/total timeouts, request/response size caps, max redirects, per-execution concurrency.
- Redactor strips `Authorization`, `Cookie`, `Set-Cookie`, configured secret patterns, and environment secret values from captured snapshots, logs, and evidence excerpts; returns a redacted-safe view.
- Stable error mapping: policy rejection → `TARGET_BLOCKED`, timeout → `TARGET_TIMEOUT`, oversize → `response_too_large`, etc. No internal network details leak.
- **Must** implement a single injected HTTPX client/transport; no other module in the repo is allowed to import `httpx.AsyncClient` directly (enforced by code-review rule + a simple import-lint test).
**Prereqs:** PR-1 (needs FastAPI app + config + errors).
**Files:** `apps/api/app/execution/**`, `apps/api/tests/security/test_target_policy.py`, `tests/security/test_dns_rebinding.py`, `tests/security/test_redirects.py`, `tests/security/test_redaction.py`.
**Tests (all required before merge):**
- SSRF test battery: loopback (`127.0.0.1`, `::1`, `0.0.0.0`), RFC1918 ranges (`10/8`, `172.16/12`, `192.168/16`), link-local (`169.254/169`), multicast, CGNAT (`100.64/10`), IPv6 ULA, cloud-metadata IPs (`169.254.169.254`, `fd00:ec2::254`, GCP/Azure equivalents), `file://` scheme.
- DNS test: hostname that resolves to both a public and a private IP must be rejected if any resolved IP is blocked (fail closed).
- Redirect test: redirect to blocked IP is rejected at hop, not after connection; redirect to loopback via meta/3xx blocked; cross-protocol redirect blocked; redirect chain over limit rejected.
- DNS rebinding test: the IP actually connected to is the validated IP (i.e., transport is wired to connect to a pre-resolved IP while sending the correct Host header — this is the rebinding defense; describe the approach in code comments and test by forcing a second resolution to return a different IP).
- Timeouts, oversize responses, header/body redaction cases; secret-redaction: configured secret substring never appears in captured snapshot or logs.
**Acceptance:** security test suite passes; no other module imports `httpx.AsyncClient` (import-lint test); `ExecutionResult` DTO agreed in a short `packages/contracts/execution.md` note; TARGET_BLOCKED/TARGET_TIMEOUT responses contain no host/IP diagnostics.
**Separate PR:** yes. This is the security foundation and should be reviewed carefully.

### PR-5 — Phase 2b: OpenAPI parser, normalizer, operation extraction (B, A→review on DTOs)
**Owner:** B
**Scope:**
- New pure-Python package (no I/O) `apps/api/app/api_understanding/`: `parser.py`, `normalizer.py`, `operations.py`, `errors.py`.
- Accepts raw bytes (JSON or YAML) and a size limit; rejects unsupported Swagger 1.x/2.0 gracefully with `VALIDATION_ERROR`; enforces size cap.
- Produces `NormalizedOperation` objects (schema to be agreed jointly and recorded in `packages/contracts/` before merge — see §4 of plan doc).
- Dereferences local `$ref`s safely (no network, no remote `$ref` fetch — return an explicit validation error on remote refs).
- Deterministic operation IDs; stable sorting.
- Unit tests for malformed/edge-case specs: empty, invalid JSON, invalid YAML, circular refs, giant schema (size cap), remote refs, path parameters with no schema, non-JSON bodies, servers with variables, etc.
**Prereqs:** PR-1 (Pydantic/DTOs only — no DB). Does **not** depend on execution service (parser is pure).
**Files:** `apps/api/app/api_understanding/**`, `apps/api/tests/api_understanding/**`, `packages/contracts/normalized_operation.md`.
**Tests:** unit tests only, no network; fixtures of malformed/edge-case specs.
**Acceptance:** Parser returns deterministic `NormalizedOperation` output across runs on the same input; remote `$ref` is rejected with a clear validation error (never fetched); size cap enforced; no `httpx` import anywhere in this package.
**Separate PR:** yes.

### PR-6 — Phase 2c: Knowledge facts + provenance (B, A→review on persistence contract)
**Owner:** B
**Scope:**
- `apps/api/app/knowledge/` pure module: fact types tagged `DECLARED` (from spec), `EXTRACTED` (from normalizer), `OBSERVED` (from execution — stub interface only), `INFERRED` (from analysis).
- Facts link to a source (spec/operation/execution/assertion) by ID; no persistence in this PR (only domain objects).
- Unit tests for provenance and stable fact IDs.
**Prereqs:** PR-5.
**Files:** `apps/api/app/knowledge/**`, `apps/api/tests/knowledge/**`.
**Tests:** pure unit tests.
**Acceptance:** Facts carry provenance and source references; no direct DB or HTTP usage.
**Separate PR:** yes.

### PR-7 — Phase 2d: Deterministic test-candidate generator + validation/deduplication (B)
**Owner:** B
**Scope:**
- `apps/api/app/test_generation/deterministic.py`, `validation.py`, `deduplication.py`.
- Produce candidate cases for: positive (canonical happy path), negative (invalid method, missing required params, wrong types), boundary (min/max/0/empty/long-strings/enum edge), schema (required/type/format/nullable mismatch), and a minimal workflow skeleton (just parameter/cross-parameter combos for MVP — full workflow is not in MVP per SoT, so keep workflow generation scoped to single-operation dependencies only).
- Candidate validation: reject unbounded payloads, reject candidates with disallowed headers (no `Host`, no `Cookie` injection, no `Authorization` overwrite unless explicitly provided by user in the saved request), enforce body size budgets.
- Deduplication: stable candidate IDs based on normalized method+path+mutation signature so re-running the generator on the same spec yields identical IDs.
- No LLM required in this PR (LLM adapter lands in PR-8).
**Prereqs:** PR-5, PR-6.
**Files:** `apps/api/app/test_generation/**` (excluding `llm_assisted.py`), `apps/api/tests/test_generation/**`.
**Tests:** Determinism (same input → same IDs across runs), deduplication, size-cap/budget enforcement, fixtures for malformed ops.
**Acceptance:** Candidate generator works without any LLM credentials; bounded outputs; stable IDs; invalid/malicious candidates rejected at validation.
**Separate PR:** yes.

### PR-8 — Phase 2e: Optional LLM adapter interface (B, A→review on config/secrets)
**Owner:** B
**Scope:**
- `apps/api/app/integrations/llm/`: `base.py` (provider-neutral interface with bounded input/output, timeout, token/size caps), `provider_openai_compat.py` (one adapter; OpenAI-compatible chat endpoint only), `factory.py`, `errors.py`.
- Configuration for provider/model/API key lives in A-owned `core/config.py` (this PR adds only typed accessors; A reviews secrets handling).
- Deterministic safe-fallback when no key configured — provider returns a clear "LLM unavailable" result; caller (future `llm_assisted.py`) must degrade gracefully.
- No prompts/responses logged beyond redacted, bounded length.
**Prereqs:** PR-1 (config), PR-7 (candidate types).
**Files:** `apps/api/app/integrations/llm/**`, `apps/api/tests/integrations/llm/**`.
**Tests:** Adapter unit tests with a fake transport; fallback when no key; size/budget enforcement; never leaks API key into errors/logs.
**Acceptance:** `httpx` usage must go through A's execution service *only for outbound calls to the LLM provider* — or, with A's approval, a narrowly scoped provider client that nevertheless respects the same secret-redaction/logging policy (document decision in PR). Fail-closed when misconfigured.
**Separate PR:** yes.

> Note: Endpoints/persistence for workspace requests, environments with secret encryption, OpenAPI file/URL import, and candidate preview are **not scheduled yet** because they depend on DB models/migrations and project ownership (A-owned). Per your instruction I am not expanding DB/auth tasks in this session. The work above is deliberately DB-free so B's intelligence modules can land and be reviewed against agreed DTOs while A's foundation work is scoped separately. If you want me to expand DB-auth tasks, see Decision #2.

### PR-9 — Phase 3a: Assertion evaluation (B)
**Owner:** B
**Scope:**
- `apps/api/app/analysis/assertions.py` implementing exactly the five MVP assertion types: (1) HTTP status code, (2) latency threshold, (3) JSON path/value, (4) response header, (5) response schema (subset: JSON Schema draft used by OpenAPI 3.1, type/required/enum/format/pattern/min/max/array items/object properties — no remote refs).
- Produce `AssertionResult` DTOs (agreed in `packages/contracts/`).
- Deterministic; no LLM use.
**Prereqs:** PR-4 (needs `ExecutionResult`), PR-5/PR-6/PR-7 (schema knowledge).
**Files:** `apps/api/app/analysis/assertions.py`, `apps/api/app/analysis/schema_compare.py`, `apps/api/tests/analysis/test_assertions.py`, `tests/analysis/test_schema_compare.py`, `packages/contracts/assertion_result.md`.
**Tests:** Each assertion type with pass/fail/edge cases; schema-compare regressions; JSON-path edge cases (missing path, type mismatch, arrays, nested).
**Acceptance:** Fixed five types only (no more added without a recorded decision); failed assertions are observations, not defect claims.
**Separate PR:** yes.

### PR-10 — Phase 3b: Evidence-based classification (B, A→review on finding DTO/persistence)
**Owner:** B
**Scope:**
- `apps/api/app/analysis/classification.py`: rules-based classifier mapping assertion mismatches + schema differences to preliminary finding categories. No "vulnerability" auto-claims; severity is `info`/`low`/`medium` by heuristic with explainable rationale.
- Produces `FindingRead` and `EvidenceReferenceRead` candidate payloads (DTOs agreed in `packages/contracts/`). Does not persist — persistence is A's job.
- All findings carry evidence provenance and are traceable to specific execution + assertion.
**Prereqs:** PR-9.
**Files:** `apps/api/app/analysis/**`, `apps/api/tests/analysis/test_classification.py`, `packages/contracts/finding.md`, `packages/contracts/evidence.md`.
**Tests:** Classifier determinism, evidence traceability, no over-claiming regressions.
**Acceptance:** No finding is emitted without evidence; no "security issue" auto-diagnosis without explicit rule + evidence.
**Separate PR:** yes.

### PR-11 — Phase 4a: Adaptive scoring / follow-up selection (B)
**Owner:** B
**Scope:**
- `apps/api/app/adaptive/scoring.py`, `selection.py`, `rationale.py`: score candidate+outcome pairs, propose next tests for diversity/coverage within budgets, produce human-readable rationale strings (for UI).
- No direct DB/HTTP in this module; receives a snapshot of prior results and returns ranked next-step candidates.
**Prereqs:** PR-7, PR-9, PR-10.
**Files:** `apps/api/app/adaptive/**`, `apps/api/tests/adaptive/**`.
**Tests:** Deterministic scoring; budget enforcement; diversity regressions; rationale stability.
**Acceptance:** Scoring is explainable, deterministic given same inputs; respects configured budgets.
**Separate PR:** yes.

### Remaining phases (A-owned, deferred by your "no DB/auth" instruction, listed for completeness)
The following all depend on DB schema + migrations + project ownership and are not expanded into detailed PRs here, but the order is:

- **PR-12+ Phase 1d:** Auth/session (Google token verify, hashed sessions, cookies, CSRF, logout), DB base/session wiring, Alembic baseline `0001_init`, users/sessions/projects models + `0002_identity_projects.py` migration, project CRUD/archive/overview, ownership enforcement dependency. (A)
- **PR-13+ Phase 2f:** Collections, saved requests, environments (secret encryption, resolver), executions/history persistence, request execution endpoint wired through PR-4's service, file-based spec import (bounded JSONB, hash/version metadata), safe URL spec import through shared execution service, non-persisting candidate preview endpoint (calls PR-7 generator, no writes). Migrations `0003_workspace_assets.py`, `0004_execution_api_understanding.py`. (A, with calls into B's modules)
- **PR-14+ Phase 3c:** Health-checks CRUD/run/run-history, evidence/findings persistence + APIs, user-managed triage PATCH, overview/report aggregation. Migration `0006_findings_evidence.py`. (A, with calls into B's assertions/classifier)
- **PR-15+ Phase 4b:** Campaign state machine, `campaign_jobs` with row-lock claim + leases + recovery, atomic create-job-event, worker entrypoint, cancel idempotency, budget-exhaustion events, uncertain-outcome recording (DB-09 — *must be designed with B's orchestration hook*), tests for restart-recovery, events/tests/executions/report endpoints. Migration `0005_testing_campaigns.py`. (A, hooks into B's adaptive module)
- **PR-16+ Phase 5:** Frontend features one-by-one against real endpoints: auth/project shell, workspace/executor/history, explorer import + candidate preview, health-check runs, campaign timeline, findings/evidence/report, generated TypeScript types in CI, drift check. (A)
- **PR-17+ Phase 6:** E2E flows (4 required: auth/project lifecycle; request execution/history; OpenAPI import+preview; campaign→executions→findings→report), migration-from-empty test, security regression suite in CI, runbook + status doc completion, release-candidate hardening. (A leads, B reviews intelligence quality)

Each of those later PRs must come with its own exact `pytest` / `npm run` commands and observed results in the PR description, per the ownership matrix §5.

---

## 7. Verification commands & acceptance gates per milestone

These are the commands each PR must show as actually passing before being marked complete. No command is listed as "passing" in this audit — they will be the gates for PRs.

### Milestone: PR-0 (docs/skeleton)
```bash
cd /home/user/IntelAPI
git status --short                 # expect: clean
ls docs/                           # expect: all 7 doc files present (2 real, 5 stubs)
test -f README.md                  # expect: 0
```
Gate: PR review confirms no source files fabricated, no `.env` committed, no secrets.

### Milestone: PR-1 (API scaffold + health)
```bash
cd apps/api
python -m venv .venv && . .venv/bin/activate
pip install -e .                   # (after manifests land; CI will do this)
pytest -q                          # must pass
python -c "from fastapi.testclient import TestClient; from app.main import app; \
           c=TestClient(app); r=c.get('/health/live'); \
           assert r.status_code==200 and r.json()=={'status':'alive'}, r.text"
```
Gate: `/health/live` body is exactly `{"status":"alive"}`; 404 under `/api/v1` returns structured error envelope.

### Milestone: PR-2 (Web scaffold)
```bash
cd apps/web
npm install
npm run lint
npm run typecheck
npm run test -- --run
npm run build
```
Gate: all green; dev server binds 0.0.0.0 and accepts the e2b preview host.

### Milestone: PR-3 (Compose + CI baseline)
```bash
docker compose config              # must parse
docker compose up --build -d api web
curl -fsS http://localhost:8000/health/live   # {"status":"alive"}
```
Gate: CI runs on push/PR and shows green; `.env.example` is exhaustive and non-secret.

### Milestone: PR-4 (Secure outbound execution — security gate)
```bash
cd apps/api
pytest -q tests/security -v        # all SSRF/DNS/redirect/rebinding/redaction tests
# import-lint: no file under app/ except app/execution/transport.py imports httpx.AsyncClient
! grep -R "httpx\.AsyncClient\|httpx\.Client" app/ --include="*.py" \
    | grep -v "^app/execution/"
```
Gate: every SSRF/redirect/DNS/redaction scenario listed in PR-4's test list passes; no second HTTP client anywhere.

### Milestone: PR-5 / PR-6 / PR-7 / PR-8 / PR-9 / PR-10 / PR-11 (intelligence modules)
```bash
cd apps/api
pytest -q tests/api_understanding tests/knowledge tests/test_generation \
          tests/integrations/llm tests/analysis tests/adaptive -v
# Determinism check for candidate generation (PR-7):
python -c "from app.test_generation.deterministic import generate; \
           from app.api_understanding import parse; \
           import json; spec=parse(b'''{...fixture...}'''); \
           a=[c.id for c in generate(spec)]; b=[c.id for c in generate(spec)]; \
           assert a==b, 'candidate ids not stable'"
```
Gate: unit tests green; no network calls made during tests (enforced by HTTPX mock / monkeypatch); no module imports `httpx.AsyncClient`; LLM adapter fails closed without credentials.

### Milestone: PR-12+ (DB/Auth — deferred per your note, gates recorded for later)
- `cd apps/api && alembic upgrade head` works from empty PostgreSQL.
- `pytest -q tests/integration` passes against a disposable PostgreSQL (Compose service).
- Migration test: `alembic downgrade base && alembic upgrade head` is repeatable.
- Ownership test: user-A cannot access user-B's project by UUID guessing; returns 404 (not 403) to avoid existence leaks (recommend 404 per SoT §5.2, but this is Decision #3).

### Milestone: Final (Phase 6)
```bash
# backend
cd apps/api && pytest -q
# frontend
cd apps/web && npm run lint && npm run typecheck && npm run test -- --run && npm run build
# generated-types drift
python scripts/export_openapi.py > /tmp/openapi.json
python scripts/generate_api_types.py /tmp/openapi.json apps/web/src/services/generated/api-schema.ts
git diff --exit-code apps/web/src/services/generated/
# e2e (4 required flows)
#   1) auth → create project → archive
#   2) send request → inspect response → see history → view execution detail
#   3) import OpenAPI (file + safe URL) → browse ops → preview candidates (non-persisting)
#   4) create campaign → observe events/executions → cancel → see findings/evidence/report (partial)
# security: ensure no secrets/Authorization headers leak into logs/snapshots/evidence
```
Gate: all four E2E flows pass; status doc is updated to mark only verified features complete.

---

## 8. Decisions requiring your approval

Before implementation begins, these decisions need an explicit answer. None of them change the frozen contract in the Source of Truth; they are implementation choices left open by the canonical docs.

1. **Docs bootstrap & README location.** Approve committing the two attached canonical docs into `docs/`, stamping the other five docs as drafts, and creating a root `README.md` that points into `docs/` (instead of a `docs/README.md`).
2. **Scope of DB/Auth work in this engagement.** You said "No need to touch database and authentication parts." I've drafted PRs 0–11 as DB/auth-free so the intelligence harness and secure execution boundary (the security-critical PR-4) can be implemented and reviewed without DB migrations. Please confirm:
   - (a) Proceed with PRs 0–11 now and leave PR-12+ (auth, DB, persistence, frontend features that need data) for a later engagement; or
   - (b) Include a thin in-memory/stub persistence layer just enough to support workspace/history endpoints in this engagement (I do **not** recommend this — it contradicts SoT layering and Alembic rule); or
   - (c) Authorize PR-12+ foundation work (A-owned) as part of this engagement despite your note, in which case I'll expand PR-12+ into detailed tasks now.
3. **Cross-tenant access error code.** SoT §5.2 lists 403 `FORBIDDEN` and 404 `NOT_FOUND`. When an authenticated user requests a project/execution/resource that exists but belongs to another user, should the API return 404 (to avoid existence oracle, recommended) or 403? The ownership section ("A user cannot read another user's resources by changing a UUID in a URL") suggests existence-hiding, but doesn't mandate 404.
4. **Frontend package manager.** SoT specifies React/Vite/TypeScript but doesn't fix a package manager. Options: `pnpm` (recommended for monorepo speed and workspaces), `npm` (built-in), `yarn` (Berry). Affects lockfile and CI.
5. **LLM outbound transport.** PR-8 must make outbound calls to an LLM provider. Two options:
   - (a) Route the LLM adapter through **the same A-owned `execution.service`** used for target requests, applying the same policy with an explicit "LLM provider" allowlist; or
   - (b) A narrowly scoped, A-owned LLM-only HTTP client that reuses redaction/timeout/secret-safe logging but bypasses the private-IP block only for a configured provider hostname (simpler, but creates a second network egress path).
   SoT §10.1 says "every outbound target request … through security controls appropriate to that operation" — both are defensible; I recommend (a) for least surprise.
6. **Worker transport/startup.** SoT says the worker is a separate process sharing domain code, not a separate HTTP service. Confirm: the worker binary is `python -m app.campaigns.worker` inside the same `apps/api` container image (separate Compose service), with its own command, rather than a new container image.
7. **Python version.** Local sandbox has 3.11.2; FastAPI/SQLAlchemy/Pydantic v2 support 3.11+. Do you want to pin `3.11` or `3.12` for the Docker image/CI?

---

## 9. Summary in one paragraph

The repository is in a pre-scaffold state: one commit, one tracked file (`.gitignore`), no source code, no manifests, no Docker/CI, no docs directory, and five of the seven canonical documents missing (the two you attached are in `/tmp/arena-coding-uploads/`, not in the repo). The local sandbox has Python 3.11 and Node 22 but no Docker/psql/alembic/pytest and I did not install anything per the audit restrictions. There are **zero** implemented features from the SoT inventory — not even `/health/live`. The highest-priority risk is the absence of the single secure outbound execution boundary (SSRF/DNS/redirect/redaction), which must land before any feature that touches the network. Because you asked not to touch DB and authentication in this session, the backlog is ordered so the security-critical execution service (PR-4) and B's intelligence/intelligence-test modules (PRs 5–11) can land against agreed DTOs without waiting for DB migrations, with DB/auth/persistence/frontend deferred to a later sequence pending your decision on scope.
