"""mcp_tool_calls: one row per MCP ``tools/call``

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-05

The MCP door journalled its writes into ``events`` but kept no record of reads,
so nothing could answer "which data did this client ask for, and when". This
table is that record. It is deliberately **not** ``events``: read traffic is
orders of magnitude busier than writes and needs an age-based retention sweep
(``mcp_call_cleanup``), which the append-only journal forbids by trigger.

Rows carry the tool, the key and client that called it, timing, outcome, a
minimised argument summary and the ids the call returned. Query text is
recorded only when the operator turns it on (the job's ``log_query_text``);
content arguments are never stored, only their size (write-time minimisation).

Additive only: a new table and its indexes, no existing row touched, so it
upgrades a populated database in place.
"""
from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE mcp_tool_calls (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            occurred_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            tool          TEXT NOT NULL,
            scope         TEXT,
            status        TEXT NOT NULL,
            duration_ms   INTEGER NOT NULL DEFAULT 0,
            api_key_id    UUID REFERENCES api_keys(id) ON DELETE SET NULL,
            key_name      TEXT,
            client        TEXT,
            project       TEXT,
            arguments     JSONB NOT NULL DEFAULT '{}'::jsonb,
            result_count  INTEGER,
            result_ids    TEXT[] NOT NULL DEFAULT '{}',
            error         TEXT,
            CONSTRAINT chk_mcp_tool_calls_status
                CHECK (status IN ('ok', 'error', 'denied'))
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_mcp_tool_calls_occurred ON mcp_tool_calls (occurred_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_mcp_tool_calls_tool_occurred "
        "ON mcp_tool_calls (tool, occurred_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_mcp_tool_calls_key_occurred "
        "ON mcp_tool_calls (api_key_id, occurred_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mcp_tool_calls")
