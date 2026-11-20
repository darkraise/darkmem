"""code_edges: index the file segment of each edge key

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-21

Removing a file's edges matches `split_part(source_key, '::', 2)` and the
target twin against the file paths a run rewrites or deletes; without an
expression index each such delete scans every edge of the repository.

Additive only: two indexes on an existing table, no row touched, so it
upgrades a populated database in place.
"""
from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_code_edges_source_file "
        "ON code_edges (repo_id, split_part(source_key, '::', 2))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_code_edges_target_file "
        "ON code_edges (repo_id, split_part(target_key, '::', 2))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_code_edges_target_file")
    op.execute("DROP INDEX IF EXISTS ix_code_edges_source_file")
