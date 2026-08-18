"""LLM config service layer.

Reads ONE table: ``llm_purpose_configs``. The provider/profile/ml-profile
indirection is gone (doc 04 §7), so a purpose resolves from its own row
with no joins and no overlay.

- ``get_llm_config(session)`` returns ``dict[purpose, LLMPurposeConfig]``

T1.01 owns asserting the one-query property with a query-counting test.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import LLMPurposeConfig, settings
from app.models.llm_config import LLMPurposeConfigRow
from app.schemas.config import LLMPurposeConfigSchema

# Legacy JSONB keys, kept only because some external scripts may still
# reference them. Routes no longer write here; the table is the source
# of truth.
LLM_CONFIG_KEY = "llm_config"
LLM_PROVIDERS_KEY = "llm_providers"
LLM_PROFILES_KEY = "llm_profiles"

# The six live purposes plus the two Tier-C purposes seeded by T1.05.
# `verification`'s first writer landed in T2.26: the qualification-gated
# judge service is the only lawful dispatcher, scan-pinned by the judge's
# own test suite; `synthesis` stays inert until T3.02. Doc 11 §6 requires
# the rows and this sweep to land before any consumer reaches them.
PURPOSES = [
    "embedding", "extraction", "classification", "reasoning",
    "summarization", "reranker", "synthesis", "verification",
]


def cfg_to_schema(cfg: LLMPurposeConfig, mask_key: bool = True) -> LLMPurposeConfigSchema:
    return LLMPurposeConfigSchema(
        base_url=cfg.base_url, model=cfg.model,
        api_key="***" if (mask_key and cfg.api_key) else cfg.api_key,
        dimensions=cfg.dimensions, reasoning=cfg.reasoning,
        api_kind=getattr(cfg, "api_kind", "openai"),
        params=cfg.params,
        classifier_kind=getattr(cfg, "classifier_kind", None),
    )


async def get_llm_config(session: AsyncSession) -> dict[str, LLMPurposeConfig]:
    """Read every purpose config from its own row — one query, no joins.

    Falls back to ``Settings.llm_*`` defaults for purposes not in the table,
    so a fresh install or a user who has not customised yet still works.
    """
    defaults = {
        "embedding": settings.llm_embedding,
        "extraction": settings.llm_extraction,
        "classification": settings.llm_classification,
        "reasoning": settings.llm_reasoning,
        "summarization": settings.llm_summarization,
        "reranker": settings.llm_reranker,
        "synthesis": settings.llm_synthesis,
        "verification": settings.llm_verification,
    }

    rows = (await session.execute(select(LLMPurposeConfigRow))).scalars().all()
    by_purpose = {row.purpose: row for row in rows}

    merged: dict[str, LLMPurposeConfig] = {}
    for purpose in PURPOSES:
        row = by_purpose.get(purpose)
        if row is None:
            merged[purpose] = defaults[purpose]
            continue
        merged[purpose] = LLMPurposeConfig(
            base_url=row.base_url,
            model=row.model,
            api_key=row.api_key,
            dimensions=row.dimensions,
            reasoning=row.reasoning,
            api_kind=row.api_kind,
            params=row.params or {},
            classifier_kind=row.classifier_kind,
        )
    return merged
