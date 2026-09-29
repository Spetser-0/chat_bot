"""Initial schema — all Spetser AI tables

Revision ID: 0001
Revises: 
Create Date: 2026-09-28

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── students ─────────────────────────────────────────────────────────────
    op.create_table(
        "students",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("external_auth_id", sa.String(255), unique=True, nullable=True),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("phone_number", sa.String(30), nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="student"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("credit_balance", sa.Float, nullable=False, server_default="100.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_students_email", "students", ["email"])
    op.create_index("ix_students_external_auth_id", "students", ["external_auth_id"])
    op.create_index("ix_students_role", "students", ["role"])

    # ── prompt_versions ───────────────────────────────────────────────────────
    op.create_table(
        "prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("feature_key", sa.String(50), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("change_note", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="SET NULL"), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_prompt_versions_feature_key", "prompt_versions", ["feature_key"])
    op.create_index("ix_prompt_versions_status", "prompt_versions", ["status"])

    # ── requests ──────────────────────────────────────────────────────────────
    op.create_table(
        "requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature", sa.String(50), nullable=False),
        sa.Column("intent", sa.String(50), nullable=True),
        sa.Column("model_tier", sa.String(20), nullable=False, server_default="default"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("request_payload_hash", sa.String(64), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("resolved_provider", sa.String(100), nullable=True),
        sa.Column("resolved_model", sa.String(100), nullable=True),
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("display_title", sa.String(500), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_requests_student_id", "requests", ["student_id"])
    op.create_index("ix_requests_feature", "requests", ["feature"])
    op.create_index("ix_requests_status", "requests", ["status"])
    op.create_index("ix_requests_idempotency_key", "requests", ["idempotency_key"])
    # Uniqueness: one idempotency key per student (partial — only non-null keys)
    op.create_index(
        "uq_requests_student_idempotency",
        "requests",
        ["student_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    # ── deliverables ─────────────────────────────────────────────────────────
    op.create_table(
        "deliverables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("storage_object_key", sa.String(1000), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size", sa.BigInteger, nullable=True),
        sa.Column("renderer_version", sa.String(20), nullable=True),
        sa.Column("schema_version", sa.String(20), nullable=True),
        sa.Column("input_hash", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_deliverables_request_id", "deliverables", ["request_id"])
    op.create_index("ix_deliverables_student_id", "deliverables", ["student_id"])

    # ── source_records ────────────────────────────────────────────────────────
    op.create_table(
        "source_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("deliverable_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deliverables.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_text", sa.Text, nullable=False),
        sa.Column("citation_text", sa.Text, nullable=False),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="unverified"),
        sa.Column("source_metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_source_records_deliverable_id", "source_records", ["deliverable_id"])

    # ── credit_ledger ─────────────────────────────────────────────────────────
    op.create_table(
        "credit_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(100), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("computed_usd_cost", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("pricing_version", sa.String(50), nullable=True),
        sa.Column("credits_charged", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("idempotency_key", sa.String(255), unique=True, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_credit_ledger_student_id", "credit_ledger", ["student_id"])
    op.create_index("ix_credit_ledger_request_id", "credit_ledger", ["request_id"])
    op.create_index("ix_credit_ledger_idempotency_key", "credit_ledger", ["idempotency_key"])

    # ── model_providers ───────────────────────────────────────────────────────
    op.create_table(
        "model_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider_key", sa.String(100), unique=True, nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("secret_reference", sa.String(500), nullable=True),
        sa.Column("health_status", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_model_providers_provider_key", "model_providers", ["provider_key"])

    # ── model_configurations ──────────────────────────────────────────────────
    op.create_table(
        "model_configurations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("capabilities_json", postgresql.JSONB, nullable=True),
        sa.Column("input_price_per_1k_tokens", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("output_price_per_1k_tokens", sa.Numeric(18, 8), nullable=False, server_default="0"),
        sa.Column("pricing_version", sa.String(50), nullable=True),
        sa.Column("max_tokens", sa.Integer, nullable=True),
        sa.Column("context_window", sa.Integer, nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("fallback_priority", sa.Integer, nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_model_configurations_provider_id", "model_configurations", ["provider_id"])
    op.create_index("ix_model_configurations_tier", "model_configurations", ["tier"])

    # ── feature_configurations ────────────────────────────────────────────────
    op.create_table(
        "feature_configurations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("feature_key", sa.String(50), unique=True, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("default_tier", sa.String(20), nullable=False, server_default="default"),
        sa.Column("active_prompt_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("response_schema_key", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_feature_configurations_feature_key", "feature_configurations", ["feature_key"])

    # ── routing_rules ─────────────────────────────────────────────────────────
    op.create_table(
        "routing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("feature_key", sa.String(50), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("primary_model_configuration_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_configurations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fallback_model_configuration_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="1"),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="60"),
        sa.Column("temperature", sa.Float, nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_routing_rules_feature_key", "routing_rules", ["feature_key"])

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("routing_rules")
    op.drop_table("feature_configurations")
    op.drop_table("model_configurations")
    op.drop_table("model_providers")
    op.drop_table("credit_ledger")
    op.drop_table("source_records")
    op.drop_table("deliverables")
    op.drop_table("requests")
    op.drop_table("prompt_versions")
    op.drop_table("students")
