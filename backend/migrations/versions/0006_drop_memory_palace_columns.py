"""drop dead wing/room/hall columns

The memory-palace hierarchy (wing, room, hall) shipped in 0001 as a
spatial-navigation metaphor but was never wired into the ingest pipeline.
No code path ever wrote values, so every row carried NULLs. The schema-v2
filter set (project, memory_type, technologies, status) covers the same
structured-filter use cases, so the columns are dead weight.

Downgrade reinstates the three nullable columns as-is, matching the 0001
schema, but the data is gone. Taking a pre-migration pg_dump is cheap
insurance if there's any chance the column was populated externally.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-19
"""
from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("memories", "hall")
    op.drop_column("memories", "room")
    op.drop_column("memories", "wing")


def downgrade() -> None:
    op.add_column("memories", sa.Column("wing", sa.String(length=100), nullable=True))
    op.add_column("memories", sa.Column("room", sa.String(length=100), nullable=True))
    op.add_column("memories", sa.Column("hall", sa.String(length=50), nullable=True))
