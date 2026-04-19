import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.config import FEATURE_FLAGS_DEFAULTS, LLMPurposeConfig, ml_pipeline_settings, settings
from app.database import get_session
from app.models.config import Config
from app.schemas.config import LLMConfigResponse, LLMConfigUpdate, LLMConfigUpdateResponse
from app.services.config import LLM_CONFIG_KEY, PURPOSES, cfg_to_schema
from app.services.config import get_llm_config as fetch_llm_config

router = APIRouter(prefix="/api/v1/config", tags=["config"])

logger = logging.getLogger(__name__)


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    config = await fetch_llm_config(session)
    return LLMConfigResponse(**{p: cfg_to_schema(c) for p, c in config.items()})


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
    llm_lock: asyncio.Lock = getattr(request.app.state, "llm_config_lock", None)
    if llm_lock is None:
        llm_lock = asyncio.Lock()
        request.app.state.llm_config_lock = llm_lock

    async with llm_lock:
        result = await session.execute(select(Config).where(Config.key == LLM_CONFIG_KEY))
        db_entry = result.scalar_one_or_none()

        current = await fetch_llm_config(session)
        update_data = body.model_dump(exclude_unset=True)

        new_value = {}
        for purpose in PURPOSES:
            if purpose in update_data and update_data[purpose] is not None:
                existing = current[purpose].model_dump()
                incoming = {k: v for k, v in update_data[purpose].items() if v is not None}
                # Sentinel: "***" means "don't rotate the stored API key".
                if incoming.get("api_key") == "***":
                    incoming.pop("api_key")
                existing.update(incoming)
                new_value[purpose] = existing
            else:
                new_value[purpose] = current[purpose].model_dump()

        if db_entry:
            db_entry.value = new_value
        else:
            session.add(Config(key=LLM_CONFIG_KEY, value=new_value))

        await session.flush()

        updated_config = {p: LLMPurposeConfig(**v) for p, v in new_value.items()}
        new_llm = LLMOrchestrator(updated_config)
        request.app.state.llm = new_llm

        # Resolve the dimensions of the new embedder before updating the
        # fingerprint. Prefer the explicit user value; otherwise probe the
        # model; otherwise keep the previous value so obsolete counts stay
        # interpretable.
        new_embedding_dims: int | None = updated_config["embedding"].dimensions
        if new_embedding_dims is None:
            try:
                probe = await new_llm.embed("dimension probe")
                new_embedding_dims = len(probe)
            except Exception as exc:
                logger.warning("Could not probe new embedder dimensions: %s", exc)
                new_embedding_dims = getattr(
                    request.app.state, "embedding_dims", settings.embedding_dimensions
                )

        request.app.state.embedding_dims = new_embedding_dims

        pipeline = getattr(request.app.state, "pipeline", None)
        if pipeline is not None:
            pipeline.llm = new_llm
            pipeline.extraction.llm = new_llm
            pipeline.embedding_fingerprint = (
                f"{new_llm.config['embedding'].model}|{new_embedding_dims}"
            )

        obsolete_after_change = None
        if pipeline is not None:
            from app.services.reembed import ReembedService
            reembed_svc = ReembedService(session)
            obsolete_after_change = await reembed_svc.count_obsolete(pipeline.embedding_fingerprint)

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
    ml_device: str = "auto"
    ml_cuda_index: int = 0
    ml_extraction: bool = False
    ml_classification: bool = False
    ml_retrieval: bool = False
    ml_shadow_mode: bool = False
    confidence_rank_gamma: float = 0.0
    ml_idle_ttl_minutes: int = 30
    ml_eviction_check_interval_seconds: int = 60


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
    ml_device: Literal["auto", "cpu", "cuda"] | None = None
    ml_cuda_index: int | None = Field(default=None, ge=0, le=15)
    ml_extraction: bool | None = None
    ml_classification: bool | None = None
    ml_retrieval: bool | None = None
    ml_shadow_mode: bool | None = None
    confidence_rank_gamma: float | None = Field(default=None, ge=0, le=5)
    ml_idle_ttl_minutes: int | None = Field(default=None, ge=0, le=1440)
    ml_eviction_check_interval_seconds: int | None = Field(default=None, ge=10, le=3600)


