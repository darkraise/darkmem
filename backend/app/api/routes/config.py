import asyncio
import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.utils.background import spawn
from app.config import FEATURE_FLAGS_DEFAULTS
from app.database import get_session
from app.models.config import Config
from app.models.llm_config import LLMProvider, LLMProfile, LLMPurposeConfigRow, MLProfile
from app.schemas.config import (
    LLMConfigResponse,
    LLMConfigUpdate,
    LLMConfigUpdateResponse,
)
from app.services.config import (
    PURPOSES,
    cfg_to_schema,
)
from app.services.config import get_llm_config as fetch_llm_config
from app.services.feature_flags import FEATURE_FLAGS_KEY, get_feature_flags_dict

router = APIRouter(prefix="/api/v1/config", tags=["config"])

logger = logging.getLogger(__name__)


def _swap_pipeline_llm(pipeline, new_llm) -> None:
    """Replace every LLM reference the pipeline holds.

    The ``ExtractionService`` / ``ClassificationService`` instances pin
    their own copy via ``self.llm = llm`` at construction time, so a bare
    ``pipeline.llm = new_llm`` would leave the call sites firing against
    the stale orchestrator (e.g. still OpenAI after the user pointed
    extraction at Ollama).
    """
    pipeline.llm = new_llm
    extraction_svc = getattr(pipeline, "extraction", None)
    if extraction_svc is not None:
        extraction_svc.llm = new_llm
    classification_svc = getattr(pipeline, "classification", None)
    if classification_svc is not None:
        classification_svc.llm = new_llm
    # The pipeline caches its per-batch classifier resolution (LLM vs in-process
    # ML, keyed on the classification purpose's ml_profile_ref) for a short TTL.
    # A config save can flip that ref, so drop the cache here — the same place
    # the LLM references are swapped — to honor the per-batch contract instead of
    # serving the stale classifier until the TTL lapses.
    if hasattr(pipeline, "_classifier_cache"):
        pipeline._classifier_cache = None


async def _close_orchestrator_safely(old_llm) -> None:
    """Close the previous orchestrator's httpx client without raising.

    Runs as a background task so any concurrent request that still holds
    a reference to ``old_llm`` finishes before its connection pool is
    torn down. Swallows close-time exceptions to a warning — the new
    orchestrator is already live so a failed close is just a leaked
    socket, not a user-visible error.
    """
    try:
        await old_llm.close()
    except Exception:
        logger.warning("Failed to close replaced LLM orchestrator", exc_info=True)


def _replace_orchestrator(request: Request, new_llm) -> None:
    """Atomically install ``new_llm`` as the active orchestrator.

    Updates ``app.state.llm``, swaps every reference inside the
    pipeline, and schedules the previous orchestrator's client to be
    closed as a background task so its keep-alive connections don't
    leak. Without this teardown, every Save on the LLM Providers page
    leaked an ``httpx.AsyncClient``; under load that produced sporadic
    Bad Gateway responses on the *first* save (stale pool) followed by
    a clean second save (fresh pool warmed up).
    """
    old_llm = getattr(request.app.state, "llm", None)
    request.app.state.llm = new_llm
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is not None:
        _swap_pipeline_llm(pipeline, new_llm)
    if old_llm is not None and old_llm is not new_llm:
        spawn(_close_orchestrator_safely(old_llm), name="close-orchestrator")


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    config = await fetch_llm_config(session)
    return LLMConfigResponse(**{p: cfg_to_schema(c) for p, c in config.items()})


