"""entity embedding cache and model fingerprint columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-10

Adds:
  - entity_embedding_cache table (name_lower + model_fingerprint composite PK)
  - model_fingerprint column on memory_embeddings, code_chunk_embeddings, entities
"""
from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE entity_embedding_cache (
            name_lower VARCHAR(255) NOT NULL,
            model_fingerprint VARCHAR(100) NOT NULL,
            embedding vector(1024) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            hit_count INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (name_lower, model_fingerprint)
        )
    """)
    op.execute("CREATE INDEX ix_entity_embedding_cache_last_used ON entity_embedding_cache(last_used_at)")

    op.add_column('memory_embeddings', sa.Column('model_fingerprint', sa.String(100), nullable=True))
    op.add_column('code_chunk_embeddings', sa.Column('model_fingerprint', sa.String(100), nullable=True))
    op.execute("ALTER TABLE entities ADD COLUMN model_fingerprint VARCHAR(100)")


def downgrade() -> None:
    op.execute("ALTER TABLE entities DROP COLUMN IF EXISTS model_fingerprint")
    op.drop_column('code_chunk_embeddings', 'model_fingerprint')
    op.drop_column('memory_embeddings', 'model_fingerprint')
    op.execute("DROP INDEX IF EXISTS ix_entity_embedding_cache_last_used")
    op.execute("DROP TABLE IF EXISTS entity_embedding_cache")
