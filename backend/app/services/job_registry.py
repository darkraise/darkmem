"""Background-job registry.

Replaces the per-loop ``asyncio.create_task(periodic_X())`` pattern in
``app.main`` with a unified registry: each periodic job is described
by a ``Job`` dataclass and dispatched via ``JobRegistry.start()``.
The registry persists per-job config (enabled, cron) in the
``config`` table under keys of the form ``job:<key>`` and exposes
read / write / trigger operations consumed by the ``/api/v1/jobs``
routes.

Scheduling shape: each job runs on a cron expression. Five-field
expressions (``*/5 * * * *``) carry the standard minute-precision
semantics. Six-field expressions put the seconds field first
(``*/10 * * * * *`` = every ten seconds), matching the Quartz
convention. ``min_interval_seconds`` is a per-job floor that
protects against runaway expressions; the loop will not fire more
often than this regardless of what the cron computes.

Persistence shape — each job has a ``config`` row keyed
``job:<key>`` with JSON value::

    {
        "enabled": bool,
        "cron": "*/5 * * * *",
        "min_interval_seconds": int,
        "last_run_at": "ISO8601 string" | null,
        "last_status": "ok" | "error" | null,
        "last_error": "<short message>" | null,
    }

Manual trigger semantics: ``trigger(key)`` schedules an out-of-band
run that does NOT wait for the next tick and does NOT conflict with
the loop — it acquires the same per-job ``asyncio.Lock`` the loop
uses, runs the job's ``runner``, and records the outcome.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable

from croniter import croniter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.config import Config

logger = logging.getLogger(__name__)


JobRunner = Callable[[], Awaitable[None]]


def is_valid_cron(expr: str) -> bool:
    """Validate a 5- or 6-field cron expression. Six-field puts the
    seconds field first (Quartz-style)."""
    if not isinstance(expr, str) or not expr.strip():
        return False
    return croniter.is_valid(expr.strip(), second_at_beginning=True)


def next_fire_delta_seconds(expr: str, now: datetime, *, floor: int) -> float:
    """Seconds until the next cron fire, never less than ``floor``."""
    base = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    itr = croniter(expr, base, second_at_beginning=True)
    nxt: datetime = itr.get_next(datetime)
    if nxt.tzinfo is None:
        nxt = nxt.replace(tzinfo=timezone.utc)
    delta = (nxt - base).total_seconds()
    return max(float(floor), delta)


class FieldDescriptor(BaseModel):
    """A single per-job config field the UI renders generically."""
    key: str
    type: str = "int"
    label: str
    default: int
    min: int | None = None
    max: int | None = None
    step: int | None = 1
    help: str | None = None


@dataclass
class JobConfig:
    enabled: bool
    cron: str
    min_interval_seconds: int
    last_run_at: datetime | None = None
    last_status: str | None = None
    last_error: str | None = None
    config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "cron": self.cron,
            "min_interval_seconds": self.min_interval_seconds,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobConfig":
        last_run = data.get("last_run_at")
        return cls(
            enabled=bool(data.get("enabled", False)),
            cron=str(data.get("cron", "*/5 * * * *")),
            min_interval_seconds=int(data.get("min_interval_seconds", 1)),
            last_run_at=datetime.fromisoformat(last_run) if last_run else None,
            last_status=data.get("last_status"),
            last_error=data.get("last_error"),
            config=data.get("config") or {},
        )


@dataclass
class Job:
    key: str
    display_name: str
    description: str
    default_cron: str
    min_interval_seconds: int
    runner: JobRunner
    config_schema: list[FieldDescriptor] = field(default_factory=list)
    # Live wiring filled in by the registry at start().
    task: asyncio.Task | None = field(default=None, init=False, repr=False)
    wakeup: asyncio.Event = field(default_factory=asyncio.Event, init=False, repr=False)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    @property
    def default_config(self) -> dict:
        return {fd.key: fd.default for fd in self.config_schema}


class JobRegistry:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._jobs: dict[str, Job] = {}
        self._stopped = False

    # ── registration ────────────────────────────────────────────────

    def register(self, job: Job) -> None:
        if job.key in self._jobs:
            raise ValueError(f"Job {job.key!r} already registered")
        if not is_valid_cron(job.default_cron):
            raise ValueError(
                f"Job {job.key!r} default_cron {job.default_cron!r} is not a "
                f"valid 5- or 6-field cron expression"
            )
        self._jobs[job.key] = job

    def keys(self) -> list[str]:
        return list(self._jobs.keys())

    def get(self, key: str) -> Job | None:
        return self._jobs.get(key)

    # ── persistence ─────────────────────────────────────────────────

    @staticmethod
    def _config_key(job_key: str) -> str:
        return f"job:{job_key}"

    async def load_config(self, key: str) -> JobConfig:
        async with self._session_factory() as session:
            row = (await session.execute(
                select(Config).where(Config.key == self._config_key(key))
            )).scalar_one_or_none()
        job = self._jobs.get(key)
        if row and isinstance(row.value, dict) and "cron" in row.value:
            return JobConfig.from_dict(row.value)
        # Synthesize a default if the row is missing or pre-cron — keeps
        # tests and fresh installs happy without forcing the migration to
        # be the only path that creates these rows.
        return JobConfig(
            enabled=True,
            cron=job.default_cron if job else "*/5 * * * *",
            min_interval_seconds=job.min_interval_seconds if job else 1,
        )

    async def save_config(self, key: str, cfg: JobConfig) -> None:
        async with self._session_factory() as session:
            row = (await session.execute(
                select(Config).where(Config.key == self._config_key(key))
            )).scalar_one_or_none()
            if row is None:
                session.add(Config(key=self._config_key(key), value=cfg.to_dict()))
            else:
                row.value = cfg.to_dict()
            await session.commit()

    async def list_with_config(self) -> list[dict]:
        keys = [self._config_key(k) for k in self._jobs]
        async with self._session_factory() as session:
            rows = (await session.execute(
                select(Config).where(Config.key.in_(keys))
            )).scalars().all()
        by_key = {row.key: row.value for row in rows if isinstance(row.value, dict)}

        out: list[dict] = []
        for key, job in self._jobs.items():
            value = by_key.get(self._config_key(key))
            if value and "cron" in value:
                cfg = JobConfig.from_dict(value)
            else:
                cfg = JobConfig(
                    enabled=True,
                    cron=job.default_cron,
                    min_interval_seconds=job.min_interval_seconds,
                )
            running = job.task is not None and not job.task.done()
            out.append({
                "key": job.key,
                "display_name": job.display_name,
                "description": job.description,
                "default_cron": job.default_cron,
                "min_interval_seconds": job.min_interval_seconds,
                "running": running,
                **cfg.to_dict(),
            })
        return out

    # ── lifecycle ───────────────────────────────────────────────────

    async def start_all(self) -> None:
        for key in self._jobs:
            await self._restart_loop(key)

    async def stop_all(self) -> None:
        self._stopped = True
        for job in self._jobs.values():
            if job.task is not None and not job.task.done():
                job.task.cancel()
        for job in self._jobs.values():
            if job.task is not None:
                try:
                    await job.task
                except (asyncio.CancelledError, Exception):
                    pass
                job.task = None

    async def _restart_loop(self, key: str) -> None:
        """Cancel any existing task for ``key`` and start a fresh loop
        if the job is currently enabled."""
        job = self._jobs[key]
        if job.task is not None and not job.task.done():
            job.task.cancel()
            try:
                await job.task
            except (asyncio.CancelledError, Exception):
                pass
            job.task = None

        cfg = await self.load_config(key)
        if not cfg.enabled:
            logger.info("Job %s disabled — not starting loop", key)
            return
        job.task = asyncio.create_task(self._loop(key))

    # ── loop ────────────────────────────────────────────────────────

    async def _loop(self, key: str) -> None:
        job = self._jobs[key]
        logger.info("Job %s loop started", key)
        try:
            while not self._stopped:
                cfg = await self.load_config(key)
                if not cfg.enabled:
                    logger.info("Job %s disabled mid-loop, exiting", key)
                    return
                try:
                    delta = next_fire_delta_seconds(
                        cfg.cron,
                        datetime.now(timezone.utc),
                        floor=cfg.min_interval_seconds,
                    )
                except Exception as exc:
                    logger.error(
                        "Job %s cron %r is invalid; sleeping %ss before retry: %s",
                        key, cfg.cron, cfg.min_interval_seconds, exc,
                    )
                    delta = float(cfg.min_interval_seconds)
                try:
                    await asyncio.wait_for(job.wakeup.wait(), timeout=delta)
                except asyncio.TimeoutError:
                    pass
                job.wakeup.clear()
                if self._stopped:
                    return
                await self._run_once(key)
        except asyncio.CancelledError:
            logger.info("Job %s loop cancelled", key)
            raise

    async def _run_once(self, key: str) -> None:
        job = self._jobs[key]
        async with job.lock:
            cfg = await self.load_config(key)
            cfg.last_run_at = datetime.now(timezone.utc)
            try:
                await job.runner()
                cfg.last_status = "ok"
                cfg.last_error = None
            except Exception as exc:
                cfg.last_status = "error"
                cfg.last_error = str(exc)[:500]
                logger.exception("Job %s runner raised", key)
            await self.save_config(key, cfg)

    # ── operations ──────────────────────────────────────────────────

    async def update_config(
        self,
        key: str,
        *,
        enabled: bool | None = None,
        cron: str | None = None,
    ) -> JobConfig:
        if key not in self._jobs:
            raise KeyError(key)
        job = self._jobs[key]
        cfg = await self.load_config(key)
        prev_enabled = cfg.enabled
        if enabled is not None:
            cfg.enabled = enabled
        if cron is not None:
            cron = cron.strip()
            if not is_valid_cron(cron):
                raise ValueError(
                    f"Cron {cron!r} is not a valid 5- or 6-field expression"
                )
            cfg.cron = cron
        await self.save_config(key, cfg)
        # Apply enable / disable flips by restarting the loop. Cron
        # changes are picked up on the loop's next read of load_config(),
        # which happens on every iteration; nudging the wakeup makes the
        # change effective immediately.
        if prev_enabled != cfg.enabled:
            await self._restart_loop(key)
        elif cfg.enabled:
            job.wakeup.set()
        _ = job  # used above; satisfy linter
        return cfg

    async def trigger(self, key: str) -> JobConfig:
        if key not in self._jobs:
            raise KeyError(key)
        await self._run_once(key)
        return await self.load_config(key)

    def wakeup(self, key: str) -> None:
        """Nudge the loop so the next iteration runs immediately. Cheap
        external alternative to ``trigger`` when the caller doesn't need
        to wait for the run to complete."""
        job = self._jobs.get(key)
        if job is not None:
            job.wakeup.set()