FEATURE_FLAGS_KEY = "feature_flags"


async def get_feature_flags_dict(session: AsyncSession) -> dict:
    result = await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))
    config = result.scalar_one_or_none()
    if not config:
        return dict(FEATURE_FLAGS_DEFAULTS)
    merged = dict(FEATURE_FLAGS_DEFAULTS)
    merged.update(config.value)
    return merged


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


class EnrichmentConfigUpdate(BaseModel):
    enabled: bool = False
    batch_size: int = Field(default=5, ge=1, le=100)
    interval_seconds: int = Field(default=10, ge=1, le=3600)


@router.get("/enrichment")
async def get_enrichment_config(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Config).where(Config.key == "enrichment_config"))
    config = result.scalar_one_or_none()
    if not config:
        return {"enabled": False, "batch_size": 5, "interval_seconds": 10}
    return config.value


@router.put("/enrichment")
async def update_enrichment_config(
    body: EnrichmentConfigUpdate,
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Config).where(Config.key == "enrichment_config"))
    config = result.scalar_one_or_none()
    new_value = body.model_dump()
    if config:
        config.value = new_value
    else:
        session.add(Config(key="enrichment_config", value=new_value))
    await session.flush()

    worker = getattr(request.app.state, "enrichment_worker", None)
    if worker:
        worker.batch_size = body.batch_size
        worker.interval = body.interval_seconds

        if body.enabled and not worker._running:
            old_task = getattr(request.app.state, "enrichment_task", None)
            if old_task and not old_task.done():
                worker.stop()
                old_task.cancel()
                # Wait for the cancelled loop to actually exit before we start
                # a new one so we never have two run_loops racing on the same
                # worker state.
                try:
                    await old_task
                except (asyncio.CancelledError, Exception):
                    pass
            worker._running = False

            task = asyncio.create_task(worker.run_loop())
            request.app.state.enrichment_task = task
        elif not body.enabled and worker._running:
            worker.stop()

    return new_value


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


# ── ML pipeline device selection ─────────────────────────────────────


class MLDeviceInfo(BaseModel):
    id: str
    label: str
    kind: str
    index: int | None = None


class MLDeviceCurrent(BaseModel):
    ml_device: str
    ml_cuda_index: int
    loaded: bool
    effective_device: str | None
    cpu_fallback: bool


class MLDevicesResponse(BaseModel):
    available: list[MLDeviceInfo]
    current: MLDeviceCurrent


class MLDeviceApplyRequest(BaseModel):
    ml_device: Literal["auto", "cpu", "cuda"] | None = None
    ml_cuda_index: int | None = Field(default=None, ge=0, le=15)


class MLDeviceApplyResponse(BaseModel):
    ml_device: str
    ml_cuda_index: int
    effective_device: str
    loaded: bool
    reloaded: bool
    reload_error: str | None = None


def _current_ml_info_from_flags(flags: dict) -> MLDeviceCurrent:
    """Build the live-state view that the UI renders alongside the picker."""
    from app.services.ml_models import models_available

    loaded = models_available()
    effective: str | None = None
    if loaded:
        from app.services.ml_models import get_ml_models  # noqa: PLC0415
        try:
            effective = get_ml_models().device
        except Exception:
            effective = None
    return MLDeviceCurrent(
        ml_device=str(flags.get("ml_device", "auto")),
        ml_cuda_index=int(flags.get("ml_cuda_index", 0) or 0),
        loaded=loaded,
        effective_device=effective,
        cpu_fallback=bool(getattr(ml_pipeline_settings, "cpu_fallback", True)),
    )


