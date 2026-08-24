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

from app.models.job_run import JobRun
from app.services.usage_recorder import UsageSubject, subject_scope

logger = logging.getLogger(__name__)


JobRunner = Callable[[], Awaitable[None]]


class JobBusyError(RuntimeError):
    """Raised by ``trigger`` when a run is already in flight for the job, so the
    route can map it to a 409 instead of the caller blocking on the per-job
    lock for the full runner duration."""

    def __init__(self, key: str) -> None:
        super().__init__(f"Job {key!r} is already running")
        self.key = key


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
            # Default True to match the install-enabled intent and the
            # synthesized defaults in ``load_config`` / ``list_with_config`` —
            # a persisted row missing the key should be treated as enabled, not
            # silently disabled.
            enabled=bool(data.get("enabled", True)),
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
    # Hard ceiling on a single runner invocation (seconds). None = no ceiling.
    # Without it a runner that blocks on a hung upstream (LLM, parse) holds the
    # per-job lock indefinitely and every scheduled tick queues behind it.
    max_run_seconds: float | None = None
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

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """The factory a runner opens its own session from.

        A runner takes no arguments, so a job that needs a session has to reach
        one; exposing the registry's own keeps it on the same engine the
        registry was constructed with rather than a module-level global that a
        test harness pointing elsewhere would silently bypass.
        """
        return self._session_factory

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
            # `job.task` is the *scheduling loop*, alive for the whole
            # process once start() runs, so it reported every registered job
            # as permanently running. The per-job lock is what a run actually
            # holds — the same signal the trigger route's 409 branch reads.
            running = job.lock.locked()
            item = {
                "key": job.key,
                "display_name": job.display_name,
                "description": job.description,
                "default_cron": job.default_cron,
                "min_interval_seconds": job.min_interval_seconds,
                "running": running,
                "config_schema": [fd.model_dump() for fd in job.config_schema],
                **cfg.to_dict(),
            }
            item["config"] = {**job.default_config, **cfg.config}
            out.append(item)
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
                except asyncio.CancelledError:
                    # Expected: we cancelled the task above. Awaiting it here
                    # re-raises the cancellation from the task; swallow it.
                    pass
                except Exception:
                    # An unexpected teardown error inside the loop — log it
                    # instead of hiding it, but keep stopping the rest.
                    logger.exception("Job %s loop raised during shutdown", job.key)
                job.task = None

    async def _restart_loop(self, key: str) -> None:
        """Cancel any existing task for ``key`` and start a fresh loop
        if the job is currently enabled."""
        job = self._jobs[key]
        if job.task is not None and not job.task.done():
            job.task.cancel()
            try:
                await job.task
            except asyncio.CancelledError:
                # Expected: we just cancelled this task. Swallow the
                # re-raised cancellation from the awaited task.
                pass
            except Exception:
                logger.exception("Job %s loop raised while restarting", key)
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
                try:
                    cfg = await self.load_config(key)
                except Exception as exc:
                    # A single malformed config row must not kill the loop
                    # permanently. Log, sleep on the default floor, and retry.
                    logger.error(
                        "Job %s load_config failed; retrying in %ss: %s",
                        key, job.min_interval_seconds, exc,
                    )
                    try:
                        await asyncio.wait_for(
                            job.wakeup.wait(),
                            timeout=float(job.min_interval_seconds),
                        )
                    except asyncio.TimeoutError:
                        pass
                    job.wakeup.clear()
                    continue
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
            try:
                cfg = await self.load_config(key)
            except Exception:
                # A transient failure loading the config row must not escape
                # _run_once and kill the loop task; skip this run and let the
                # next tick retry.
                logger.exception("Job %s load_config failed; skipping run", key)
                return
            cfg.last_run_at = datetime.now(timezone.utc)
            started_at = cfg.last_run_at
            result = None
            try:
                # The subject has to exist before the runner does any work, and
                # `job_runs.id` does not: it is minted after the runner returns,
                # and a run that reports nothing writes no row at all. Key and
                # start time identify the run without waiting for it.
                with subject_scope(UsageSubject(
                    "job_run", f"{key}@{started_at.isoformat()}", None,
                )):
                    if job.max_run_seconds is not None:
                        result = await asyncio.wait_for(
                            job.runner(), timeout=job.max_run_seconds
                        )
                    else:
                        result = await job.runner()
                cfg.last_status = "ok"
                cfg.last_error = None
            except asyncio.TimeoutError:
                # The runner blew past its ceiling — typically a hung upstream.
                # wait_for cancelled it; the per-job lock releases on block exit
                # as long as the runner lets CancelledError propagate at its
                # await points (none of ours swallow it). The executor thread or
                # subprocess behind a blocking call isn't force-killed — it winds
                # down at its own internal timeout — but the lock is freed here.
                cfg.last_status = "error"
                cfg.last_error = f"runner exceeded max_run_seconds={job.max_run_seconds}"
                logger.error(
                    "Job %s runner timed out after %ss", key, job.max_run_seconds,
                )
            except Exception as exc:
                cfg.last_status = "error"
                cfg.last_error = str(exc)[:500]
                logger.exception("Job %s runner raised", key)
            try:
                await self.save_config(key, cfg)
            except Exception:
                # Persisting the outcome failed (DB blip). The loop must survive
                # so the job keeps firing on its next tick; the prior copy of
                # this write outside the try is what could kill the loop forever.
                logger.exception("Job %s save_config failed after run", key)
            await self._record_run(key, cfg, started_at, result)

    async def _record_run(self, key: str, cfg, started_at, result) -> None:
        """One `job_runs` row per run that had something to say.

        **The no-op rule.** A runner's return value is its work signal:

        - a falsy summary (``0``, ``{}``, ``False``) means *explicitly nothing
          happened* and the run is not recorded;
        - a truthy summary is recorded, and lands in ``detail``;
        - ``None`` means the runner has not opted in, and is recorded as
          before, so adding the signal to a runner is a change to that runner
          alone and never a silent loss of its history.

        A failure is always recorded whatever it returned — a run that broke
        is the one row nobody can afford to have suppressed.

        This is why the high-frequency drainers stopped flooding: `buffer_flush`
        polls an empty queue every five seconds and now says so by returning 0.

        Writes go to `job_runs`, never `events`: that table is append-only by
        trigger and permanent by ruling, and telemetry that wants pruning has
        no business in the substrate gate metrics are computed from.

        Recording is a side-channel to the run it describes, so a failure here
        is logged and swallowed rather than allowed to kill the loop.
        """
        failed = cfg.last_status == "error"
        if not failed and result is not None and not result:
            return
        try:
            duration = (datetime.now(timezone.utc) - started_at).total_seconds()
            detail = result if isinstance(result, dict) else (
                {"count": result} if isinstance(result, int) else {}
            )
            async with self._session_factory() as session:
                session.add(JobRun(
                    job_key=key,
                    outcome=cfg.last_status or "unknown",
                    started_at=started_at,
                    duration_seconds=round(duration, 3),
                    error=cfg.last_error,
                    detail=detail,
                ))
                await session.commit()
        except Exception:
            logger.error("Job %s: failed to record run", key, exc_info=True)

        if failed:
            from app.services.notifications import notify_job_failure

            # Outside the recording try/except on purpose: a notifier that
            # cannot reach Telegram must not look like a failure to record,
            # and neither may take the scheduling loop down.
            await notify_job_failure(
                self._session_factory,
                job_key=key,
                error=cfg.last_error,
                duration_seconds=(
                    datetime.now(timezone.utc) - started_at
                ).total_seconds(),
            )

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
        if cron is not None:
            cron = cron.strip()
            if not is_valid_cron(cron):
                raise ValueError(
                    f"Cron {cron!r} is not a valid 5- or 6-field expression"
                )
        # Share the per-job lock with _run_once / set_config so this
        # read-modify-write can't be clobbered by (or clobber) a concurrent
        # scheduled run's last_run_at/status write.
        async with job.lock:
            cfg = await self.load_config(key)
            prev_enabled = cfg.enabled
            if enabled is not None:
                cfg.enabled = enabled
            if cron is not None:
                cfg.cron = cron
            await self.save_config(key, cfg)
        # Apply enable / disable flips by restarting the loop. A cron-only
        # change is picked up on the loop's next read of load_config(),
        # which happens on every iteration; it should take effect on the
        # next scheduled tick, NOT fire an immediate out-of-schedule run, so
        # we deliberately do not nudge the wakeup for a pure cron edit.
        if prev_enabled != cfg.enabled:
            await self._restart_loop(key)
        _ = job  # used above; satisfy linter
        return cfg

    async def set_config(self, key: str, partial: dict) -> JobConfig:
        if key not in self._jobs:
            raise KeyError(key)
        job = self._jobs[key]
        schema = {fd.key: fd for fd in job.config_schema}
        for field_key, value in partial.items():
            fd = schema.get(field_key)
            if fd is None:
                raise ValueError(f"Unknown config key {field_key!r} for job {key!r}")
            if fd.type == "int":
                if isinstance(value, bool) or not isinstance(value, int):
                    raise ValueError(f"Config {field_key!r} must be an integer")
                if fd.min is not None and value < fd.min:
                    raise ValueError(f"Config {field_key!r} must be >= {fd.min}")
                if fd.max is not None and value > fd.max:
                    raise ValueError(f"Config {field_key!r} must be <= {fd.max}")
        # Share the per-job lock with _run_once so a save can't be clobbered
        # by a concurrent scheduled run.
        async with job.lock:
            cfg = await self.load_config(key)
            cfg.config = {**cfg.config, **partial}
            await self.save_config(key, cfg)
        return cfg

    async def trigger(self, key: str) -> JobConfig:
        if key not in self._jobs:
            raise KeyError(key)
        job = self._jobs[key]
        # Non-blocking: if a scheduled or earlier manual run already holds the
        # per-job lock, report busy instead of queueing behind it (which would
        # hang the caller for the full runner duration). Closes the check-then-
        # act window the route's pre-check leaves open.
        if job.lock.locked():
            raise JobBusyError(key)
        await self._run_once(key)
        return await self.load_config(key)

    def wakeup(self, key: str) -> None:
        """Nudge the loop so the next iteration runs immediately. Cheap
        external alternative to ``trigger`` when the caller doesn't need
        to wait for the run to complete."""
        job = self._jobs.get(key)
        if job is not None:
            job.wakeup.set()
