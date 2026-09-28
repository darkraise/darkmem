"""Daily retention for the work log (spec §6).

Closed workstreams past the window go, their entries and vectors with them
through the cascade; open and retained ones stay however old. One transaction
per workstream, so a journal failure stops the sweep with every earlier erase
journalled and committed and nothing of the failed one removed.
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services import worklog
from app.services.job_registry import FieldDescriptor

logger = logging.getLogger(__name__)

WORKLOG_CLEANUP_JOB_KEY = "worklog_cleanup"
# Nightly, after both backup producers start (03:30 timer, 04:30 backup_ship).
# Overlapping a long backup_ship run is harmless: pg_dump reads one snapshot.
WORKLOG_CLEANUP_CRON = "15 5 * * *"
RETENTION_DAYS_DEFAULT = 90

WORKLOG_CLEANUP_CONFIG_SCHEMA = [
    FieldDescriptor(
        key="retention_days", label="Retention (days)",
        default=RETENTION_DAYS_DEFAULT, min=1, max=3650,
        help="A closed workstream is deleted with its entries once it has been "
             "closed this long. Open workstreams and those marked retain are "
             "never deleted.",
    ),
]


def make_worklog_cleanup_runner(app, session_factory: async_sessionmaker[AsyncSession]):
    async def run() -> dict | int:
        registry = getattr(app.state, "job_registry", None)
        retention = RETENTION_DAYS_DEFAULT
        if registry is not None:
            cfg = await registry.load_config(WORKLOG_CLEANUP_JOB_KEY)
            retention = int(cfg.config.get("retention_days", RETENTION_DAYS_DEFAULT))

        workstreams = entries = 0
        while True:
            async with session_factory() as session:
                removed = await worklog.expire_next(
                    session, retention_days=retention, actor=WORKLOG_CLEANUP_JOB_KEY,
                )
                if removed is None:
                    break
                await session.commit()
            workstreams += 1
            entries += removed

        if not workstreams:
            # 0, not {}: a nightly sweep with nothing to erase writes no job_runs row.
            return 0
        logger.info(
            "worklog_cleanup: erased %s workstream(s), %s entr(ies), closed over %s days",
            workstreams, entries, retention,
        )
        return {"workstreams": workstreams, "entries": entries, "retention_days": retention}
    return run