# Known REST deviation: this is an idempotent full-replace of the six-purpose
# LLM config, so for symmetry with its PUT siblings (llm-providers, llm-profiles,
# feature-flags) it should be PUT /config/llm. Left as POST because changing it
# would break existing frontend clients. See docs/api-rest-conventions.md
# ("Known deviations").
@router.post("/llm", response_model=LLMConfigUpdateResponse)
async def update_llm_config(
    body: LLMConfigUpdate,
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services.llm import LLMOrchestrator

    # Serialise concurrent config swaps so two admins saving at once can't
    # leave ``app.state.llm`` and ``app.state.pipeline`` wired to different
    # orchestrators.
    async with request.app.state.llm_config_lock:
        update_data = body.model_dump(exclude_unset=True)

        # Look up provider/profile/ml-profile name → id once for the
        # whole request.
        prov_rows = (await session.execute(select(LLMProvider))).scalars().all()
        provider_id_by_name = {row.name: row.id for row in prov_rows}
        prof_rows = (await session.execute(select(LLMProfile))).scalars().all()
        profile_id_by_name = {row.name: row.id for row in prof_rows}
        ml_prof_rows = (await session.execute(select(MLProfile))).scalars().all()
        ml_profile_id_by_name = {row.name: row.id for row in ml_prof_rows}

        for purpose in PURPOSES:
            purpose_update = getattr(body, purpose, None)
            if purpose not in update_data or purpose_update is None:
                continue
            # Keep only the fields the client actually set, but preserve an
            # explicit ``null`` so dimensions/provider_ref/profile_ref can be
            # CLEARED — an omitted field stays untouched, an explicit null
            # clears the column.
            incoming = {
                k: v
                for k, v in update_data[purpose].items()
                if k in purpose_update.model_fields_set
            }
            # Sentinel: "***" means "don't rotate the stored API key".
            if incoming.get("api_key") == "***":
                incoming.pop("api_key")

            row = (await session.execute(
                select(LLMPurposeConfigRow).where(LLMPurposeConfigRow.purpose == purpose)
            )).scalar_one_or_none()
            if row is None:
                row = LLMPurposeConfigRow(purpose=purpose, model="")
                session.add(row)

            # Map name-based fields onto the FK columns. Empty string means
            # "clear the link" (matches the API contract used by the UI).
            if "provider_ref" in incoming:
                ref = incoming.pop("provider_ref") or None
                if ref and ref not in provider_id_by_name:
                    raise HTTPException(
                        status_code=422,
                        detail=f"unknown provider {ref!r}",
                    )
                row.provider_id = provider_id_by_name.get(ref) if ref else None
            if "profile_ref" in incoming:
                ref = incoming.pop("profile_ref") or None
                if ref and ref not in profile_id_by_name:
                    raise HTTPException(
                        status_code=422,
                        detail=f"unknown profile {ref!r}",
                    )
                row.profile_id = profile_id_by_name.get(ref) if ref else None
                # Picking an LLM profile clears any previously-set ML
                # profile reference. Only one of the two FKs should be
                # populated at a time; the pipeline dispatch reads
                # ml_profile_id first and falls back to the LLM path.
                if ref:
                    row.ml_profile_id = None
            if "ml_profile_ref" in incoming:
                ref = incoming.pop("ml_profile_ref") or None
                if ref and ref not in ml_profile_id_by_name:
                    raise HTTPException(
                        status_code=422,
                        detail=f"unknown ml-profile {ref!r}",
                    )
                row.ml_profile_id = ml_profile_id_by_name.get(ref) if ref else None
                if ref:
                    row.profile_id = None

            for field in (
                "model", "dimensions", "reasoning", "api_kind",
                "provider", "base_url", "api_key", "params",
            ):
                if field in incoming:
                    setattr(row, field, incoming[field])
            row.updated_at = datetime.now(timezone.utc)

        await session.flush()

        # Re-resolve through ``fetch_llm_config`` so profile-referenced
        # purposes get their connection fields overlaid before the
        # orchestrator goes live. ``new_value`` itself stays unresolved on
        # disk by design — the overlay is applied at read time.
        updated_config = await fetch_llm_config(session)
        new_llm = LLMOrchestrator(updated_config)
        _replace_orchestrator(request, new_llm)

        # Resolve the dimensions of the new embedder before updating the
        # fingerprint. Prefer the explicit user value; otherwise probe the
        # model; otherwise leave it unset and let the next embed call
        # populate the registry on demand.
        new_embedding_dims: int | None = updated_config["embedding"].dimensions
        if new_embedding_dims is None:
            try:
                probe, _ = await new_llm.embed("dimension probe")
                new_embedding_dims = len(probe)
            except Exception as exc:
                logger.warning("Could not probe new embedder dimensions: %s", exc)

        pipeline = getattr(request.app.state, "pipeline", None)

        obsolete_after_change = None
        if pipeline is not None and new_embedding_dims:
            from app.services.reembed import ReembedService
            reembed_svc = ReembedService(session)
            # Build the partition fingerprint with the canonical helper so the
            # ``model|dims`` format can never drift from what the embed methods
            # emit. ``new_embedding_dims`` is the probed/explicit dimension,
            # which may differ from the (possibly-unset) configured value.
            new_fp = LLMOrchestrator._fingerprint(
                updated_config["embedding"].model, new_embedding_dims
            )
            obsolete_after_change = await reembed_svc.count_missing(new_fp)

    purpose_payload = {p: cfg_to_schema(c) for p, c in updated_config.items()}
    return LLMConfigUpdateResponse(
        **purpose_payload,
        obsolete_after_change=obsolete_after_change,
    )


class FeatureFlagsResponse(BaseModel):
    llm_enrichment_enabled: bool
    hybrid_search_enabled: bool
    reranker_enabled: bool
    pipeline_concurrency: int
    classification_areas: list[str]
    classification_mode: str
    embedding_batch_size: int
    embedding_concurrency: int
    entity_cache_ttl_minutes: int
    relation_rescue: bool = True
    confidence_rank_gamma: float = 0.0


class FeatureFlagsUpdate(BaseModel):
    llm_enrichment_enabled: bool | None = None
    hybrid_search_enabled: bool | None = None
    reranker_enabled: bool | None = None
    pipeline_concurrency: int | None = Field(default=None, ge=1, le=20)
    classification_areas: list[str] | None = None
    classification_mode: Literal["simple", "expanded"] | None = None
    embedding_batch_size: int | None = Field(default=None, ge=1, le=200)
    embedding_concurrency: int | None = Field(default=None, ge=1, le=10)
    entity_cache_ttl_minutes: int | None = Field(default=None, ge=1, le=1440)
    relation_rescue: bool | None = None
    confidence_rank_gamma: float | None = Field(default=None, ge=0, le=5)


@router.get("/feature-flags", response_model=FeatureFlagsResponse)
async def get_feature_flags(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    flags = await get_feature_flags_dict(session)
    return FeatureFlagsResponse(**flags)


@router.put("/feature-flags", response_model=FeatureFlagsResponse)
async def update_feature_flags(
    body: FeatureFlagsUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    current = await get_feature_flags_dict(session)
    updates = body.model_dump(exclude_unset=True)

    if "classification_areas" in updates:
        from app.services.classification_areas import AREAS
        invalid = [a for a in updates["classification_areas"] if a not in AREAS]
        if invalid:
            raise HTTPException(status_code=422, detail=f"Unknown classification areas: {invalid}")
        # `general` is the always-on fallback — enforce it server-side so
        # classification can never be left without at least the base area.
        if "general" not in updates["classification_areas"]:
            updates["classification_areas"] = ["general", *updates["classification_areas"]]

    current.update(updates)

    # Drop any keys that aren't part of the current schema so deprecated flags
    # don't linger in the DB row forever.
    stored = {k: current[k] for k in FEATURE_FLAGS_DEFAULTS if k in current}

    result = await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))
    config = result.scalar_one_or_none()
    if config:
        config.value = stored
    else:
        session.add(Config(key=FEATURE_FLAGS_KEY, value=stored))
    await session.flush()

    return FeatureFlagsResponse(**stored)


@router.get("/classification-areas")
async def list_classification_areas(
    _user=Depends(require_auth),
):
    from app.services.classification_areas import AREAS
    return [
        {
            "key": area.key,
            "display_name": area.display_name,
            "types": list(area.llm_types.keys()),
            "type_descriptions": area.llm_types,
        }
        for area in AREAS.values()
    ]


# ── System prompts (UI-editable) ─────────────────────────────────────


class SystemPromptsResponse(BaseModel):
    defaults: dict[str, str]
    overrides: dict[str, str]
    effective: dict[str, str]


class SystemPromptsUpdate(BaseModel):
    """Partial update. Keys map to the prompt body.

    - A non-empty string installs / replaces the override for that purpose.
    - An empty string clears the override (falls back to the in-code default).
    - Omitted keys are left unchanged.
    """

    overrides: dict[str, str] = Field(default_factory=dict)


@router.get("/system-prompts", response_model=SystemPromptsResponse)
async def get_system_prompts(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services import prompt as _prompt_mod  # noqa: PLC0415

    await _prompt_mod.refresh_from_db(session)
    defaults = dict(_prompt_mod.PROMPTS)
    overrides = _prompt_mod.get_overrides()
    effective = {k: overrides.get(k, defaults.get(k, "")) for k in defaults}
    return SystemPromptsResponse(defaults=defaults, overrides=overrides, effective=effective)


@router.put("/system-prompts", response_model=SystemPromptsResponse)
async def update_system_prompts(
    body: SystemPromptsUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services import prompt as _prompt_mod  # noqa: PLC0415

    row = (
        await session.execute(select(Config).where(Config.key == _prompt_mod.SYSTEM_PROMPTS_KEY))
    ).scalar_one_or_none()
    stored: dict[str, str] = {}
    if row and isinstance(row.value, dict):
        for k, v in row.value.items():
            if isinstance(k, str) and isinstance(v, str):
                stored[k] = v

    for key, value in body.overrides.items():
        if not isinstance(key, str) or key not in _prompt_mod.PROMPTS:
            raise HTTPException(status_code=422, detail=f"Unknown prompt purpose: {key!r}")
        if not isinstance(value, str):
            raise HTTPException(status_code=422, detail=f"Prompt for {key!r} must be a string")
        if value == "":
            stored.pop(key, None)
        else:
            # Guard against silently storing 500KB blobs that would blow up
            # the system prompt budget on small-context models.
            if len(value) > 20_000:
                raise HTTPException(
                    status_code=422,
                    detail=f"Prompt for {key!r} exceeds 20,000 characters",
                )
            stored[key] = value

    if row:
        row.value = stored
    else:
        session.add(Config(key=_prompt_mod.SYSTEM_PROMPTS_KEY, value=stored))
    await session.flush()

    await _prompt_mod.refresh_from_db(session)

    defaults = dict(_prompt_mod.PROMPTS)
    overrides = _prompt_mod.get_overrides()
    effective = {k: overrides.get(k, defaults.get(k, "")) for k in defaults}
    return SystemPromptsResponse(defaults=defaults, overrides=overrides, effective=effective)


class ReposPathResponse(BaseModel):
    path: str | None


class ReposPathUpdate(BaseModel):
    path: str


@router.get("/repos-path", response_model=ReposPathResponse)
async def get_repos_path(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    row = (await session.execute(
        select(Config).where(Config.key == "repos_default_local_path")
    )).scalar_one_or_none()
    if row is None or not isinstance(row.value, dict):
        return ReposPathResponse(path=None)
    return ReposPathResponse(path=row.value.get("path"))


@router.put("/repos-path", response_model=ReposPathResponse)
async def update_repos_path(
    body: ReposPathUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services.repo_manager import validate_local_path

    try:
        resolved = validate_local_path(body.path, must_not_be_repo=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    row = (await session.execute(
        select(Config).where(Config.key == "repos_default_local_path")
    )).scalar_one_or_none()
    if row is None:
        session.add(Config(key="repos_default_local_path", value={"path": str(resolved)}))
    else:
        row.value = {"path": str(resolved)}
    await session.flush()
    return ReposPathResponse(path=str(resolved))


