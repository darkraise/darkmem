"""drop regex classification columns

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-18

The zero-LLM regex classifier was removed; LLM classification now runs
unconditionally and writes the ``llm_*`` columns. Its display-only output
columns ``classified_type`` / ``classified_confidence`` have no remaining
writer or reader, so they are dropped. Downgrade re-adds them as the nullable
columns they were, but cannot recover the historical regex values.
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('memories', 'classified_confidence')
    op.drop_column('memories', 'classified_type')


def downgrade() -> None:
    op.add_column('memories', sa.Column('classified_type', sa.String(50), nullable=True))
    op.add_column('memories', sa.Column('classified_confidence', sa.Float(), nullable=True))
