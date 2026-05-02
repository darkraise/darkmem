"""Background-job registry.

Replaces the per-loop ``asyncio.create_task(periodic_X())`` pattern in
``app.main`` with a unified registry: each periodic job is described
by a ``Job`` dataclass and dispatched via ``JobRegistry.start()``.
The registry persists per-job config (enabled, interval) in the
``config`` table under keys of the form ``job:<key>`` and exposes
read / write / trigger operations consumed by the ``/api/v1/jobs``
routes.

Design choices worth noting:

* **One asyncio task per job, owned by the registry.** Tasks are
  cancelled cleanly on app shutdown via ``stop_all()``; the registry
  also re-spawns a job's task when its ``enabled`` flag flips on
  through the UI / API.
* **Interruptible wait.** Every job's loop uses
  ``asyncio.wait_for(wakeup.wait(), timeout=interval_seconds)`` with a
  per-job ``asyncio.Event``. Updating ``interval_seconds`` or
  triggering manually sets the event so the loop wakes immediately
  instead of waiting for the previous interval to elapse.
* **Persistence shape.** Each job has a ``config`` row keyed
  ``job:<key>`` with JSON value::

        {
            "enabled": bool,
            "interval_seconds": int,
            "min_interval_seconds": int,
            "last_run_at": "ISO8601 string" | null,
            "last_status": "ok" | "error" | null,
            "last_error": "<short message>" | null
        }

* **Manual trigger semantics.** ``trigger(key)`` schedules an
  out-of-band run that does NOT wait for the next tick and does NOT
  conflict with the loop — it acquires the same per-job
  ``asyncio.Lock`` the loop uses, runs the job's ``runner``, and
  records the outcome.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.config import Config

logger = logging.getLogger(__name__)


JobRunner = Callable[[], Awaitable[None]]


@dataclass
class JobConfig:
    enabled: bool
    interval_seconds: int
    min_interval_seconds: int
    last_run_at: datetime | None = None
    last_status: str | None = None
    last_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "min_interval_seconds": self.min_interval_seconds,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_status": self.last_status,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobConfig":
        last_run = data.get("last_run_at")
        return cls(
            enabled=bool(data.get("enabled", False)),
            interval_seconds=int(data.get("interval_seconds", 60)),
            min_interval_seconds=int(data.get("min_interval_seconds", 1)),
            last_run_at=datetime.fromisoformat(last_run) if last_run else None,
            last_status=data.get("last_status"),
            last_error=data.get("last_error"),
        )


@dataclass
class Job:
    key: str
    display_name: str
    description: str
    default_interval_seconds: int
    min_interval_seconds: int
    runner: JobRunner
    # Live wiring filled in by the registry at start().
    task: asyncio.Task | None = field(default=None, init=False, repr=False)
    wakeup: asyncio.Event = field(default_factory=asyncio.Event, init=False, repr=False)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)


class JobRegistry:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._jobs: dict[str, Job] = {}
        self._stopped = False

    # ── registration ────────────────────────────────────────────────

    def register(self, job: Job) -> None:
        if job.key in self._jobs:
            raise ValueError(f"Job {job.key!r} already registered")
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
        if row and isinstance(row.value, dict):
            return JobConfig.from_dict(row.value)
        # Synthesize a default if the row is missing — keeps tests and
        # fresh installs happy without forcing the migration to be the
        # only path that creates these rows.
        return JobConfig(
            enabled=True,
            interval_seconds=job.default_interval_seconds if job else 60,
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
        out: list[dict] = []
        for key, job in self._jobs.items():
            cfg = await self.load_config(key)
            running = job.task is not None and not job.task.done()
            out.append({
                "key": job.key,
                "display_name": job.display_name,
                "description": job.description,
                "default_interval_seconds": job.default_interval_seconds,
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
                interval = max(cfg.min_interval_seconds, cfg.interval_seconds)
                try:
                    await asyncio.wait_for(job.wakeup.wait(), timeout=interval)
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
        interval_seconds: int | None = None,
    ) -> JobConfig:
        if key not in self._jobs:
            raise KeyError(key)
        job = self._jobs[key]
        cfg = await self.load_config(key)
        prev_enabled = cfg.enabled
        if enabled is not None:
            cfg.enabled = enabled
        if interval_seconds is not None:
            if interval_seconds < job.min_interval_seconds:
                raise ValueError(
                    f"interval_seconds {interval_seconds} is below the min "
                    f"of {job.min_interval_seconds} for job {key!r}"
                )
            cfg.interval_seconds = interval_seconds
        await self.save_config(key, cfg)
        # Apply enable / disable flips by restarting the loop. Interval
        # changes are picked up on the loop's next read of load_config(),
        # which happens on every iteration; nudging the wakeup makes the
        # change effective immediately.
        if prev_enabled != cfg.enabled:
            await self._restart_loop(key)
        elif cfg.enabled:
            job.wakeup.set()
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
