from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.config import FEATURE_FLAGS_DEFAULTS, LLMPurposeConfig, settings
from app.database import get_session
from app.models.config import Config
from app.schemas.config import LLMConfigResponse, LLMConfigUpdate, LLMConfigUpdateResponse, LLMPurposeConfigSchema
from app.services.config import LLM_CONFIG_KEY, PURPOSES, cfg_to_schema
from app.services.config import get_llm_config as fetch_llm_config

router = APIRouter(prefix="/api/v1/config", tags=["config"])


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

    # Read existing DB config
    result = await session.execute(select(Config).where(Config.key == LLM_CONFIG_KEY))
    db_entry = result.scalar_one_or_none()

    # Build new config from existing + updates
    current = await fetch_llm_config(session)
    update_data = body.model_dump(exclude_unset=True)

    new_value = {}
    for purpose in PURPOSES:
        if purpose in update_data and update_data[purpose] is not None:
            # Merge: keep existing fields, override with provided ones
            existing = current[purpose].model_dump()
            incoming = {k: v for k, v in update_data[purpose].items() if v is not None}
            # If api_key is "***", keep the existing one
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

    # Swap the live LLM orchestrator so new requests pick up the updated config.
    # In-flight requests keep their existing reference to the old orchestrator (safe).
    updated_config = {p: LLMPurposeConfig(**v) for p, v in new_value.items()}
    new_llm = LLMOrchestrator(updated_config)
    request.app.state.llm = new_llm

    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is not None:
        pipeline.llm = new_llm
        pipeline.extraction.llm = new_llm
        pipeline.embedding_fingerprint = f"{new_llm.config['embedding'].model}|{getattr(request.app.state, 'embedding_dims', 1024)}"

    # Feature 3: compute obsolete counts for the new fingerprint
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
    # Per-stage pipeline path: True -> ML head, False -> LLM fallback.
    ml_extraction: bool = False
    ml_classification: bool = False
    ml_retrieval: bool = False
    ml_shadow_mode: bool = False
    confidence_rank_gamma: float = 0.0
    # Idle-eviction controls (applied by the background eviction loop).
    ml_idle_ttl_minutes: int = 30
    ml_eviction_check_interval_seconds: int = 60


class FeatureFlagsUpdate(BaseModel):
    llm_enrichment_enabled: bool | None = None
    hybrid_search_enabled: bool | None = None
    reranker_enabled: bool | None = None
    pipeline_concurrency: int | None = None
    classification_areas: list[str] | None = None
    classification_mode: str | None = None
    embedding_batch_size: int | None = None
    embedding_concurrency: int | None = None
    entity_cache_ttl_minutes: int | None = None
    ml_device: str | None = None
    ml_cuda_index: int | None = None
    ml_extraction: bool | None = None
    ml_classification: bool | None = None
    ml_retrieval: bool | None = None
    ml_shadow_mode: bool | None = None
    confidence_rank_gamma: float | None = None
    ml_idle_ttl_minutes: int | None = None
    ml_eviction_check_interval_seconds: int | None = None


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

    if "classification_mode" in updates:
        if updates["classification_mode"] not in ("simple", "expanded"):
            raise HTTPException(status_code=422, detail="classification_mode must be 'simple' or 'expanded'")

    if "embedding_batch_size" in updates:
        v = updates["embedding_batch_size"]
        if not isinstance(v, int) or v < 1 or v > 200:
            raise HTTPException(status_code=422, detail="embedding_batch_size must be between 1 and 200")

    if "embedding_concurrency" in updates:
        v = updates["embedding_concurrency"]
        if not isinstance(v, int) or v < 1 or v > 10:
            raise HTTPException(status_code=422, detail="embedding_concurrency must be between 1 and 10")

    if "entity_cache_ttl_minutes" in updates:
        v = updates["entity_cache_ttl_minutes"]
        if not isinstance(v, int) or v < 1 or v > 1440:
            raise HTTPException(status_code=422, detail="entity_cache_ttl_minutes must be between 1 and 1440")

    if "ml_device" in updates:
        v = updates["ml_device"]
        if v not in ("auto", "cpu", "cuda"):
            raise HTTPException(status_code=422, detail="ml_device must be one of 'auto', 'cpu', 'cuda'")

    if "ml_cuda_index" in updates:
        v = updates["ml_cuda_index"]
        if not isinstance(v, int) or v < 0 or v > 15:
            raise HTTPException(status_code=422, detail="ml_cuda_index must be a non-negative int (0-15)")

    if "confidence_rank_gamma" in updates:
        v = updates["confidence_rank_gamma"]
        if not isinstance(v, (int, float)) or v < 0 or v > 5:
            raise HTTPException(status_code=422, detail="confidence_rank_gamma must be between 0 and 5")

    if "ml_idle_ttl_minutes" in updates:
        v = updates["ml_idle_ttl_minutes"]
        if not isinstance(v, int) or v < 0 or v > 24 * 60:
            raise HTTPException(
                status_code=422,
                detail="ml_idle_ttl_minutes must be a non-negative int <= 1440 (24h); 0 disables eviction",
            )

    if "ml_eviction_check_interval_seconds" in updates:
        v = updates["ml_eviction_check_interval_seconds"]
        if not isinstance(v, int) or v < 10 or v > 3600:
            raise HTTPException(
                status_code=422,
                detail="ml_eviction_check_interval_seconds must be between 10 and 3600",
            )

    current.update(updates)

    result = await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))
    config = result.scalar_one_or_none()
    if config:
        config.value = current
    else:
        session.add(Config(key=FEATURE_FLAGS_KEY, value=current))
    await session.flush()

    return FeatureFlagsResponse(**current)


