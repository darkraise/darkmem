"""memory metadata v2: status, project, technologies, confidence, superseded_by

Adds five columns to ``memories`` to support the 5-type coding schema
retrieval (see ``fine-tuning/SCHEMA_V2_PLAN.md``):

  - ``project``        text, default 'default', retrieval filter
  - ``status``         enum memory_status, default 'active', retrieval filter
  - ``superseded_by``  uuid, set by the REPLACES detector
  - ``technologies``   text[] of tech entity names, retrieval filter (GIN)
  - ``confidence``     real, default 0.75, rank-fusion weight

A CHECK constraint enforces that a superseded memory always names its
successor. Downgrade drops everything cleanly.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-19
"""
from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE memory_status AS ENUM ('active', 'deprecated', 'superseded')"
    )

    op.add_column(
        "memories",
        sa.Column("project", sa.Text(), nullable=False, server_default="default"),
    )
    op.add_column(
        "memories",
        sa.Column(
            "status",
            pg.ENUM(
                "active",
                "deprecated",
                "superseded",
                name="memory_status",
                create_type=False,
            ),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "memories",
        sa.Column("superseded_by", pg.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "memories",
        sa.Column(
            "technologies",
            pg.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "memories",
        sa.Column("confidence", sa.REAL(), nullable=False, server_default="0.75"),
    )

    op.create_foreign_key(
        "fk_memories_superseded_by",
        "memories",
        "memories",
        ["superseded_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_memories_project", "memories", ["project"])
    op.create_index("ix_memories_status", "memories", ["status"])
    op.create_index(
        "ix_memories_technologies",
        "memories",
        ["technologies"],
        postgresql_using="gin",
    )

    # Invariant: a superseded memory must point to its successor.
    op.execute(
        "ALTER TABLE memories ADD CONSTRAINT chk_superseded_has_pointer "
        "CHECK (status != 'superseded' OR superseded_by IS NOT NULL)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE memories DROP CONSTRAINT chk_superseded_has_pointer")
    op.drop_index("ix_memories_technologies", table_name="memories")
    op.drop_index("ix_memories_status", table_name="memories")
    op.drop_index("ix_memories_project", table_name="memories")
    op.drop_constraint("fk_memories_superseded_by", "memories", type_="foreignkey")
    op.drop_column("memories", "confidence")
    op.drop_column("memories", "technologies")
    op.drop_column("memories", "superseded_by")
    op.drop_column("memories", "status")
    op.drop_column("memories", "project")
    op.execute("DROP TYPE memory_status")
