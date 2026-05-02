"""ML profiles + per-purpose constraint on LLM profiles.

Three changes, all in service of the new "Darkmem ML Profiles" Settings
tab and the per-purpose dropdown filter on the Pipeline page:

- Creates ``ml_profiles`` (id, name, model_repo, ttl_seconds, …). One
  row will be inserted at app startup from ``app.services.ml_seed``
  (no INSERTs in this migration — keeps with the no-seed-in-migration
  rule established in commit b09e461).
- Adds a nullable ``purpose`` column to ``llm_profiles`` so the
  Pipeline page can filter the dropdown to profiles whose purpose
  matches the row. The column is nullable rather than NOT NULL because
  legacy rows pre-dating this column have no obvious purpose for the
  multi-purpose seeded profiles like ``openai-extraction`` (they map
  to one purpose by name suffix). A best-effort backfill assigns the
  purpose from the trailing token of the profile name.
- Adds nullable ``ml_profile_id`` FK on ``llm_purpose_configs`` so
  the classifier purpose row can point at an ML profile instead of an
  LLM profile. The pipeline's classifier dispatch picks the ML path
  whenever this column is set.

Revision ID: 0003
Revises: 0002
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ml_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("model_repo", sa.String(512), nullable=False),
        sa.Column("ttl_seconds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )

    op.add_column(
        "llm_profiles",
        sa.Column("purpose", sa.String(32), nullable=True),
    )
    # Best-effort backfill: trailing token of the profile name maps to a
    # known purpose. Profiles whose names don't fit this convention
    # (legacy operator-created rows) stay NULL and the user picks a
    # purpose explicitly via the new add-dialog.
    op.execute(
        """
        UPDATE llm_profiles SET purpose = 'embedding'
            WHERE purpose IS NULL
              AND (name ~* '(^|-)embedding(-|$)' OR is_embedding = TRUE)
        """
    )
    op.execute(
        """
        UPDATE llm_profiles SET purpose = 'extraction'
            WHERE purpose IS NULL AND name ~* '(^|-)extraction(-|$)'
        """
    )
    op.execute(
        """
        UPDATE llm_profiles SET purpose = 'classification'
            WHERE purpose IS NULL AND name ~* '(^|-)classification(-|$)'
        """
    )
    op.execute(
        """
        UPDATE llm_profiles SET purpose = 'reasoning'
            WHERE purpose IS NULL
              AND (name ~* '(^|-)reasoning(-|$)' OR reasoning = TRUE)
        """
    )
    op.execute(
        """
        UPDATE llm_profiles SET purpose = 'summarization'
            WHERE purpose IS NULL AND name ~* '(^|-)summarization(-|$)'
        """
    )
    op.execute(
        """
        UPDATE llm_profiles SET purpose = 'reranker'
            WHERE purpose IS NULL AND name ~* '(^|-)reranker(-|$)'
        """
    )

    op.add_column(
        "llm_purpose_configs",
        sa.Column(
            "ml_profile_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ml_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("llm_purpose_configs", "ml_profile_id")
    op.drop_column("llm_profiles", "purpose")
    op.drop_table("ml_profiles")
