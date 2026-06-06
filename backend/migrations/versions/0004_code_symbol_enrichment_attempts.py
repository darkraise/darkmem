"""code_symbols.enrichment_attempts

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-06

Adds a bounded retry counter so a transient LLM failure during symbol
enrichment no longer permanently strands a symbol in the terminal 'failed'
state. The worker increments this on a caught exception and only marks the
symbol 'failed' once it crosses the attempt cap; until then the symbol stays
'pending' and is retried on a later batch.
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'code_symbols',
        sa.Column('enrichment_attempts', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('code_symbols', 'enrichment_attempts')
