"""initial schema

Revision ID: 0001_init
Revises:
Create Date: 2026-10-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("google_sub", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, server_default=""),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_sub"),
    )
    op.create_index("ix_users_google_sub", "users", ["google_sub"])

    # sessions
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("ip", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"])

    # projects
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])

    # collections
    op.create_table(
        "collections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_collections_project_id", "collections", ["project_id"])

    # environments
    op.create_table(
        "environments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_environments_project_id", "environments", ["project_id"])

    # environment_variables
    op.create_table(
        "environment_variables",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("value_enc", sa.LargeBinary(), nullable=False),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("environment_id", "name", name="uq_env_var_env_name"),
    )
    op.create_index("ix_environment_variables_environment_id", "environment_variables", ["environment_id"])

    # api_specifications
    op.create_table(
        "api_specifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("version", sa.String(), nullable=True),
        sa.Column("spec_json", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("spec_format", sa.String(), nullable=False, server_default="openapi_3"),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_specifications_project_id", "api_specifications", ["project_id"])
    op.create_index("ix_api_specifications_content_hash", "api_specifications", ["content_hash"])

    # campaigns
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source_specification_id", sa.Uuid(), nullable=True),
        sa.Column("source_operation_id", sa.Uuid(), nullable=True),
        sa.Column("state", sa.String(), nullable=False, server_default="queued"),
        sa.Column("budget_executions", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("executions_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_specification_id"], ["api_specifications.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaigns_project_id", "campaigns", ["project_id"])
    op.create_index("ix_campaigns_state", "campaigns", ["state"])

    # api_operations (FK to campaigns.source_operation_id added after creation)
    op.create_table(
        "api_operations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("specification_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("operation_id", sa.String(), nullable=True),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("normalized", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["specification_id"], ["api_specifications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("specification_id", "method", "path", name="uq_op_spec_method_path"),
    )
    op.create_index("ix_api_operations_specification_id", "api_operations", ["specification_id"])
    op.create_index("ix_api_operations_project_id", "api_operations", ["project_id"])

    with op.batch_alter_table("campaigns") as b:
        b.create_foreign_key("fk_campaigns_source_operation_id", "api_operations", ["source_operation_id"], ["id"], ondelete="SET NULL")

    # saved_requests
    op.create_table(
        "saved_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("method", sa.String(), nullable=False, server_default="GET"),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("headers", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("environment_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_requests_project_id", "saved_requests", ["project_id"])
    op.create_index("ix_saved_requests_collection_id", "saved_requests", ["collection_id"])

    # knowledge_facts
    op.create_table(
        "knowledge_facts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("provenance", sa.String(), nullable=False),
        sa.Column("fact_type", sa.String(), nullable=False),
        sa.Column("subject_type", sa.String(), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_facts_project_id", "knowledge_facts", ["project_id"])

    # health_checks
    op.create_table(
        "health_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("request_definition", sa.JSON(), nullable=False),
        sa.Column("assertions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_health_checks_project_id", "health_checks", ["project_id"])

    # test_cases
    op.create_table(
        "test_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_operation_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("request_definition", sa.JSON(), nullable=False),
        sa.Column("assertions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("provenance", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_operation_id"], ["api_operations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_cases_campaign_id", "test_cases", ["campaign_id"])
    op.create_index("ix_test_cases_project_id", "test_cases", ["project_id"])

    # executions
    op.create_table(
        "executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("saved_request_id", sa.Uuid(), nullable=True),
        sa.Column("parent_check_run_id", sa.Uuid(), nullable=True),
        sa.Column("parent_test_case_id", sa.Uuid(), nullable=True),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("request_snapshot", sa.JSON(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("response_headers", sa.JSON(), nullable=True),
        sa.Column("response_body_excerpt", sa.Text(), nullable=True),
        sa.Column("response_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("transport_error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["saved_request_id"], ["saved_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_test_case_id"], ["test_cases.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_executions_project_id", "executions", ["project_id"])
    op.create_index("ix_executions_saved_request_id", "executions", ["saved_request_id"])
    op.create_index("ix_executions_parent_test_case_id", "executions", ["parent_test_case_id"])

    # assertion_results
    op.create_table(
        "assertion_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("assertion_type", sa.String(), nullable=False),
        sa.Column("assertion_config", sa.JSON(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("actual", sa.JSON(), nullable=True),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assertion_results_execution_id", "assertion_results", ["execution_id"])

    # health_check_runs
    op.create_table(
        "health_check_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("health_check_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["health_check_id"], ["health_checks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_health_check_runs_health_check_id", "health_check_runs", ["health_check_id"])
    op.create_index("ix_health_check_runs_project_id", "health_check_runs", ["project_id"])

    with op.batch_alter_table("executions") as b:
        b.create_foreign_key("fk_executions_parent_check_run_id", "health_check_runs", ["parent_check_run_id"], ["id"], ondelete="SET NULL")

    # campaign_jobs
    op.create_table(
        "campaign_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("lease_owner", sa.String(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_test_cursor", sa.JSON(), nullable=True),
        sa.Column("recovery_uncertain_execution_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recovery_uncertain_execution_id"], ["executions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id"),
    )
    op.create_index("ix_campaign_jobs_campaign_id", "campaign_jobs", ["campaign_id"])
    op.create_index("ix_campaign_jobs_lease_expires_at", "campaign_jobs", ["lease_expires_at"])

    # campaign_events
    op.create_table(
        "campaign_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaign_events_campaign_id_created_at", "campaign_events", ["campaign_id", "created_at"])

    # evidence_references
    op.create_table(
        "evidence_references",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("provenance", sa.String(), nullable=False),
        sa.Column("excerpt", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_references_project_id", "evidence_references", ["project_id"])

    # findings
    op.create_table(
        "findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("machine_severity", sa.String(), nullable=False, server_default="info"),
        sa.Column("triage_status", sa.String(), nullable=False, server_default="new"),
        sa.Column("user_severity", sa.String(), nullable=True),
        sa.Column("user_notes", sa.Text(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_findings_project_id", "findings", ["project_id"])


def downgrade() -> None:
    op.drop_table("findings")
    op.drop_table("evidence_references")
    op.drop_table("campaign_events")
    op.drop_table("campaign_jobs")
    op.drop_table("health_check_runs")
    op.drop_table("assertion_results")
    op.drop_table("executions")
    op.drop_table("test_cases")
    op.drop_table("health_checks")
    op.drop_table("knowledge_facts")
    op.drop_table("saved_requests")
    op.drop_table("api_operations")
    op.drop_table("campaigns")
    op.drop_table("api_specifications")
    op.drop_table("environment_variables")
    op.drop_table("environments")
    op.drop_table("collections")
    op.drop_table("projects")
    op.drop_table("sessions")
    op.drop_table("users")
