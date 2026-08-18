"""ORM model for job run history.

Deliberately **not** the ``events`` table. That is the audit substrate:
append-only by trigger, permanent by ruling (doc 04 §8.1), and doc 17 §5.1's
verification metrics are SQL over it alone. Job telemetry is the opposite
shape — high volume, individually near-worthless, and it wants pruning. One
five-second job wrote ~17k rows a day into a table nothing can delete from,
which is what sent this to its own home.

Here DELETE is ordinary, so ``job_run_cleanup`` can hold the table to a
configured ceiling.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class JobRun(Base):
    """One completed run of one registered job, scheduled or manual."""

    __tablename__ = "job_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    job_key: Mapped[str] = mapped_column(String(128), nullable=False)
    #: ``ok`` | ``error``. Never null — a run that finished has an outcome.
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    #: Whether the run was a manual trigger rather than a scheduled tick.
    trigger: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'schedule'"))
    #: The failure reason, truncated by the writer. Null on a clean run.
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: What the runner reported doing — counts, ids, whatever it returns.
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    __table_args__ = (
        # The history dialog reads one job, newest first, and the cleanup job
        # trims oldest-first across all jobs.
        Index("ix_job_runs_key_started", "job_key", started_at.desc()),
        Index("ix_job_runs_started", "started_at"),
    )
