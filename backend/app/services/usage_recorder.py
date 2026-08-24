"""Writes one ``llm_usage`` row per vendor call.

**Its own session, always.** The pipeline runs Phase 5 in two savepoints, and
an extraction failure never enters savepoint B at all. A usage row written on
the caller's session is rolled back with the work it describes — so the
failed-work rows, the ones this feature exists to surface, would delete their
own evidence. ``record`` therefore takes no session: the factory handed to the
constructor is the only way in.

**Never raises.** Same contract as ``record_event``: a metering failure must
not kill the work it is metering. It logs at ERROR and returns.

Invariant 13's single worker makes this safe without cross-process
coordination, and the async-session-lifetime invariant permits it because these
rows share no locks with the caller's transaction.
"""
from __future__ import annotations

import asyncio
import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import NamedTuple

from sqlalchemy import select

from app.models.config import Config
from app.models.llm_usage import LLMUsage
from app.services.llm import extract_usage
from app.services.llm_quirks import quirks_for
from app.services.usage_pricing import (
    MODEL_PRICES_CONFIG_KEY,
    compute_cost_micros,
    resolve_rates,
)

logger = logging.getLogger(__name__)

#: Prices are read from the config row rather than frozen at construction, so
#: an operator's edit takes effect on the next call instead of the next boot.
#: Short TTL for the same reason the feature-flag cache has one: this runs on
#: every vendor call, and a per-call SELECT would make metering cost more than
#: some of the calls it meters.
_PRICE_CACHE_TTL = 30.0
_price_cache: dict = {"value": None, "at": 0.0}
_price_lock = asyncio.Lock()


async def _read_price_overrides(session_factory) -> dict:
    async with session_factory() as session:
        row = (await session.execute(
            select(Config).where(Config.key == MODEL_PRICES_CONFIG_KEY)
        )).scalar_one_or_none()
    return dict(row.value) if row and isinstance(row.value, dict) else {}


async def get_price_overrides(session_factory) -> dict:
    now = time.monotonic()
    value = _price_cache["value"]
    if value is not None and now - _price_cache["at"] < _PRICE_CACHE_TTL:
        return value
    async with _price_lock:
        value = _price_cache["value"]
        if value is not None and now - _price_cache["at"] < _PRICE_CACHE_TTL:
            return value
        fresh = await _read_price_overrides(session_factory)
        _price_cache["value"] = fresh
        _price_cache["at"] = time.monotonic()
        return fresh


def price_cache_reset() -> None:
    """Drop the cached price table.

    Called by the price write path so an operator's edit is visible on the next
    call rather than up to the TTL later -- a settings form that takes half a
    minute to mean anything reads as a form that did not work. Tests use it too.
    """
    _price_cache["value"] = None
    _price_cache["at"] = 0.0

#: What a call is recorded against when nobody claimed it. Still counted in
#: totals — an unattributed cost is a real cost.
UNATTRIBUTED = "unattributed"


class UsageSubject(NamedTuple):
    subject_type: str
    subject_id: str | None
    project: str | None


#: The ambient subject, for scopes that genuinely wrap many calls — a job run,
#: an HTTP request. Ingest does **not** rely on this: every task
#: ``asyncio.gather`` creates copies the *same* parent context, so a per-entry
#: value has to be passed explicitly or every call in a batch attributes to the
#: batch.
current_subject: ContextVar[UsageSubject | None] = ContextVar(
    "current_subject", default=None
)


@contextmanager
def subject_scope(subject: UsageSubject):
    """Set the ambient subject for the duration of a scope."""
    token = current_subject.set(subject)
    try:
        yield
    finally:
        current_subject.reset(token)


class UsageRecorder:
    def __init__(self, session_factory, price_overrides: dict | None = None):
        self._session_factory = session_factory
        #: An explicit table pins the rates (tests, and any caller that wants a
        #: fixed price basis). ``None`` means read the live config row.
        self._price_overrides = price_overrides

    async def _rates_for(self, model: str):
        overrides = self._price_overrides
        if overrides is None:
            overrides = await get_price_overrides(self._session_factory)
        return resolve_rates(model, overrides)

    async def record(
        self,
        *,
        purpose: str,
        model: str,
        provider: str | None,
        api_kind: str,
        payload: dict | None,
        subject: UsageSubject | None,
        duration_ms: int,
        ok: bool,
        error_kind: str | None,
        extra_raw: dict | None = None,
    ) -> None:
        """Record one call. Innermost subject wins; failures are swallowed."""
        try:
            subj = (
                subject
                or current_subject.get()
                or UsageSubject(UNATTRIBUTED, None, None)
            )
            usage = extract_usage(payload, quirks_for(api_kind))
            rates = await self._rates_for(model)
            cost = compute_cost_micros(
                rates,
                usage["prompt_tokens"] if usage else None,
                usage["cached_tokens"] if usage else None,
                usage["completion_tokens"] if usage else None,
            )
            raw = dict((usage or {}).get("raw") or {})
            if extra_raw:
                raw.update(extra_raw)
            row = LLMUsage(
                purpose=purpose,
                model=model,
                provider=provider,
                api_kind=api_kind,
                subject_type=subj.subject_type,
                subject_id=subj.subject_id,
                project=subj.project,
                prompt_tokens=usage["prompt_tokens"] if usage else None,
                cached_tokens=usage["cached_tokens"] if usage else None,
                completion_tokens=usage["completion_tokens"] if usage else None,
                reasoning_tokens=usage["reasoning_tokens"] if usage else None,
                tokens_measured=usage is not None,
                cost_micros=cost,
                rates_used=(
                    {
                        "input": rates.input_micros_per_mtok,
                        "cached": rates.cached_micros_per_mtok,
                        "output": rates.output_micros_per_mtok,
                    }
                    if rates
                    else {}
                ),
                usage_raw=raw,
                ok=ok,
                error_kind=error_kind,
                duration_ms=duration_ms,
            )
            async with self._session_factory() as session:
                session.add(row)
                await session.commit()
        except Exception:
            logger.exception(
                "usage recording failed for purpose=%s model=%s", purpose, model
            )
