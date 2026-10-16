# Database Schema

PostgreSQL 15+. SQLAlchemy 2.x ORM. All schema changes via Alembic migrations in `apps/api/alembic/versions/`.
Do **not** use `Base.metadata.create_all()` as a migration substitute.

## Conventions

- Primary keys: UUIDv4 (`id` column).
- Timestamps: `created_at`, `updated_at` (timezone-aware UTC).
- Soft deletes: `deleted_at TIMESTAMPTZ NULL` (projects only, per DB-01).
- All project-scoped resources carry `project_id` with FK and NOT NULL; repositories must
  filter by owner (server-side enforcement).
- Money/counts: INTEGER unless noted.
- JSONB for OpenAPI specs, parsed parameter/body/response shapes, execution snapshots,
  evidence excerpts, candidate payloads.

## Tables

### `users`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `google_sub` | TEXT UNIQUE NOT NULL | Google stable `sub` (identity key) |
| `email` | TEXT | Attribute only — not used for identity |
| `display_name` | TEXT NULL | |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

### `sessions`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK users | |
| `token_hash` | TEXT UNIQUE NOT NULL | SHA-256 of the opaque cookie token; token itself is never persisted |
| `expires_at` | TIMESTAMPTZ NOT NULL | |
| `revoked_at` | TIMESTAMPTZ NULL | Revocation is idempotent |
| `created_at` | TIMESTAMPTZ | |
| `user_agent`, `ip` | TEXT NULL | Audit fields only — do not trust for security |

### `projects`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `owner_id` | UUID FK users NOT NULL | |
| `name` | TEXT NOT NULL | |
| `description` | TEXT NULL | |
| `archived_at` | TIMESTAMPTZ NULL | Soft-delete (DB-01) |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

### `collections`
| Column | Type |
|---|---|
| `id` | UUID PK |
| `project_id` | UUID FK projects NOT NULL |
| `name` | TEXT NOT NULL |
| `created_at`, `updated_at` | TIMESTAMPTZ |

### `saved_requests`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `project_id` | UUID FK projects NOT NULL | |
| `collection_id` | UUID FK collections NULL | |
| `name` | TEXT NOT NULL | |
| `method` | TEXT NOT NULL | `GET`/`POST`/... uppercased |
| `url` | TEXT NOT NULL | |
| `headers` | JSONB NOT NULL DEFAULT `{}` | Resolved headers are stored in execution snapshot; this holds saved (possibly templated) headers |
| `body` | TEXT NULL | Saved body; templating allowed |
| `environment_id` | UUID FK environments NULL | |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

### `environments`
| Column | Type |
|---|---|
| `id` | UUID PK |
| `project_id` | UUID FK projects NOT NULL |
| `name` | TEXT NOT NULL |
| `created_at`, `updated_at` | TIMESTAMPTZ |

### `environment_variables`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `environment_id` | UUID FK environments NOT NULL | |
| `name` | TEXT NOT NULL | Unique per environment |
| `value_enc` | BYTEA NOT NULL | Fernet-encrypted value; plaintext never leaves the server after write (DB-02) |
| `is_secret` | BOOLEAN NOT NULL DEFAULT TRUE | When true, value is redacted in logs/snapshots/evidence as well |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

### `executions`
Immutable after insert.
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `project_id` | UUID FK projects NOT NULL | |
| `saved_request_id` | UUID FK saved_requests NULL | Null for ad-hoc/campaign runs |
| `parent_check_run_id` | UUID FK health_check_runs NULL | |
| `parent_test_case_id` | UUID FK test_cases NULL | |
| `method` | TEXT NOT NULL | |
| `url` | TEXT NOT NULL | Final URL (post-redirect) |
| `request_snapshot` | JSONB NOT NULL | Resolved, redacted request snapshot (DB-04) |
| `outcome` | TEXT NOT NULL | `http_response`/`timeout`/`connection_error`/`blocked_by_policy`/`response_too_large`/`execution_error` |
| `status_code` | INT NULL | |
| `duration_ms` | INT NULL | |
| `response_headers` | JSONB NULL | |
| `response_body_excerpt` | TEXT NULL | Bounded (capped by config) |
| `response_size_bytes` | BIGINT NULL | |
| `transport_error` | TEXT NULL | Redacted, internal-only |
| `started_at`, `completed_at` | TIMESTAMPTZ | |
| `created_at` | TIMESTAMPTZ | |

### `assertion_results`
| Column | Type |
|---|---|
| `id` | UUID PK |
| `execution_id` | UUID FK executions NOT NULL |
| `assertion_type` | TEXT NOT NULL |
| `assertion_config` | JSONB NOT NULL |
| `passed` | BOOLEAN NOT NULL |
| `actual` | JSONB NULL |
| `message` | TEXT NULL |
| `created_at` | TIMESTAMPTZ |

### `api_specifications`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `project_id` | UUID FK projects NOT NULL | |
| `source_type` | TEXT NOT NULL | `file` / `url` |
| `source_url` | TEXT NULL | |
| `title`, `version` | TEXT NULL | Extracted |
| `spec_json` | JSONB NOT NULL | Bounded original document (DB-03) |
| `content_hash` | TEXT NOT NULL | SHA-256 of raw input |
| `spec_format` | TEXT NOT NULL | `openapi_3` |
| `size_bytes` | BIGINT NOT NULL | |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

### `api_operations`
| Column | Type |
|---|---|
| `id` | UUID PK |
| `specification_id` | UUID FK api_specifications NOT NULL |
| `project_id` | UUID FK projects NOT NULL |
| `method` | TEXT NOT NULL |
| `path` | TEXT NOT NULL |
| `operation_id` | TEXT NULL |
| `summary` | TEXT NULL |
| `normalized` | JSONB NOT NULL |
| `created_at` | TIMESTAMPTZ |

