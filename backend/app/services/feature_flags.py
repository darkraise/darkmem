"""Read helpers for the feature_flags Config row. Shared by routes + services."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import FEATURE_FLAGS_DEFAULTS, settings
from app.models.config import Config

FEATURE_FLAGS_KEY = "feature_flags"


async def get_feature_flags_dict(session: AsyncSession) -> dict:
    """Return feature flags merged with defaults. DB values win on conflict."""
    result = await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))
    row = result.scalar_one_or_none()
    merged = dict(FEATURE_FLAGS_DEFAULTS)
    if row:
        merged.update(row.value)
    if settings.read_only:
        merged["reranker_enabled"] = False
    return merged
