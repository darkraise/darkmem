"""board_views: the progress board's saved views

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-13

A saved view is layout, not data: a name, a position among the project's
views and a definition (layout, grouping, filters, sort, columns) validated
against a closed schema at the door before it reaches the CHECK below. The
two built-in views are code constants (`app.services.board_views`) and never
rows. Views journal nothing.

Additive only: a new table, its trigger and its constraints, no existing row
touched, so it upgrades a populated database in place.
"""
from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE board_views (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project     TEXT NOT NULL,
            name        TEXT NOT NULL,
            position    INTEGER NOT NULL,
            definition  JSONB NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ux_board_views_project_name UNIQUE (project, name),
            CONSTRAINT chk_board_views_name_len CHECK (char_length(name) BETWEEN 1 AND 100),
            CONSTRAINT chk_board_views_definition_size
                CHECK (pg_column_size(definition) <= 16384)
        )
        """
    )
    op.execute(
        "CREATE TRIGGER board_views_touch_updated_at BEFORE UPDATE "
        "ON board_views FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS board_views")
