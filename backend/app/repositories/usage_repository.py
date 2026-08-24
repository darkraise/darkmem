"""Aggregation SQL for the usage read API.

Every number is computed in Postgres. Fetching rows and summing them in Python
would be the same answer only while the table is small, and this table grows
one row per vendor call -- the one shape where a post-fetch filter turns into
an outage rather than a slowdown.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import Integer, and_, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_usage import LLMUsage

_WINDOW = re.compile(r"^(\d+)([hd])$")

#: A call whose rate lookup found nothing writes an empty ``rates_used``. That
#: is what separates "no price for this model" from "measured, and genuinely
#: zero" -- the local embedders bill nothing and must not read as unpriced.
_UNPRICED = and_(LLMUsage.tokens_measured.is_(True), LLMUsage.rates_used == {})
_UNMEASURED = LLMUsage.tokens_measured.is_(False)


def window_start(window: str, now: datetime | None = None) -> datetime | None:
    """Resolve ``30d`` / ``24h`` / ``all`` to a lower bound.

    ``all`` returns None rather than a very old date: an unbounded window is a
    different query, not a wide one, and saying so keeps the predicate off the
    index scan entirely.
    """
    if window == "all":
        return None
    match = _WINDOW.match(window)
    if not match:
        raise ValueError(f"unrecognised window {window!r}")
    amount, unit = int(match.group(1)), match.group(2)
    delta = timedelta(days=amount) if unit == "d" else timedelta(hours=amount)
    return (now or datetime.now(timezone.utc)) - delta


def _filters(start: datetime | None, project: str | None):
    clauses = []
    if start is not None:
        clauses.append(LLMUsage.occurred_at >= start)
    if project is not None:
        clauses.append(LLMUsage.project == project)
    return clauses


_MERGED = LLMUsage.usage_raw["merged_classification"].as_boolean().is_(True)


def _counted(condition):
    return func.count().filter(condition)


def _sum(column):
    return func.coalesce(func.sum(column), 0)


class UsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── totals ──────────────────────────────────────────────────────

    async def totals(self, start: datetime | None, project: str | None) -> dict:
        stmt = select(
            _sum(LLMUsage.cost_micros).label("total_cost_micros"),
            func.count().label("total_calls"),
            _sum(LLMUsage.prompt_tokens).label("prompt_tokens"),
            _sum(LLMUsage.cached_tokens).label("cached_tokens"),
            _sum(LLMUsage.completion_tokens).label("completion_tokens"),
            _sum(LLMUsage.reasoning_tokens).label("reasoning_tokens"),
            _counted(_UNMEASURED).label("unmeasured_calls"),
            _counted(_UNPRICED).label("unpriced_calls"),
            _counted(LLMUsage.ok.is_(False)).label("failed_calls"),
            func.coalesce(
                func.sum(case((LLMUsage.ok.is_(False), LLMUsage.cost_micros), else_=0)),
                0,
            ).label("failed_cost_micros"),
            func.bool_or(_MERGED).label("merged_classification_present"),
        ).where(*_filters(start, project))
        row = (await self.session.execute(stmt)).one()
        result = dict(row._mapping)
        result["merged_classification_present"] = bool(
            result["merged_classification_present"]
        )
        prompt = result["prompt_tokens"]
        result["cache_hit_ratio"] = (
            result["cached_tokens"] / prompt if prompt else None
        )
        return result

    async def unpriced_models(
        self, start: datetime | None, project: str | None
    ) -> list[str]:
        stmt = (
            select(LLMUsage.model)
            .where(*_filters(start, project), _UNPRICED)
            .group_by(LLMUsage.model)
            .order_by(func.count().desc(), LLMUsage.model)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    # ── breakdowns ──────────────────────────────────────────────────

    async def breakdown(
        self, column, start: datetime | None, project: str | None
    ) -> list[dict]:
        cost = _sum(LLMUsage.cost_micros).label("cost_micros")
        stmt = (
            select(
                column.label("key"),
                cost,
                func.count().label("calls"),
                _sum(LLMUsage.prompt_tokens).label("prompt_tokens"),
                _sum(LLMUsage.cached_tokens).label("cached_tokens"),
                _sum(LLMUsage.completion_tokens).label("completion_tokens"),
                _counted(_UNMEASURED).label("unmeasured_calls"),
                _counted(_UNPRICED).label("unpriced_calls"),
            )
            .where(*_filters(start, project))
            .group_by(column)
            .order_by(cost.desc(), column)
        )
        return [dict(r._mapping) for r in (await self.session.execute(stmt)).all()]

    # ── series ──────────────────────────────────────────────────────

    async def series(
        self, bucket: str, start: datetime | None, project: str | None
    ) -> list[dict]:
        trunc = func.date_trunc(bucket, LLMUsage.occurred_at).label("bucket_start")
        stmt = (
            select(
                trunc,
                _sum(LLMUsage.cost_micros).label("cost_micros"),
                func.count().label("calls"),
                _sum(LLMUsage.prompt_tokens).label("prompt_tokens"),
                _sum(LLMUsage.completion_tokens).label("completion_tokens"),
                _counted(_UNMEASURED).label("unmeasured_calls"),
            )
            .where(*_filters(start, project))
            .group_by(trunc)
            .order_by(trunc)
        )
        return [dict(r._mapping) for r in (await self.session.execute(stmt)).all()]

    # ── one subject ─────────────────────────────────────────────────

    async def subject_calls(
        self, subject_type: str, subject_id: str, limit: int
    ) -> list[LLMUsage]:
        stmt = (
            select(LLMUsage)
            .where(
                LLMUsage.subject_type == subject_type,
                LLMUsage.subject_id == subject_id,
            )
            .order_by(LLMUsage.occurred_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def subject_totals(self, subject_type: str, subject_id: str) -> dict:
        stmt = select(
            _sum(LLMUsage.cost_micros).label("total_cost_micros"),
            func.count().label("total_calls"),
        ).where(
            LLMUsage.subject_type == subject_type,
            LLMUsage.subject_id == subject_id,
        )
        return dict((await self.session.execute(stmt)).one()._mapping)

    async def totals_for_subjects(
        self, subject_type: str, subject_ids: list[str]
    ) -> list[dict]:
        """Per-id totals for a page that already knows which rows it is drawing.

        One grouped query rather than one request per row: an Activity page
        showing fifty pipeline runs would otherwise open fifty connections to
        answer a column.
        """
        if not subject_ids:
            return []
        stmt = (
            select(
                LLMUsage.subject_id,
                _sum(LLMUsage.cost_micros).label("cost_micros"),
                func.count().label("calls"),
                _sum(LLMUsage.prompt_tokens).label("prompt_tokens"),
                _sum(LLMUsage.cached_tokens).label("cached_tokens"),
                _sum(LLMUsage.completion_tokens).label("completion_tokens"),
                _counted(_UNMEASURED).label("unmeasured_calls"),
                _counted(_UNPRICED).label("unpriced_calls"),
            )
            .where(
                LLMUsage.subject_type == subject_type,
                LLMUsage.subject_id.in_(subject_ids),
            )
            .group_by(LLMUsage.subject_id)
        )
        return [dict(r._mapping) for r in (await self.session.execute(stmt)).all()]

    async def totals_by_job(
        self, start: datetime | None, project: str | None
    ) -> list[dict]:
        """Per job *key*, not per run.

        A job-run subject is ``{key}@{started_at}`` because the `job_runs` row is
        minted only after the runner returns. Grouping on the key means splitting
        that id rather than joining a table that may hold no row for the run.
        """
        key = func.split_part(LLMUsage.subject_id, "@", 1).label("job_key")
        cost = _sum(LLMUsage.cost_micros).label("cost_micros")
        stmt = (
            select(
                key,
                cost,
                func.count().label("calls"),
                func.count(func.distinct(LLMUsage.subject_id)).label("runs"),
                _sum(LLMUsage.prompt_tokens).label("prompt_tokens"),
                _sum(LLMUsage.cached_tokens).label("cached_tokens"),
                _sum(LLMUsage.completion_tokens).label("completion_tokens"),
                _counted(_UNMEASURED).label("unmeasured_calls"),
                _counted(_UNPRICED).label("unpriced_calls"),
            )
            .where(
                *_filters(start, project),
                LLMUsage.subject_type == "job_run",
                LLMUsage.subject_id.is_not(None),
            )
            .group_by(key)
            .order_by(cost.desc(), key)
        )
        return [dict(r._mapping) for r in (await self.session.execute(stmt)).all()]

    # ── outliers ────────────────────────────────────────────────────

    _ORDERS = {
        "cost": _sum(LLMUsage.cost_micros),
        "calls": func.count(),
        "duration": _sum(LLMUsage.duration_ms),
    }

    async def top(
        self,
        by: str,
        start: datetime | None,
        project: str | None,
        subject_type: str | None,
        limit: int,
    ) -> list[dict]:
        clauses = _filters(start, project)
        if subject_type is not None:
            clauses.append(LLMUsage.subject_type == subject_type)
        stmt = (
            select(
                LLMUsage.subject_type,
                LLMUsage.subject_id,
                func.min(LLMUsage.project).label("project"),
                _sum(LLMUsage.cost_micros).label("cost_micros"),
                func.count().label("calls"),
                cast(_sum(LLMUsage.duration_ms), Integer).label("duration_ms"),
                _counted(_UNMEASURED).label("unmeasured_calls"),
            )
            .where(*clauses)
            .group_by(LLMUsage.subject_type, LLMUsage.subject_id)
            .order_by(self._ORDERS[by].desc())
            .limit(limit)
        )
        return [dict(r._mapping) for r in (await self.session.execute(stmt)).all()]
