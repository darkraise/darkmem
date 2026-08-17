"""The `auto_research` config row — configuration, not the loop (T3.28).

Split out of `auto_research.py` so a config surface can read and write the
row without importing the Tier-C loop. Invariant 15's scan forbids app code
reaching that module, and it is right to: the day someone wires a research run
into the pipeline to fill the corpus faster, that scan is what fails. But the
loop's *configuration* is not the loop — an operator toggling a switch runs
nothing — so the honest fix was to move the row rather than to exempt the
route, which would have widened a guard that is doing its job.

The reader fails closed and the writer refuses coercion; both reasons are at
the functions themselves.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.schemas.memory import MemoryBatchCreate

logger = logging.getLogger(__name__)

AUTO_RESEARCH_CONFIG_KEY = "auto_research"

# The reserved source-kind. Every capture the loop files carries it, so
# `memories.source` alone distinguishes a manufactured origin from an observed
# one without joining anything.
#
# **It lives here rather than in the loop for the same reason the config key
# does** (T3.28): recognising a researched row is not running the loop, and
# invariant 15's scan forbids app code importing `app.services.auto_research`.
# The re-derivation surface has to tell a researched memory from any other one
# before it touches it, and importing the loop to read a string constant would
# have bought a second sanctioned crossing for nothing. `auto_research`
# re-exports it, so the loop's own spelling is unchanged.
RESEARCH_SOURCE = "research"

__all__ = [
    "AUTO_RESEARCH_CONFIG_KEY",
    "AUTO_RESEARCH_DEFAULTS",
    "MAX_FINDINGS_CEILING",
    "RESEARCH_SOURCE",
    "ResearchBudget",
    "load_budget",
    "write_auto_research_config",
]


def _positive_int(value: object, fallback: int) -> int:
    """A positive int, or the fallback. Never raises: an unreadable bound must
    not read as "unbounded"."""
    if isinstance(value, bool) or not isinstance(value, int):
        return fallback
    return value if value > 0 else fallback


# Fail closed. Building the loop is not running it (T3.07 brief): pointing it
# at a live instance is a separate, owner-owned decision, so an install that
# has never been configured refuses every run.
AUTO_RESEARCH_DEFAULTS: dict[str, object] = {
    "enabled": False,
    "max_findings_per_run": 20,
    "max_content_chars": 8000,
}

# The batch door's own cap, read off the schema rather than re-typed, so the
# budget cannot quietly authorise a batch the front door would reject.
MAX_FINDINGS_CEILING: int = next(
    meta.max_length
    for meta in MemoryBatchCreate.model_fields["entries"].metadata
    if getattr(meta, "max_length", None) is not None
)


@dataclass(frozen=True)
class ResearchBudget:
    enabled: bool
    max_findings_per_run: int
    max_content_chars: int


async def load_budget(session: AsyncSession) -> ResearchBudget:
    """The per-run budget, from the `auto_research` config row over defaults.

    A malformed row degrades to the defaults rather than raising: the budget
    bounds a run, and an unreadable bound must never read as "unbounded".
    """
    row = (await session.execute(
        select(Config).where(Config.key == AUTO_RESEARCH_CONFIG_KEY)
    )).scalar_one_or_none()
    stored = row.value if row is not None and isinstance(row.value, dict) else {}

    max_findings = _positive_int(
        stored.get("max_findings_per_run"),
        int(AUTO_RESEARCH_DEFAULTS["max_findings_per_run"]),
    )
    if max_findings > MAX_FINDINGS_CEILING:
        logger.warning(
            "%s.max_findings_per_run=%d exceeds the capture batch cap %d; clamping",
            AUTO_RESEARCH_CONFIG_KEY, max_findings, MAX_FINDINGS_CEILING,
        )
        max_findings = MAX_FINDINGS_CEILING

    # `bool()` is the wrong coercion for the master switch: `{"enabled":
    # "false"}` — the most natural malformed shape an operator writes — is
    # truthy, so the one field where failing closed matters most would fail
    # open. The int fields already get this treatment from `_positive_int`.
    enabled = stored.get("enabled", AUTO_RESEARCH_DEFAULTS["enabled"])
    if not isinstance(enabled, bool):
        logger.warning(
            "%s.enabled=%r is not a boolean; falling back to the default",
            AUTO_RESEARCH_CONFIG_KEY, enabled,
        )
        enabled = AUTO_RESEARCH_DEFAULTS["enabled"]

    return ResearchBudget(
        enabled=bool(enabled),
        max_findings_per_run=max_findings,
        max_content_chars=_positive_int(
            stored.get("max_content_chars"),
            int(AUTO_RESEARCH_DEFAULTS["max_content_chars"]),
        ),
    )


async def write_auto_research_config(
    session: AsyncSession, patch: dict
) -> ResearchBudget:
    """The **one** writer of the `auto_research` config row (T3.28).

    Nothing in the tree wrote this row before: arming the loop meant a manual
    database write, which was deliberate ("building the door is not arming the
    loop") until the owner asked for an operator surface. An operator surface
    is a different thing from arming it by default, and the default stays
    `False`.

    Three rules, and the first is the one with teeth:

    - **`enabled` fails closed on every non-boolean.** `bool("false")` is
      `True`, and `{"enabled": "false"}` is the most natural malformed shape an
      operator writes — T3.07's review found exactly that arming the master
      switch. A string, a number, a null: all refused with a 422-shaped error
      rather than coerced, because a coercion that can only fail open has no
      safe direction.
    - **Unknown keys are refused**, not ignored. An operator who misspells
      `max_findings_per_run` must be told, or they will believe they set a
      budget they did not.
    - **The write is a merge over the stored row**, so a partial update does
      not silently reset the fields it omits to their defaults.

    Returns the budget as the reader now resolves it — the same
    `load_research_budget` path a run takes, never a separate echo of what was
    sent, so the response cannot disagree with what the loop will do.
    """
    unknown = sorted(set(patch) - set(AUTO_RESEARCH_DEFAULTS))
    if unknown:
        raise ValueError(
            f"unknown auto_research setting(s): {unknown}; the settable keys are "
            f"{sorted(AUTO_RESEARCH_DEFAULTS)}"
        )

    if "enabled" in patch and not isinstance(patch["enabled"], bool):
        raise ValueError(
            f"auto_research.enabled must be a boolean, got {patch['enabled']!r}; "
            "the master switch is never coerced — a coercion that can only fail "
            "open has no safe direction"
        )

    for key in ("max_findings_per_run", "max_content_chars"):
        if key in patch:
            value = patch[key]
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(
                    f"auto_research.{key} must be a positive integer, got {value!r}"
                )

    row = (await session.execute(
        select(Config).where(Config.key == AUTO_RESEARCH_CONFIG_KEY)
    )).scalar_one_or_none()
    stored = dict(row.value) if row is not None and isinstance(row.value, dict) else {}
    stored.update(patch)

    if row is None:
        session.add(Config(key=AUTO_RESEARCH_CONFIG_KEY, value=stored))
    else:
        row.value = stored
    await session.flush()

    return await load_budget(session)


