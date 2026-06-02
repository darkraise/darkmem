"""reset code graph for owner-qualified symbol keys

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-02

Symbol graph keys gained an optional owner segment
(``name::file_path::owner``) so two same-named methods of different classes in
one file no longer collapse onto a single ``name::file_path`` node. Every key
already stored in ``code_edges`` / ``code_graph_nodes`` predates that change, so
a method node and its inbound/outbound call, override and has_method edges are
keyed inconsistently with what the pipeline now writes. Reads that compose an
owner-qualified key (blast radius, symbol context, the graph view) would miss
those stale rows.

The graph is fully derived from ``code_symbols`` and re-parsed on every index,
so the safe reset is to drop the derived rows and null each repo's
``last_indexed_commit``. The next sync (or manual reindex) then runs a full
file discovery and rebuilds the whole graph with owner-qualified keys.
"""
from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _reset_graph() -> None:
    op.execute("DELETE FROM code_edges")
    op.execute("DELETE FROM code_graph_nodes")
    op.execute("UPDATE repositories SET last_indexed_commit = NULL")


def upgrade() -> None:
    _reset_graph()


def downgrade() -> None:
    # The keyspace change is not reversible by data alone; clearing the derived
    # graph and forcing a full reindex is the only coherent rollback.
    _reset_graph()
