"""LLM config service layer.

Reads three tables: ``llm_providers``, ``llm_profiles``,
``llm_purpose_configs`` (replaces the previous JSONB blobs in the
``config`` table). The public function signatures match what the
routes / orchestrator already consume:

- ``get_llm_providers(session)`` returns ``dict[name, LLMProviderProfile]``
- ``get_llm_profiles(session)`` returns ``dict[name, LLMProfile]``
- ``get_llm_config(session)`` returns ``dict[purpose, LLMPurposeConfig]``

so callers don't need to know the storage shape changed.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import LLMProfile, LLMProviderProfile, LLMPurposeConfig, settings
from app.models.llm_config import LLMProvider, LLMProfile as LLMProfileRow, LLMPurposeConfigRow
from app.schemas.config import LLMPurposeConfigSchema

# Legacy JSONB keys, kept only because some external scripts may still
# reference them. Routes no longer write here; the table is the source
# of truth.
LLM_CONFIG_KEY = "llm_config"
LLM_PROVIDERS_KEY = "llm_providers"
LLM_PROFILES_KEY = "llm_profiles"

PURPOSES = ["embedding", "extraction", "classification", "reasoning", "summarization", "reranker"]


def cfg_to_schema(cfg: LLMPurposeConfig, mask_key: bool = True) -> LLMPurposeConfigSchema:
    return LLMPurposeConfigSchema(
        provider=cfg.provider, base_url=cfg.base_url, model=cfg.model,
        api_key="***" if (mask_key and cfg.api_key) else cfg.api_key,
        dimensions=cfg.dimensions, reasoning=cfg.reasoning,
        api_kind=getattr(cfg, "api_kind", "openai"),
        params=cfg.params,
        provider_ref=getattr(cfg, "provider_ref", None),
        profile_ref=getattr(cfg, "profile_ref", None),
        ml_profile_ref=getattr(cfg, "ml_profile_ref", None),
    )


async def get_llm_providers(session: AsyncSession) -> dict[str, LLMProviderProfile]:
    """Return all stored providers keyed by name."""
    result = await session.execute(select(LLMProvider))
    rows = result.scalars().all()
    return {
        row.name: LLMProviderProfile(
            provider=row.provider,
            base_url=row.base_url,
            api_key=row.api_key,
            api_kind=row.api_kind,
            supports_embedding=row.supports_embedding,
        )
        for row in rows
    }


async def get_llm_profiles(session: AsyncSession) -> dict[str, LLMProfile]:
    """Return all stored profiles keyed by name.

    Joins ``llm_providers`` so the returned ``provider_ref`` matches the
    Provider's name (the API contract callers depend on).
    """
    stmt = (
        select(LLMProfileRow, LLMProvider.name.label("provider_name"))
        .join(LLMProvider, LLMProfileRow.provider_id == LLMProvider.id)
    )
    result = await session.execute(stmt)
    profiles: dict[str, LLMProfile] = {}
    for row, provider_name in result.all():
        profiles[row.name] = LLMProfile(
            provider_ref=provider_name,
            model=row.model,
            params=row.params or {},
            is_embedding=row.is_embedding,
            reasoning=row.reasoning,
        )
    return profiles


def _apply_provider(purpose: LLMPurposeConfig, provider: LLMProviderProfile) -> LLMPurposeConfig:
    """Overlay a provider's connection fields onto a purpose config.

    Note: ``provider.supports_embedding`` is intentionally NOT threaded into the
    resolved ``LLMPurposeConfig`` — it is a UI-advisory flag (greys out the
    embedding profile picker for vendors without an embeddings endpoint), and
    ``LLMPurposeConfig`` carries no embedding-capability field. The runtime guard
    against an embed call landing on a no-embeddings vendor lives in
    ``LLMOrchestrator._assert_can_embed`` (keyed off ``api_kind``), so the
    overlay only needs the connection fields below.
    """
    return purpose.model_copy(update={
        "provider": provider.provider,
        "base_url": provider.base_url,
        "api_key": provider.api_key,
        "api_kind": provider.api_kind,
    })


async def get_llm_config(session: AsyncSession) -> dict[str, LLMPurposeConfig]:
    """Read every purpose config, with the linked provider's connection
    fields overlaid when ``provider_id`` is set on the row.

    Falls back to ``Settings.llm_*`` defaults for purposes that are not
    in the table — same behavior as the old JSONB-backed implementation
    so a fresh install or a user who hasn't customised yet still works.
    """
    defaults = {
        "embedding": settings.llm_embedding,
        "extraction": settings.llm_extraction,
        "classification": settings.llm_classification,
        "reasoning": settings.llm_reasoning,
        "summarization": settings.llm_summarization,
        "reranker": settings.llm_reranker,
    }

    # One round-trip for purposes + providers + profiles + ml-profiles
    # in name form so the resolver can return _ref strings without
    # follow-up queries.
    from app.models.llm_config import MLProfile
    stmt = (
        select(
            LLMPurposeConfigRow,
            LLMProvider.name.label("provider_name"),
            LLMProfileRow.name.label("profile_name"),
            MLProfile.name.label("ml_profile_name"),
        )
        .outerjoin(LLMProvider, LLMPurposeConfigRow.provider_id == LLMProvider.id)
        .outerjoin(LLMProfileRow, LLMPurposeConfigRow.profile_id == LLMProfileRow.id)
        .outerjoin(MLProfile, LLMPurposeConfigRow.ml_profile_id == MLProfile.id)
    )
    result = await session.execute(stmt)
    by_purpose: dict[str, tuple[LLMPurposeConfigRow, str | None, str | None, str | None]] = {}
    for row, prov_name, prof_name, ml_prof_name in result.all():
        by_purpose[row.purpose] = (row, prov_name, prof_name, ml_prof_name)

    providers = await get_llm_providers(session)

    merged: dict[str, LLMPurposeConfig] = {}
    for purpose in PURPOSES:
        if purpose in by_purpose:
            row, prov_name, prof_name, ml_prof_name = by_purpose[purpose]
            cfg = LLMPurposeConfig(
                provider=row.provider,
                base_url=row.base_url,
                model=row.model,
                api_key=row.api_key,
                dimensions=row.dimensions,
                reasoning=row.reasoning,
                api_kind=row.api_kind,
                params=row.params or {},
                provider_ref=prov_name,
                profile_ref=prof_name,
                ml_profile_ref=ml_prof_name,
            )
            if prov_name and prov_name in providers:
                cfg = _apply_provider(cfg, providers[prov_name])
        else:
            cfg = defaults[purpose]
        merged[purpose] = cfg
    return merged