(UNIQUE(specification_id, method, path).)

### `knowledge_facts`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `project_id` | UUID FK projects NOT NULL | |
| `provenance` | TEXT NOT NULL | `DECLARED`/`EXTRACTED`/`OBSERVED`/`INFERRED` |
| `fact_type` | TEXT NOT NULL | |
| `subject_type`, `subject_id` | TEXT, UUID | source (spec / operation / execution / finding) |
| `payload` | JSONB NOT NULL | |
| `created_at` | TIMESTAMPTZ | |

### `health_checks`
| Column | Type |
|---|---|
| `id` | UUID PK |
| `project_id` | UUID FK projects NOT NULL |
| `name` | TEXT NOT NULL |
| `request_definition` | JSONB NOT NULL |
| `assertions` | JSONB NOT NULL | Fixed five types only; array of typed configs |
| `created_at`, `updated_at` | TIMESTAMPTZ |

### `health_check_runs`
| Column | Type |
|---|---|
| `id` | UUID PK |
| `health_check_id` | UUID FK health_checks NOT NULL |
| `project_id` | UUID FK projects NOT NULL |
| `outcome` | TEXT NOT NULL | `pass`/`fail`/`error` |
| `execution_id` | UUID FK executions NOT NULL |
| `created_at` | TIMESTAMPTZ |

### `test_cases`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | Stable deterministic ID per (campaign, candidate) |
| `campaign_id` | UUID FK campaigns NOT NULL | |
| `project_id` | UUID FK projects NOT NULL | |
| `source_operation_id` | UUID FK api_operations NULL | |
| `kind` | TEXT NOT NULL | `positive`/`negative`/`boundary`/`schema`/`workflow` |
| `request_definition` | JSONB NOT NULL | |
| `assertions` | JSONB NOT NULL | |
| `provenance` | JSONB NOT NULL | Why this test was generated |
| `created_at` | TIMESTAMPTZ | |

### `campaigns`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `project_id` | UUID FK projects NOT NULL | |
| `name` | TEXT NOT NULL | |
| `source_specification_id` | UUID FK api_specifications NULL | |
| `source_operation_id` | UUID FK api_operations NULL | |
| `state` | TEXT NOT NULL | `queued`/`running`/`completed`/`failed`/`cancelled` |
| `budget_executions` | INT NOT NULL DEFAULT 200 | |
| `executions_used` | INT NOT NULL DEFAULT 0 | |
| `started_at`, `completed_at` | TIMESTAMPTZ NULL | |
| `failure_reason` | TEXT NULL | |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

### `campaign_jobs`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | A single row per campaign is the durable queue claim target (DB-08) |
| `campaign_id` | UUID FK campaigns NOT NULL UNIQUE | |
| `lease_owner` | TEXT NULL | Worker instance ID |
| `lease_expires_at` | TIMESTAMPTZ NULL | |
| `claimed_at`, `completed_at` | TIMESTAMPTZ NULL | |
| `last_heartbeat_at` | TIMESTAMPTZ NULL | |
| `next_test_cursor` | JSONB NULL | Adaptive selection state |
| `recovery_uncertain_execution_id` | UUID FK executions NULL | DB-09: recorded, not retried blindly |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

### `campaign_events`
Append-only.
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `campaign_id` | UUID FK campaigns NOT NULL | |
| `event_type` | TEXT NOT NULL | `created`/`claimed`/`test_scheduled`/`execution_completed`/`assertion_evaluated`/`finding_created`/`budget_exhausted`/`failed`/`cancelled`/`completed`/`recovery_uncertain_outcome` |
| `payload` | JSONB NOT NULL | |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

### `evidence_references`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `project_id` | UUID FK projects NOT NULL | |
| `source_type` | TEXT NOT NULL | `execution`/`assertion`/`specification`/`fact` |
| `source_id` | UUID NOT NULL | |
| `provenance` | TEXT NOT NULL | `DECLARED`/`EXTRACTED`/`OBSERVED`/`INFERRED` (DB-10) |
| `excerpt` | JSONB NOT NULL | Bounded, redacted |
| `created_at` | TIMESTAMPTZ | |

### `findings`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `project_id` | UUID FK projects NOT NULL | |
| `campaign_id` | UUID FK campaigns NULL | |
| `category` | TEXT NOT NULL | |
| `machine_severity` | TEXT NOT NULL | `info`/`low`/`medium`/`high` |
| `triage_status` | TEXT NOT NULL DEFAULT `new` | `new`/`triaging`/`accepted`/`dismissed` (user-managed) |
| `user_severity` | TEXT NULL | User override |
| `user_notes` | TEXT NULL | |
| `title`, `summary` | TEXT NOT NULL | |
| `evidence_ids` | JSONB NOT NULL DEFAULT `[]` | Array of evidence UUIDs |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

## Indexes (summary)

- All FKs have indexes.
- `sessions(token_hash)` unique; `sessions(user_id)`.
- `projects(owner_id, archived_at)`.
- `executions(project_id, created_at desc)`; `executions(saved_request_id)`; `executions(parent_test_case_id)`.
- `api_specifications(project_id, created_at)`.
- `api_operations(specification_id, method, path)` unique.
- `test_cases(campaign_id)`; `campaign_events(campaign_id, created_at desc)`.
- `campaign_jobs(lease_expires_at)` for the claim query.
- `findings(project_id, created_at desc)`.
