# IntelAPI

AI-assisted API understanding, testing, execution, evidence and adaptive test-campaign platform.

- **Backend:** FastAPI / Pydantic v2 / SQLAlchemy 2.x / Alembic / HTTPX / PostgreSQL
- **Frontend:** React 18 + Vite + TypeScript
- **Local orchestration:** Docker Compose
- **CI:** GitHub Actions (backend lint/tests, frontend lint/typecheck/test/build, migration test, generated-API-types drift check)

## Start here

- Product/technical source of truth: [`docs/SOURCE_OF_TRUTH.md`](docs/SOURCE_OF_TRUTH.md)
- Implementation plan and ownership: [`docs/IMPLEMENTATION_PLAN_AND_OWNERSHIP.md`](docs/IMPLEMENTATION_PLAN_AND_OWNERSHIP.md)
- Verified implementation status: [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md)
- API contract reference: [`docs/api_contracts.md`](docs/api_contracts.md)
- Database schema reference: [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md)
- Local setup & runbook: [`docs/LOCAL_RUNBOOK.md`](docs/LOCAL_RUNBOOK.md)

## Quick start (Docker Compose)

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000 (health: http://localhost:8000/health/live)
- Web UI: http://localhost:5173

## Repository layout

```
apps/
  api/        FastAPI backend (Python)
  web/        React/Vite/TypeScript frontend
packages/
  contracts/  Agreed shared DTO notes between Developer A and B
scripts/      OpenAPI export / TS type generation
alembic/      (inside apps/api/) database migrations
.github/      CI workflows
```

One owner per module — see the ownership matrix in `docs/IMPLEMENTATION_PLAN_AND_OWNERSHIP.md`.
