# Local Runbook

This document describes how to run IntelAPI locally. Authoritative for local development.

## Prerequisites

- Docker Engine 24+ with Compose v2, **or**
- Python 3.11+, Node 22+, PostgreSQL 15+ for native development.

All secrets are loaded from `.env`. Copy the example and fill in values:

```bash
cp .env.example .env
```

Never commit `.env`. The `GOOGLE_CLIENT_ID` and `SESSION_SECRET_KEY` / `ENCRYPTION_KEY` must be set. For local-only
development you can generate random 32-byte hex keys:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Docker Compose (recommended)

```bash
docker compose up --build
```

Services:

| Service   | URL                          |
|-----------|------------------------------|
| `api`     | http://localhost:8000        |
| `web`     | http://localhost:5173        |
| `worker`  | (separate process, no HTTP)  |
| `db`      | Postgres 15 on localhost:5432 (host port mapped in compose.yml) |

First run creates the database and runs all Alembic migrations automatically on the API container's startup.

### Useful commands

```bash
# View logs
docker compose logs -f api

# Restart API (code changes are mounted via volume for api/web)
docker compose restart api

# Run backend tests against an ephemeral Postgres
docker compose run --rm api pytest -q

# Run frontend tests
docker compose run --rm web npm test -- --run

# Run a database migration manually
docker compose run --rm api alembic upgrade head

# Create a new migration
docker compose run --rm api alembic revision --autogenerate -m "describe change"
```

## Native (non-Docker)

```bash
# Backend
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
alembic upgrade head                                # needs a running Postgres
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd apps/web
npm install
npm run dev -- --host 0.0.0.0
```

Set `DATABASE_URL=postgresql+psycopg://intelapi:intelapi@localhost:5432/intelapi` (or whatever
your local Postgres uses) in `.env`.

## Health checks

- `GET /health/live` returns `{"status":"alive"}` (liveness, always 200 when process is up).
- `GET /health/ready` returns 200 when the API can connect to Postgres; 503 otherwise.

The canonical liveness body is `{"status":"alive"}` (see `SOURCE_OF_TRUTH.md` §12.1). Do not change it
in an unrelated PR.

## Generating TypeScript API types

FastAPI's generated OpenAPI schema is the source of truth for TypeScript types.

```bash
python scripts/export_openapi.py > apps/api/openapi.json
python scripts/generate_api_types.py apps/api/openapi.json apps/web/src/services/generated/api-schema.ts
```

CI runs these and fails if the committed file drifts.

## Running security tests (SSRF / redaction)

```bash
cd apps/api
pytest -q tests/security -v
```

The security suite covers private/loopback/link-local/multicast IP rejection, redirect revalidation,
DNS-rebinding defenses, timeout/oversize handling, and secret redaction. It must pass on every PR.

## Resetting local database (dev only)

```bash
docker compose down -v       # removes volumes
docker compose up --build
```

This is a destructive local operation. Never run against any deployed environment.