@router.get("/ml-devices", response_model=MLDevicesResponse)
async def list_ml_devices(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Return the devices the ML pipeline can target, plus the live state."""
    from app.services.ml_models import list_available_devices  # noqa: PLC0415

    flags = await get_feature_flags_dict(session)
    return MLDevicesResponse(
        available=[MLDeviceInfo(**d) for d in list_available_devices()],
        current=_current_ml_info_from_flags(flags),
    )


@router.post("/ml-device/apply", response_model=MLDeviceApplyResponse)
async def apply_ml_device(
    body: MLDeviceApplyRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Persist the device choice and reload the ML pipeline on it.

    Saves ``ml_device`` + ``ml_cuda_index`` into the feature-flags Config row,
    then reloads the in-process ML singleton so the next extraction /
    classification request honours the new device. If the underlying load
    fails (e.g. CUDA OOM), :func:`reload_ml_models` still falls back to CPU
    when ``cpu_fallback`` is true; the response reflects the effective device
    actually in use plus any ``reload_error`` surfaced from the exception.
    """
    from app.services.ml_models import (  # noqa: PLC0415
        models_available,
        reload_ml_models,
    )

    flags = await get_feature_flags_dict(session)

    device = body.ml_device if body.ml_device is not None else str(flags.get("ml_device", "auto"))
    if device not in ("auto", "cpu", "cuda"):
        raise HTTPException(status_code=422, detail="ml_device must be one of 'auto', 'cpu', 'cuda'")

    cuda_index = body.ml_cuda_index if body.ml_cuda_index is not None else int(flags.get("ml_cuda_index", 0) or 0)
    if not isinstance(cuda_index, int) or cuda_index < 0 or cuda_index > 15:
        raise HTTPException(status_code=422, detail="ml_cuda_index must be a non-negative int (0-15)")

    flags["ml_device"] = device
    flags["ml_cuda_index"] = cuda_index
    # Match the cleanup pass in update_feature_flags so we don't resurrect
    # deprecated keys via this endpoint.
    stored = {k: flags[k] for k in FEATURE_FLAGS_DEFAULTS if k in flags}

    existing = (await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))).scalar_one_or_none()
    if existing:
        existing.value = stored
    else:
        session.add(Config(key=FEATURE_FLAGS_KEY, value=stored))
    await session.flush()

    reloaded = False
    effective = "cpu"
    reload_error: str | None = None
    try:
        ml = reload_ml_models(device=device, cuda_index=cuda_index)
        reloaded = True
        effective = ml.device
    except Exception as exc:
        reload_error = f"{type(exc).__name__}: {exc}"
        logger.warning("reload_ml_models failed during /ml-device/apply: %s", exc)

    return MLDeviceApplyResponse(
        ml_device=device,
        ml_cuda_index=cuda_index,
        effective_device=effective,
        loaded=models_available(),
        reloaded=reloaded,
        reload_error=reload_error,
    )


@router.post("/enrichment/trigger")
async def trigger_enrichment(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services.enrichment_worker import EnrichmentWorker

    llm = getattr(request.app.state, "llm", None)
    if not llm:
        raise HTTPException(status_code=503, detail="LLM not available")

    # Honour the user's persisted batch_size so "Run Now" matches the Save
    # semantics. Fall back to the schema default when the row is missing.
    row = (
        await session.execute(select(Config).where(Config.key == "enrichment_config"))
    ).scalar_one_or_none()
    stored = row.value if row and isinstance(row.value, dict) else {}
    try:
        size = int(stored.get("batch_size", EnrichmentConfigUpdate().batch_size))
    except (TypeError, ValueError):
        size = EnrichmentConfigUpdate().batch_size
    size = max(1, min(100, size))

    worker = EnrichmentWorker(llm)
    count = await worker.process_batch(batch_size=size)

    return {"processed": count, "batch_size": size}
