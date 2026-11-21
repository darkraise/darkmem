"""embedder partitions: drop the unused triple-embeddings children

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-21

The registry no longer has a fact-vector family, yet every fingerprint
registered before this revision carries a `triple_embeddings__<slug>` table
and its indexes. Nothing ever wrote one in production, so each is dropped
when it holds no row. A table that does hold rows is kept and named in the
migration log, for its owner to inspect: this revision never deletes data.

The baseline created no `triple_embeddings` parent, only these per-fingerprint
children, so there is no parent to drop.
"""
import logging
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    bind = op.get_bind()
    quote = bind.dialect.identifier_preparer.quote
    names = bind.execute(sa.text(
        "SELECT tablename FROM pg_tables WHERE schemaname = current_schema() "
        "AND tablename LIKE 'triple\\_embeddings\\_\\_%' ORDER BY tablename"
    )).scalars().all()
    for name in names:
        rows = bind.execute(sa.text(f"SELECT count(*) FROM {quote(name)}")).scalar_one()
        if rows == 0:
            op.execute(f"DROP TABLE {quote(name)}")
        else:
            logger.info("kept %s rows=%d", name, rows)


def downgrade() -> None:
    # Recreates nothing: the registry that would own these tables is gone,
    # and an empty table restored here would have no writer or reader.
    pass
