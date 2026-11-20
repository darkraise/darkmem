"""Read helpers for the feature_flags Config row. Shared by routes + services."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import FEATURE_FLAGS_DEFAULTS, settings
from app.models.config import Config

FEATURE_FLAGS_KEY = "feature_flags"


async def get_feature_flags_dict(session: AsyncSession) -> dict:
    """Return feature flags merged with defaults. DB values win on conflict.

    Only declared keys are read: a stored row may still carry a retired flag,
    and the row is not rewritten until the next save.
    """
    result = await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))
    row = result.scalar_one_or_none()
    merged = dict(FEATURE_FLAGS_DEFAULTS)
    if row:
        merged.update({k: v for k, v in row.value.items() if k in FEATURE_FLAGS_DEFAULTS})
    if settings.read_only:
        merged["reranker_enabled"] = False
    return merged
