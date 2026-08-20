"""LLM config service layer.

Reads ``llm_purpose_configs`` joined to ``llm_providers``: the purpose row
carries what varies per purpose and the provider row carries the connection,
so resolution is one query with one join and no overlay. The profile and
ml-profile levels of the old indirection stay gone (doc 04 §7).

- ``get_llm_config(session)`` returns ``dict[purpose, LLMPurposeConfig]``

T1.01 owns asserting the one-query property with a query-counting test.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import LLMPurposeConfig, settings
from app.models.llm_config import LLMPurposeConfigRow
from app.models.llm_provider import LLMProviderRow
from app.schemas.config import LLMPurposeConfigSchema

# Legacy JSONB key, kept only because some external scripts may still
# reference it. Routes no longer write here; the tables are the source
# of truth.
LLM_CONFIG_KEY = "llm_config"

# The six live purposes plus the two Tier-C purposes seeded by T1.05.
# `verification`'s first writer landed in T2.26: the qualification-gated
# judge service is the only lawful dispatcher, scan-pinned by the judge's
# own test suite; `synthesis` stays inert until T3.02. Doc 11 §6 requires
# the rows and this sweep to land before any consumer reaches them.
PURPOSES = [
    "embedding", "extraction", "classification", "reasoning",
    "summarization", "reranker", "synthesis", "verification",
]

# This module owns the purpose vocabulary, so a surface that needs to name
# one purpose imports it from here rather than re-deriving it. A written-out
# literal, not an index into PURPOSES: the list's order is not a documented
# contract, and a ninth purpose appended after this one would silently
# repoint an index-based constant at the wrong row with no test failing.
# A provider-management surface asking "does this provider serve the judge?"
# needs this name, never the judge module itself.
VERIFICATION_PURPOSE = "verification"


def cfg_to_schema(cfg: LLMPurposeConfig, mask_key: bool = True) -> LLMPurposeConfigSchema:
    return LLMPurposeConfigSchema(
        base_url=cfg.base_url, model=cfg.model,
        api_key="***" if (mask_key and cfg.api_key) else cfg.api_key,
        dimensions=cfg.dimensions, reasoning=cfg.reasoning,
        api_kind=getattr(cfg, "api_kind", "openai"),
        params=cfg.params,
        classifier_kind=getattr(cfg, "classifier_kind", None),
        provider_name=getattr(cfg, "provider_name", None),
    )


async def get_llm_config(session: AsyncSession) -> dict[str, LLMPurposeConfig]:
    """Read every purpose config in one query with one join.

    Falls back to ``Settings.llm_*`` defaults for purposes not in the table,
    so a fresh install or a user who has not customised yet still works.
    The join is inner, so a purpose row with no provider takes that same
    fallback rather than resolving against an empty connection.
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

    stmt = select(LLMPurposeConfigRow, LLMProviderRow).join(
        LLMProviderRow, LLMPurposeConfigRow.provider_name == LLMProviderRow.name
    )
    by_purpose = {
        row.purpose: (row, provider)
        for row, provider in await session.execute(stmt)
    }

    merged: dict[str, LLMPurposeConfig] = {}
    for purpose in PURPOSES:
        pair = by_purpose.get(purpose)
        if pair is None:
            merged[purpose] = defaults[purpose]
            continue
        row, provider = pair
        merged[purpose] = LLMPurposeConfig(
            base_url=provider.base_url,
            model=row.model,
            api_key=provider.api_key,
            dimensions=row.dimensions,
            reasoning=row.reasoning,
            api_kind=provider.api_kind,
            params=row.params or {},
            classifier_kind=row.classifier_kind,
            provider_name=provider.name,
        )
    return merged
