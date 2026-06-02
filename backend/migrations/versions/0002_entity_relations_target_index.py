"""index entity_relations.target_entity_id

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-02

The unique constraint on (source_entity_id, target_entity_id, rel_type) leads
with source_entity_id, so reverse lookups by target_entity_id had no usable
index. Three hot paths filter/join on target_entity_id — the neighbor query
(`WHERE source_entity_id = :id OR target_entity_id = :id`), get_relations_between,
and the orphan-entity guard inside delete_by_memory_id (run on every memory
write) — and all fell back to sequential scans of entity_relations. This index
lets the target_entity_id arm of those predicates use a bitmap-OR index scan.
"""
from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_entity_relations_target', 'entity_relations', ['target_entity_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_entity_relations_target', table_name='entity_relations')
