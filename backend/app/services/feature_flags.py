"""Read helpers for the feature_flags Config row. Shared by routes + services."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import FEATURE_FLAGS_DEFAULTS
from app.models.config import Config

FEATURE_FLAGS_KEY = "feature_flags"


async def get_feature_flags_dict(session: AsyncSession) -> dict:
    """Return feature flags merged with defaults. DB values win on conflict."""
    result = await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))
    row = result.scalar_one_or_none()
    if not row:
        return dict(FEATURE_FLAGS_DEFAULTS)
    merged = dict(FEATURE_FLAGS_DEFAULTS)
    merged.update(row.value)
    return merged


# The behavioral flags gate-ledger.md's "Standing conditional gates" table
# (§ "Ranking-arm activation" / "Reranker on") holds to a measured win before
# flipping away from their today-equivalent no-op. Community injection and
# the w_ppr/w_dual arms are also named there but have no config row yet — only
# list flags that actually exist in FEATURE_FLAGS_DEFAULTS belong here.
MEASURABLE_FLAGS: tuple[str, ...] = (
    "w_importance",
    "w_heat",
    "w_recency",
    "w_context_boost",
    "reranker_enabled",
)

FLAG_MEASUREMENTS_KEY = "flag_measurements"


async def get_measured_flags(session: AsyncSession) -> list[str]:
    """Which of ``MEASURABLE_FLAGS`` carry a recorded gate-ledger win.

    Durable, not a hardcoded UI list: this reads a ``config`` row rather than
    a static frontend array, so the "unmeasured" badge can never drift from
    what actually got measured. The row is empty by default — matching
    ``docs/planning/gate-ledger.md``'s "Arm activation log", which has never
    recorded an entry — and nothing in this codebase writes to it yet; a
    future gate-clearing process is the only intended writer.
    """
    result = await session.execute(
        select(Config).where(Config.key == FLAG_MEASUREMENTS_KEY)
    )
    row = result.scalar_one_or_none()
    if not row or not isinstance(row.value, dict):
        return []
    measured = row.value.get("measured", [])
    if not isinstance(measured, list):
        return []
    return [f for f in measured if f in MEASURABLE_FLAGS]
