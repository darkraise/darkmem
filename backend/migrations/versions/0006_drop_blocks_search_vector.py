"""blocks: drop the unread keyword column and its GIN index

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-21

`blocks.search_vector` is a stored generated tsvector that no query reads:
document and page retrieval is cosine-only. Every block write still paid to
compute it and keep `ix_blocks_search_vector` current. Dropping a generated
column touches no other column, so every block row and its `text` survive.

The downgrade re-adds both with the baseline's definitions; re-adding a
stored generated column rewrites the table.
"""
from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_blocks_search_vector")
    op.execute("ALTER TABLE blocks DROP COLUMN IF EXISTS search_vector")


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE blocks ADD COLUMN IF NOT EXISTS search_vector TSVECTOR
            GENERATED ALWAYS AS (
                to_tsvector(
                    'english',
                    CASE WHEN type IN ('code', 'html') THEN '' ELSE coalesce(text, '') END
                )
            ) STORED
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_blocks_search_vector ON blocks USING GIN (search_vector)"
    )
