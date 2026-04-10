"""pipeline failures tracking

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-10

Adds:
  - pipeline_failures table with polymorphic (entity_type, entity_id) reference
  - Partial unique index on unresolved rows for upsert semantics
  - Secondary indexes on pipeline_name and resolved_at
"""
from collections.abc import Sequence
from typing import Union

from alembic import op


revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE pipeline_failures (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type VARCHAR(50) NOT NULL,
            entity_id UUID NOT NULL,
            pipeline_name VARCHAR(50) NOT NULL,
            failed_step VARCHAR(100) NOT NULL,
            error_message TEXT,
            attempts INTEGER NOT NULL DEFAULT 1,
            first_failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            resolved_at TIMESTAMPTZ,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX idx_pipeline_failures_unresolved
        ON pipeline_failures(entity_type, entity_id, pipeline_name)
        WHERE resolved_at IS NULL
    """)

    op.execute("""
        CREATE INDEX idx_pipeline_failures_pipeline_name
        ON pipeline_failures(pipeline_name)
        WHERE resolved_at IS NULL
    """)

    op.execute("""
        CREATE INDEX idx_pipeline_failures_resolved_at
        ON pipeline_failures(resolved_at)
        WHERE resolved_at IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_pipeline_failures_resolved_at")
    op.execute("DROP INDEX IF EXISTS idx_pipeline_failures_pipeline_name")
    op.execute("DROP INDEX IF EXISTS idx_pipeline_failures_unresolved")
    op.execute("DROP TABLE IF EXISTS pipeline_failures")
