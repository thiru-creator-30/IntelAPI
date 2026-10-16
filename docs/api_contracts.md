# API Contracts

This document is a human-readable companion to the machine-generated FastAPI OpenAPI schema,
which is authoritative for request/response types. Run the API and visit
`/openapi.json` or `/docs` for the canonical schema.

All product routes are prefixed with `/api/v1`. Health probes are unprefixed:

- `GET /health/live` → `{"status":"alive"}`
- `GET /health/ready` → `{"status":"ready"}` or 503

## Error envelope

All errors use:

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "...", "details": {} } }
```

Stable error codes: `UNAUTHENTICATED`, `FORBIDDEN`, `TARGET_BLOCKED`, `NOT_FOUND`,
`CONFLICT`, `VALIDATION_ERROR`, `TARGET_TIMEOUT`, `INTERNAL_ERROR`.

## Pagination

All list endpoints accept `?limit=50&offset=0` (max limit 100) and return:

```json
{ "items": [...], "pagination": { "limit": 50, "offset": 0, "total": 42 } }
```

## Auth

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/auth/google/config` | Public Google client ID for the frontend |
| POST | `/auth/google/session` | Exchange Google ID token for an opaque session cookie |
| GET  | `/auth/me` | Current user |
| POST | `/auth/logout` | Revoke session server-side, expire cookie |

Sessions are delivered as `HttpOnly` `SameSite=Lax` cookies (configurable).

## Projects

| Method | Path |
|--------|------|
| GET    | `/projects` |
| POST   | `/projects` |
| GET    | `/projects/{project_id}` |
| PATCH  | `/projects/{project_id}` |
| POST   | `/projects/{project_id}/archive` |
| GET    | `/projects/{project_id}/overview` |

Cross-tenant access returns 404 (existence hiding).

## Collections and saved requests

| Method | Path |
|--------|------|
| GET/POST | `/projects/{project_id}/collections` |
| GET/PATCH/DELETE | `/collections/{collection_id}` |
| GET/POST | `/projects/{project_id}/requests` |
| GET/PATCH/DELETE | `/requests/{request_id}` |
| POST | `/requests/execute` — send through the secure outbound boundary |
| GET | `/projects/{project_id}/history` |
| GET | `/executions/{execution_id}` |

## Environments

| Method | Path |
|--------|------|
| GET/POST | `/projects/{project_id}/environments` |
| GET/PATCH/DELETE | `/environments/{environment_id}` |

Secret values are encrypted at rest and redacted on read (never returned in plaintext after write).

## Specifications & operations

| Method | Path |
|--------|------|
| GET    | `/projects/{project_id}/specifications` |
| POST   | `/projects/{project_id}/specifications/import` (multipart: `file` OR `url`) |
| GET    | `/specifications/{specification_id}` |
| GET    | `/specifications/{specification_id}/operations` |
| GET    | `/operations/{operation_id}` |
| POST   | `/operations/{operation_id}/candidates/preview` (non-persisting) |

URL imports always traverse the shared secure outbound boundary. The OpenAPI parser never
performs its own network fetches; remote `$ref`s are rejected.

## Health checks

| Method | Path |
|--------|------|
| GET/POST | `/projects/{project_id}/health-checks` |
| GET/PATCH/DELETE | `/health-checks/{check_id}` |
| POST | `/health-checks/{check_id}/run` |
| GET  | `/health-checks/{check_id}/runs` |

Supported assertion types (fixed five): `status_code`, `latency_ms`, `json_path_value`,
`response_header`, `response_schema`.

## Campaigns

| Method | Path |
|--------|------|
| GET/POST | `/projects/{project_id}/campaigns` |
| GET    | `/campaigns/{campaign_id}` |
| POST   | `/campaigns/{campaign_id}/cancel` |
| GET    | `/campaigns/{campaign_id}/tests` |
| GET    | `/campaigns/{campaign_id}/executions` |
| GET    | `/campaigns/{campaign_id}/events` |
| GET    | `/campaigns/{campaign_id}/report` |

Create returns `202 Accepted`. Cancel is idempotent on terminal states (returns `200`).

## Findings & evidence

| Method | Path |
|--------|------|
| GET    | `/projects/{project_id}/findings` |
| GET/PATCH | `/findings/{finding_id}` |
| GET    | `/findings/{finding_id}/evidence` |
| GET    | `/evidence/{evidence_id}` |

`PATCH /findings/{finding_id}` accepts only user-managed fields (`triage_status`, `user_severity`, `user_notes`).
Machine-derived severity/classification cannot be overwritten.
