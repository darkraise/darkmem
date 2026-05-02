"""Replace per-job interval_seconds with cron expressions.

Job scheduling moves from a fixed interval to a cron expression, so
operators can express schedules like "every 5 minutes", "every hour
on the hour", "weekdays at 03:00", etc. Five-field expressions carry
standard minute-precision; six-field expressions put the seconds
field first (Quartz convention) for sub-minute schedules.

Migration shape: the four seeded ``job:*`` rows are reset to the new
cron defaults, dropping any operator-modified ``interval_seconds``.
This is a deliberate reset rather than an auto-conversion — the
existing values were almost all defaults, and the new presets are
easier to pick from the UI than to translate from arbitrary integers.

Revision ID: 0004
Revises: 0003
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM config WHERE key LIKE 'job:%'
        """
    )
    op.execute(
        """
        INSERT INTO config (key, value) VALUES
            ('job:repo_sync',
             '{"enabled": true,  "cron": "*/5 * * * *",      "min_interval_seconds": 30, "last_run_at": null, "last_status": null, "last_error": null}'::jsonb),
            ('job:code_enrichment',
             '{"enabled": false, "cron": "*/10 * * * * *",   "min_interval_seconds": 1,  "last_run_at": null, "last_status": null, "last_error": null}'::jsonb),
            ('job:token_blocklist_cleanup',
             '{"enabled": true,  "cron": "0 * * * *",        "min_interval_seconds": 60, "last_run_at": null, "last_status": null, "last_error": null}'::jsonb),
            ('job:pipeline_failure_cleanup',
             '{"enabled": true,  "cron": "0 * * * *",        "min_interval_seconds": 60, "last_run_at": null, "last_status": null, "last_error": null}'::jsonb)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM config WHERE key LIKE 'job:%'
        """
    )
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
        """
    )