@router.get("/classification-areas")
async def list_classification_areas(
    _user=Depends(require_auth),
):
    from app.services.classification_areas import AREAS, get_merged_llm_types
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
    batch_size: int = 5
    interval_seconds: int = 10


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
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    request: Request = None,
):
    result = await session.execute(select(Config).where(Config.key == "enrichment_config"))
    config = result.scalar_one_or_none()
    new_value = body.model_dump()
    if config:
        config.value = new_value
    else:
        session.add(Config(key="enrichment_config", value=new_value))
    await session.flush()

    worker = getattr(request.app.state, "enrichment_worker", None) if request else None
    if worker:
        worker.batch_size = body.batch_size
        worker.interval = body.interval_seconds
        if body.enabled and not worker._running:
            import asyncio

            old_task = getattr(request.app.state, "enrichment_task", None)
            if old_task and not old_task.done():
                worker.stop()
                old_task.cancel()
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

    # Always refresh from DB before reporting, so the UI sees the truth.
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

    # Load current stored overrides (if any) and apply the patch.
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

    # Refresh the process-level cache so subsequent get() calls see the new
    # overrides without a restart.
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
    ml_device: str | None = None
    ml_cuda_index: int | None = None


class MLDeviceApplyResponse(BaseModel):
    ml_device: str
    ml_cuda_index: int
    effective_device: str
    loaded: bool
    reloaded: bool


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
        cpu_fallback=bool(getattr(__import__("app.config", fromlist=["ml_pipeline_settings"]).ml_pipeline_settings, "cpu_fallback", True)),
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

    Validates the payload, saves ``ml_device`` + ``ml_cuda_index`` into the
    feature-flags Config row, then reloads the in-process ML singleton so the
    next extraction/classification request honours the new device. If the
    underlying load fails (e.g. CUDA OOM), :func:`reload_ml_models` still
    falls back to CPU when ``cpu_fallback`` is true; the response reflects
    the effective device actually in use.
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
    existing = (await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))).scalar_one_or_none()
    if existing:
        existing.value = flags
    else:
        session.add(Config(key=FEATURE_FLAGS_KEY, value=flags))
    await session.flush()

    reloaded = False
    effective = "cpu"
    try:
        ml = reload_ml_models(device=device, cuda_index=cuda_index)
        reloaded = True
        effective = ml.device
    except Exception as exc:
        # Best-effort reload: log + return current state. The UI can retry.
        logger = __import__("logging").getLogger(__name__)
        logger.warning("reload_ml_models failed during /ml-device/apply: %s", exc)

    return MLDeviceApplyResponse(
        ml_device=device,
        ml_cuda_index=cuda_index,
        effective_device=effective,
        loaded=models_available(),
        reloaded=reloaded,
    )


@router.post("/enrichment/trigger")
async def trigger_enrichment(
    _user=Depends(require_auth),
    request: Request = None,
):
    from app.services.enrichment_worker import EnrichmentWorker

    llm = getattr(request.app.state, "llm", None) if request else None
    if not llm:
        raise HTTPException(status_code=503, detail="LLM not available")

    worker = EnrichmentWorker(llm)
    count = await worker.process_batch(batch_size=10)

    return {"processed": count}
