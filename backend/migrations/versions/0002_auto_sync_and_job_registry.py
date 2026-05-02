"""Auto-sync rename + job registry seed.

- Renames ``repositories.is_active`` to ``repositories.auto_sync`` so the
  column reads as the operational concept (does the periodic loop pull
  this repo?) rather than a generic activity flag.
- Drops ``repositories.sync_interval_minutes``. Per-repo intervals are
  removed in favour of a single tunable interval per background job
  (configured via the new job registry).
- Seeds four ``Config`` rows under ``job:<key>`` with the default
  enabled / interval values for the migrated periodic loops:

    * ``job:repo_sync``                 — every 300s, enabled
    * ``job:code_enrichment``           — every 10s, disabled (matches
      legacy ``enrichment_config.enabled=false`` default)
    * ``job:token_blocklist_cleanup``   — every 3600s, enabled
    * ``job:pipeline_failure_cleanup``  — every 3600s, enabled

  These rows are the source of truth the registry reads at boot. The
  job_registry service writes them back on PUT and on every loop tick.

Revision ID: 0002
Revises: 0001
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("repositories", "is_active", new_column_name="auto_sync")
    op.drop_column("repositories", "sync_interval_minutes")

    op.execute(
        """
        INSERT INTO config (key, value) VALUES
            ('job:repo_sync',
             '{"enabled": true,  "interval_seconds": 300, "min_interval_seconds": 30,  "last_run_at": null, "last_status": null, "last_error": null}'::jsonb),
            ('job:code_enrichment',
             '{"enabled": false, "interval_seconds": 10,  "min_interval_seconds": 1,   "last_run_at": null, "last_status": null, "last_error": null}'::jsonb),
            ('job:token_blocklist_cleanup',
             '{"enabled": true,  "interval_seconds": 3600,"min_interval_seconds": 60,  "last_run_at": null, "last_status": null, "last_error": null}'::jsonb),
            ('job:pipeline_failure_cleanup',
             '{"enabled": true,  "interval_seconds": 3600,"min_interval_seconds": 60,  "last_run_at": null, "last_status": null, "last_error": null}'::jsonb)
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM config WHERE key LIKE 'job:%'")
    op.add_column(
        "repositories",
        sa.Column(
            "sync_interval_minutes",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
    )
    op.alter_column(
        "repositories", "sync_interval_minutes", server_default=None,
    )
    op.alter_column("repositories", "auto_sync", new_column_name="is_active")
