"""index for the enrichment drain query

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-07

The enrichment drain query
(``WHERE enrichment_status='pending' ORDER BY enrichment_attempts ASC,
enrichment_priority DESC LIMIT n``) full-scanned and sorted ``code_symbols`` on
every iteration — up to ~200 iterations per reindex. A partial index keyed on the
sort columns over just the pending rows serves it directly and stays tiny because
it only covers the pending backlog.

(An earlier draft of this migration also added a btree on ``entities.entity_type``
on the theory it would speed the type-filtered dedup probe in
``find_similar_entity``. Review showed that query is driven by the HNSW vector
index on the per-fingerprint embeddings partition and applies ``entity_type`` as a
post-join filter on a primary-key-fetched row, so a standalone btree there is not a
usable access path. It was dropped rather than ship a write-cost index with no
matching read path.)
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_code_symbols_enrichment_pending',
        'code_symbols',
        [sa.text('enrichment_attempts'), sa.text('enrichment_priority DESC')],
        postgresql_where=sa.text("enrichment_status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index('ix_code_symbols_enrichment_pending', table_name='code_symbols')
